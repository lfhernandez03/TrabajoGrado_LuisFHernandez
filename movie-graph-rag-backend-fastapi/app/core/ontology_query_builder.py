from __future__ import annotations

from collections import Counter
import logging
from datetime import datetime

from app.core.fuseki_client import execute_update_query
from app.domain.entities.query_context import QueryContext

logger = logging.getLogger(__name__)


MOOD_ES_MAP = {
    "happy": "feliz",
    "relaxed": "relajado",
    "stressed": "estresado",
    "sad": "triste",
    "anxious": "ansioso",
    "excited": "emocionado",
    "bored": "aburrido",
    "curious": "curioso",
    "romantic": "romantico",
    "nostalgic": "nostalgico",
    "adventurous": "aventurero",
    "nervous": "nervioso",
    "adventurer": "aventurero",
    "neutral": None,
}

COMPANION_ES_MAP = {
    "alone": "solo",
    "partner": "pareja",
    "family": "familia",
    "friends": "amigos",
    "family_with_kids": "familia con niños",
}

ENERGY_ES_MAP = {
    "low": "bajo",
    "medium": "medio",
    "high": "alto",
    "relaxed": "bajo",
    "excited": "alto",
}


def _escape_turtle_literal(value: str) -> str:
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", " ")
        .replace("\r", " ")
    )


def translate_mood(mood: str | None) -> str | None:
    if mood is None:
        return None
    return MOOD_ES_MAP.get(str(mood).strip().lower())


def translate_companion(companion_type: str | None, has_children: bool = False) -> str | None:
    if companion_type is None:
        return None

    normalized = str(companion_type).strip().lower()
    if normalized == "family" and has_children:
        return "familia con niños"

    return COMPANION_ES_MAP.get(normalized)


def translate_energy(energy_description: str | None) -> str | None:
    if energy_description is None:
        return None
    return ENERGY_ES_MAP.get(str(energy_description).strip().lower())


def build_context_triples_turtle(
    snapshot_id: str,
    ctx: QueryContext,
    user_id: str,
    now: datetime,
) -> str:
    safe_snapshot_id = _escape_turtle_literal(snapshot_id)
    safe_intent = _escape_turtle_literal(ctx.intent)
    iso_timestamp = now.replace(microsecond=0).isoformat()
    day_name = now.strftime("%A")

    lines: list[str] = [
        "@prefix context: <http://www.semanticweb.org/movierecommendation/ontologies/2025/context-ontology#> .",
        "@prefix contextdata: <http://www.semanticweb.org/movierecommendation/data/context/> .",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
        "",
        f"contextdata:Session_{safe_snapshot_id} a context:ContextSnapshot ;",
        f"    context:snapshotID \"{safe_snapshot_id}\"^^xsd:string ;",
        f"    context:requestTimestamp \"{iso_timestamp}\"^^xsd:dateTime ;",
        f"    context:userIntent \"{safe_intent}\"^^xsd:string ;",
        f"    context:hourOfDay {now.hour} ;",
        f"    context:dayOfWeek \"{_escape_turtle_literal(day_name)}\"^^xsd:string .",
    ]

    mood_es = translate_mood(ctx.mood)
    if mood_es:
        energy_hint = translate_energy(ctx.mood) or "medio"
        lines.extend(
            [
                f"contextdata:Session_{safe_snapshot_id} context:feelsMood contextdata:Mood_{safe_snapshot_id} .",
                f"contextdata:Mood_{safe_snapshot_id} a context:EmotionalContext ;",
                f"    context:moodDescription \"{_escape_turtle_literal(mood_es)}\"^^xsd:string ;",
                f"    context:desiredEnergyLevel \"{_escape_turtle_literal(energy_hint)}\"^^xsd:string .",
            ]
        )

    social_context = ctx.social_context or {}
    has_children = bool(social_context.get("hasChildren", False)) if social_context else False
    companion_es = translate_companion(social_context.get("companionType"), has_children)
    if social_context and companion_es:
        lines.extend(
            [
                f"contextdata:Session_{safe_snapshot_id} context:withCompanion contextdata:Social_{safe_snapshot_id} .",
                f"contextdata:Social_{safe_snapshot_id} a context:SocialContext ;",
                f"    context:companionType \"{_escape_turtle_literal(companion_es)}\"^^xsd:string ;",
                f"    context:hasChildren {str(has_children).lower()} .",
            ]
        )

    has_runtime = ctx.runtime_max is not None
    has_exclusions = bool(ctx.exclusions)
    if has_runtime or has_exclusions:
        lines.extend(
            [
                f"contextdata:Session_{safe_snapshot_id} context:hasRequirement contextdata:Req_{safe_snapshot_id} .",
                f"contextdata:Req_{safe_snapshot_id} a context:RequirementContext .",
            ]
        )

        if has_runtime:
            lines.append(
                f"contextdata:Req_{safe_snapshot_id} context:availableTime {int(ctx.runtime_max)} ."
            )

        if has_exclusions:
            exclusions_joined = ", ".join(_escape_turtle_literal(str(item)) for item in ctx.exclusions)
            lines.append(
                f"contextdata:Req_{safe_snapshot_id} context:contentRestrictions \"{exclusions_joined}\"^^xsd:string ."
            )

    return "\n".join(lines)


def inject_context_snapshot(snapshot_id: str, ctx: QueryContext, user_id: str, now: datetime) -> str:
    try:
        triples = build_context_triples_turtle(snapshot_id, ctx, user_id, now)
        prefix_lines: list[str] = []
        body_lines: list[str] = []
        for line in triples.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("@prefix") and stripped.endswith("."):
                prefix_lines.append(f"PREFIX {stripped[len('@prefix'):].rstrip('.').strip()}")
                continue
            body_lines.append(line)

        prefixes = "\n".join(prefix_lines)
        body = "\n".join(body_lines)
        sparql_update = f"""
{prefixes}
INSERT DATA {{
    GRAPH <http://session/{snapshot_id}> {{
{body}
}}
}}
"""
        success = execute_update_query(sparql_update)
        if success:
            return f"http://session/{snapshot_id}"
        return ""
    except Exception as exc:
        logger.error("Failed to inject context snapshot %s: %s", snapshot_id, exc)
        return ""


def delete_context_snapshot(snapshot_id: str) -> None:
    try:
        execute_update_query(f"DROP SILENT GRAPH <http://session/{snapshot_id}>")
    except Exception as exc:
        logger.error("Failed to delete context snapshot %s: %s", snapshot_id, exc)


def _escape_sparql_literal(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").strip()


def _safe_cross_ontology_fallback(limit: int = 30) -> str:
    """Fallback SPARQL query using standardized RDF properties for Gemini queries.
    
    Uses standardized property names:
    - movie:hasRating (standardized across all rating sources: MovieLens, IMDb, TMDb)
    - movie:hasVoteCount (vote count across sources)
    This prevents Gemini from generating queries with non-existent properties.
    """
    safe_limit = max(1, min(100, int(limit)))
    return (
        "PREFIX movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>\n"
        "PREFIX bridge: <http://www.semanticweb.org/movierecommendation/ontologies/2025/bridge-ontology#>\n"
        "PREFIX schema1: <http://schema.org/>\n"
        "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
        "SELECT DISTINCT ?movie ?title ?genreName ?runtime ?rating ?posterUrl "
        "?releaseDate ?compatibilityScore ?moodMatch ?socialMatch ?energyMatch ?kidFriendly\n"
        "WHERE {\n"
        "  ?movie rdf:type movie:FeatureFilm ; movie:hasTitle ?title .\n"
        "  OPTIONAL { ?movie movie:hasMainGenre/movie:genreName ?genreName }\n"
        "  OPTIONAL { ?movie movie:runtime ?runtime }\n"
        "  OPTIONAL { ?movie movie:hasRating ?rating }\n"
        "  OPTIONAL { ?movie schema1:image ?posterUrl }\n"
        "  OPTIONAL { ?movie movie:releaseDate ?releaseDate }\n"
        "  OPTIONAL { ?movie bridge:compatibilityScore ?compatibilityScore }\n"
        "  OPTIONAL { ?movie bridge:moodMatchScore ?moodMatch }\n"
        "  OPTIONAL { ?movie bridge:socialMatchScore ?socialMatch }\n"
        "  OPTIONAL { ?movie bridge:energyMatchScore ?energyMatch }\n"
        "  OPTIONAL { ?movie bridge:isKidFriendly ?kidFriendly }\n"
        "}\n"
        "ORDER BY DESC(?compatibilityScore) DESC(?rating)\n"
        f"LIMIT {safe_limit}"
    )


def build_genre_semantic_fallback_sparql(
    genres: list[str] | None,
    has_children: bool,
    excluded_normalized: set[str],
    limit: int = 40,
) -> str:
    """Build genre-based semantic fallback SPARQL when bridge predicates might not exist.
    
    This is used when:
    - User provides genre preferences without explicit mood/companion signals
    - AND social context indicates need for semantic filtering (e.g., has_children)
    
    The query adds semantic constraints based on genre + context without relying on
    bridge predicates, allowing graceful fallback if bridge properties aren't populated.
    """
    safe_limit = max(1, min(100, int(limit)))
    
    genre_filter = ""
    if genres:
        genre_values = ", ".join(
            f'"{_escape_sparql_literal(g)}"' for g in genres if str(g).strip()
        )
        genre_filter = f"  FILTER(?genreName IN ({genre_values}))\n"
    
    kid_friendly_suggestion = ""
    if has_children and ("Animation" in (genres or []) or "Family" in (genres or [])):
        # For kids viewing, prioritize appropriate certifications
        # This uses movie properties instead of bridge predicates
        kid_friendly_suggestion = (
            "  OPTIONAL { ?movie movie:hasCertification ?cert }\n"
            "  OPTIONAL { ?movie bridge:isKidFriendly ?kf }\n"
        )
    
    exclusion_filter = ""
    if excluded_normalized:
        clauses = [
            f'!CONTAINS(LCASE(STR(?title)), LCASE("{_escape_sparql_literal(value)}"))'
            for value in sorted(excluded_normalized)[:10]
            if str(value).strip()
        ]
        if clauses:
            exclusion_filter = f"  FILTER({' && '.join(clauses)})\n"
    
    candidate = (
        "PREFIX movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>\n"
        "PREFIX bridge: <http://www.semanticweb.org/movierecommendation/ontologies/2025/bridge-ontology#>\n"
        "PREFIX schema1: <http://schema.org/>\n"
        "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
        "\n"
        "SELECT DISTINCT ?movie ?title ?genreName ?runtime ?rating ?posterUrl ?releaseDate\n"
        "WHERE {\n"
        "  ?movie rdf:type movie:FeatureFilm ;\n"
        "         movie:hasTitle ?title .\n"
        "  OPTIONAL { ?movie movie:hasMainGenre/movie:genreName ?genreName }\n"
        "  OPTIONAL { ?movie movie:runtime ?runtime }\n"
        "  OPTIONAL { ?movie movie:hasRating ?rating }\n"
        "  OPTIONAL { ?movie schema1:image ?posterUrl }\n"
        "  OPTIONAL { ?movie movie:releaseDate ?releaseDate }\n"
        f"{kid_friendly_suggestion}"
        f"{genre_filter}"
        f"{exclusion_filter}"
        "}\n"
        "ORDER BY DESC(?rating) DESC(?releaseDate)\n"
        f"LIMIT {safe_limit}"
    )
    
    
    return candidate if _is_valid_sparql_query(candidate) else _safe_cross_ontology_fallback(limit=safe_limit)


def _is_valid_sparql_query(query_text: str) -> bool:
    normalized = query_text.strip()
    upper = normalized.upper()
    if not normalized:
        return False

    for token in ("PREFIX", "SELECT", "WHERE", "LIMIT"):
        if token not in upper:
            return False

    if normalized.count("{") != normalized.count("}"):
        return False

    forbidden = ("INSERT", "DELETE", "DROP", "CLEAR", "CREATE", "LOAD", "MOVE", "COPY", "ADD")
    if any(f" {token} " in f" {upper} " for token in forbidden):
        return False

    return True


def build_activity_query_from_history(history_rows: list[dict]) -> tuple[str | None, str | None, str | None]:
    mood_counter: Counter[str] = Counter()
    companion_counter: Counter[str] = Counter()
    energy_counter: Counter[str] = Counter()

    for row in history_rows:
        mood = str(row.get("moodDescription") or "").strip()
        if mood:
            mood_counter[mood] += 1

        companion = str(row.get("companionType") or "").strip()
        if companion:
            companion_counter[companion] += 1

        energy = str(row.get("desiredEnergyLevel") or "").strip()
        if energy:
            energy_counter[energy] += 1

    mood_es = mood_counter.most_common(1)[0][0] if mood_counter else None
    companion_es = companion_counter.most_common(1)[0][0] if companion_counter else None
    energy_es = energy_counter.most_common(1)[0][0] if energy_counter else None

    return mood_es, companion_es, energy_es


def build_cross_ontology_sparql_from_signals(
    mood_es: str | None,
    companion_es: str | None,
    energy_es: str | None,
    has_children: bool,
    runtime_max: int | None,
    excluded_normalized: set[str],
    limit: int = 30,
) -> str:
    """Build SPARQL query using bridge semantic compatibility predicates.

    Uses exact matching over bridge:compatibleMood / bridge:compatibleCompanion /
    bridge:compatibleEnergyLevel so semantic filters are always effective when
    signals are present.
    """
    safe_limit = max(1, min(100, int(limit)))

    mood_filter = ""
    if mood_es:
        mood_filter = (
            f'  ?movie bridge:compatibleMood "{_escape_sparql_literal(mood_es)}" .\n'
        )

    companion_filter = ""
    if companion_es:
        companion_filter = (
            f'  ?movie bridge:compatibleCompanion "{_escape_sparql_literal(companion_es)}" .\n'
        )

    energy_filter = ""
    if energy_es:
        energy_filter = (
            f'  ?movie bridge:compatibleEnergyLevel "{_escape_sparql_literal(energy_es)}" .\n'
        )

    children_filter = "  ?movie bridge:isKidFriendly true .\n" if has_children else ""
    runtime_filter = (
        f"  FILTER(!BOUND(?runtime) || ?runtime <= {int(runtime_max)})\n"
        if runtime_max is not None
        else ""
    )

    exclusions = sorted(excluded_normalized)[:10]
    exclusion_filter = ""
    if exclusions:
        clauses = [
            f'!CONTAINS(LCASE(STR(?title)), LCASE("{_escape_sparql_literal(value)}"))'
            for value in exclusions
            if str(value).strip()
        ]
        if clauses:
            exclusion_filter = f"  FILTER({' && '.join(clauses)})\n"

    candidate = (
        "PREFIX movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>\n"
        "PREFIX bridge: <http://www.semanticweb.org/movierecommendation/ontologies/2025/bridge-ontology#>\n"
        "PREFIX schema1: <http://schema.org/>\n"
        "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
        "\n"
        "SELECT DISTINCT ?movie ?title ?genreName ?runtime ?rating ?posterUrl\n"
        "                ?releaseDate ?compatibilityScore ?moodMatch ?socialMatch\n"
        "                ?energyMatch ?kidFriendly\n"
        "WHERE {\n"
        "  ?movie rdf:type movie:FeatureFilm ;\n"
        "         movie:hasTitle ?title .\n"
        "  OPTIONAL { ?movie movie:hasMainGenre/movie:genreName ?genreName }\n"
        "  OPTIONAL { ?movie movie:runtime ?runtime }\n"
        "  OPTIONAL { ?movie movie:hasRating ?rating }\n"
        "  OPTIONAL { ?movie schema1:image ?posterUrl }\n"
        "  OPTIONAL { ?movie movie:releaseDate ?releaseDate }\n"
        "  OPTIONAL { ?movie bridge:compatibilityScore ?compatibilityScore }\n"
        "  OPTIONAL { ?movie bridge:moodMatchScore ?moodMatch }\n"
        "  OPTIONAL { ?movie bridge:socialMatchScore ?socialMatch }\n"
        "  OPTIONAL { ?movie bridge:energyMatchScore ?energyMatch }\n"
        "  OPTIONAL { ?movie bridge:isKidFriendly ?kidFriendly }\n"
        f"{mood_filter}"
        f"{companion_filter}"
        f"{energy_filter}"
        f"{children_filter}"
        f"{runtime_filter}"
        f"{exclusion_filter}"
        "}\n"
        "ORDER BY DESC(?compatibilityScore) DESC(?rating)\n"
        f"LIMIT {safe_limit}"
    )

    if not _is_valid_sparql_query(candidate):
        return _safe_cross_ontology_fallback(limit=safe_limit)
    return candidate


def build_cross_ontology_sparql(
    ctx: QueryContext,
    excluded_normalized: set[str],
) -> list[tuple[str, str]]:
    """Translate QueryContext to Spanish signals and build progressive ontology attempt chain.

    Returns a list of (attempt_name, sparql_query) tuples compatible with the
    ontology_attempts parameter of build_query_attempts in recommendation_components.py.
    """
    social_context = ctx.social_context or {}
    has_children = bool(social_context.get("hasChildren", False))
    companion_type = social_context.get("companionType") if social_context else None

    mood_es = translate_mood(ctx.mood)
    companion_es = translate_companion(companion_type, has_children)
    energy_hint = translate_energy(ctx.mood) if ctx.mood else None
    runtime_max = ctx.runtime_max

    attempts: list[tuple[str, str]] = []

    if mood_es and companion_es:
        attempts.append((
            "ontology_full",
            build_cross_ontology_sparql_from_signals(
                mood_es=mood_es,
                companion_es=companion_es,
                energy_es=energy_hint,
                has_children=has_children,
                runtime_max=runtime_max,
                excluded_normalized=excluded_normalized,
                limit=30,
            ),
        ))
        attempts.append((
            "ontology_mood_companion",
            build_cross_ontology_sparql_from_signals(
                mood_es=mood_es,
                companion_es=companion_es,
                energy_es=None,
                has_children=has_children,
                runtime_max=None,
                excluded_normalized=excluded_normalized,
                limit=40,
            ),
        ))

    if mood_es:
        attempts.append((
            "ontology_mood_only",
            build_cross_ontology_sparql_from_signals(
                mood_es=mood_es,
                companion_es=None,
                energy_es=energy_hint,
                has_children=has_children,
                runtime_max=runtime_max,
                excluded_normalized=excluded_normalized,
                limit=40,
            ),
        ))

    if companion_es:
        attempts.append((
            "ontology_companion_only",
            build_cross_ontology_sparql_from_signals(
                mood_es=None,
                companion_es=companion_es,
                energy_es=None,
                has_children=has_children,
                runtime_max=None,
                excluded_normalized=excluded_normalized,
                limit=40,
            ),
        ))

    genre_set = {str(genre).strip().lower() for genre in (ctx.genres or []) if str(genre).strip()}
    family_or_animation_query = bool({"family", "animation"}.intersection(genre_set))
    if not attempts and family_or_animation_query:
        attempts.append((
            "ontology_kids_only",
            build_cross_ontology_sparql_from_signals(
                mood_es=None,
                companion_es=None,
                energy_es=None,
                has_children=True,
                runtime_max=runtime_max,
                excluded_normalized=excluded_normalized,
                limit=40,
            ),
        ))
        # Add fallback if bridge predicates aren't populated
        attempts.append((
            "genre_semantic_family",
            build_genre_semantic_fallback_sparql(
                genres=ctx.genres,
                has_children=True,
                excluded_normalized=excluded_normalized,
                limit=40,
            ),
        ))

    seen: set[str] = set()
    unique: list[tuple[str, str]] = []
    for name, query in attempts:
        if query not in seen:
            seen.add(query)
            unique.append((name, query))
    
    return unique
