from __future__ import annotations

from app.domain.entities.recommendation_models import UserContext, UserProfile
from app.core.ontology_query_builder import (
    build_cross_ontology_sparql_from_signals,
    translate_mood,
    translate_companion,
    translate_energy,
)

# ---------------------------------------------------------------------------
# Prefixes shared by all queries in this module
# ---------------------------------------------------------------------------
_PREFIXES = (
    "PREFIX movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>\n"
    "PREFIX bridge: <http://www.semanticweb.org/movierecommendation/ontologies/2025/bridge-ontology#>\n"
    "PREFIX schema1: <http://schema.org/>\n"
    "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
)

# Full SELECT projection — same columns every strategy returns so Scorer always
# has the same fields regardless of which strategy fired.
_SELECT_COLS = (
    "SELECT DISTINCT ?movie ?title ?genreName ?runtime ?rating ?posterUrl\n"
    "                ?releaseDate ?compatibilityScore ?moodMatchScore ?socialMatchScore\n"
    "                ?energyMatchScore ?timeMatchScore ?kidFriendly\n"
)

_OPTIONAL_BLOCK = (
    "  OPTIONAL { ?movie movie:hasMainGenre/movie:genreName ?genreName }\n"
    "  OPTIONAL { ?movie movie:runtime ?runtime }\n"
    "  OPTIONAL { ?movie movie:hasRating ?rating }\n"
    "  OPTIONAL { ?movie schema1:image ?posterUrl }\n"
    "  OPTIONAL { ?movie movie:releaseDate ?releaseDate }\n"
    "  OPTIONAL { ?movie bridge:compatibilityScore ?compatibilityScore }\n"
    "  OPTIONAL { ?movie bridge:moodMatchScore ?moodMatchScore }\n"
    "  OPTIONAL { ?movie bridge:socialMatchScore ?socialMatchScore }\n"
    "  OPTIONAL { ?movie bridge:energyMatchScore ?energyMatchScore }\n"
    "  OPTIONAL { ?movie bridge:timeMatchScore ?timeMatchScore }\n"
    "  OPTIONAL { ?movie bridge:isKidFriendly ?kidFriendly }\n"
)

# Broadest possible fallback — no filters, just ORDER BY rating.
_BROAD_SPARQL = (
    _PREFIXES
    + _SELECT_COLS
    + "WHERE {\n"
    + "  ?movie rdf:type movie:FeatureFilm ; movie:hasTitle ?title .\n"
    + _OPTIONAL_BLOCK
    + "}\n"
    + "ORDER BY DESC(?compatibilityScore) DESC(?rating)\n"
    + "LIMIT 50"
)


def _esc(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def _genre_filter_sparql(
    genres: list[str],
    excluded: set[str],
    hard_kid_filter: bool,
    runtime_max: int | None,
) -> str:
    """SELECT filtered by genre names — fallback when no mood/companion signals."""
    genre_values = ", ".join(f'"{_esc(g)}"' for g in genres if str(g).strip())
    genre_filter = f"  FILTER(?genreName IN ({genre_values}))\n" if genre_values else ""

    children_filter = "  ?movie bridge:isKidFriendly true .\n" if hard_kid_filter else ""

    runtime_filter = (
        f"  FILTER(!BOUND(?runtime) || ?runtime <= {int(runtime_max)})\n"
        if runtime_max is not None
        else ""
    )

    excl_clauses = [
        f'!CONTAINS(LCASE(STR(?title)), LCASE("{_esc(v)}"))'
        for v in sorted(excluded)[:10]
        if str(v).strip()
    ]
    exclusion_filter = f"  FILTER({' && '.join(excl_clauses)})\n" if excl_clauses else ""

    return (
        _PREFIXES
        + _SELECT_COLS
        + "WHERE {\n"
        + "  ?movie rdf:type movie:FeatureFilm ; movie:hasTitle ?title .\n"
        + _OPTIONAL_BLOCK
        + children_filter
        + genre_filter
        + runtime_filter
        + exclusion_filter
        + "}\n"
        + "ORDER BY DESC(?compatibilityScore) DESC(?rating)\n"
        + "LIMIT 40"
    )


def _centrality_ranking_sparql(genre: str | None = None, limit: int = 50) -> str:
    """Movies ordered by rating + bridge score — used as cold-start ranking.

    When ``genre`` is provided the query is restricted to that genre so cold-start
    users that did express a genre preference still receive relevant results.
    """
    genre_filter = (
        f'  FILTER(?genreName = "{_esc(genre)}")\n' if genre else ""
    )
    return (
        _PREFIXES
        + _SELECT_COLS
        + "WHERE {\n"
        + "  ?movie rdf:type movie:FeatureFilm ; movie:hasTitle ?title .\n"
        + "  ?movie movie:hasMainGenre ?_genre .\n"
        + "  ?_genre movie:genreName ?genreName .\n"
        + genre_filter
        + "  OPTIONAL { ?movie movie:runtime ?runtime }\n"
        + "  OPTIONAL { ?movie movie:hasRating ?rating }\n"
        + "  OPTIONAL { ?movie schema1:image ?posterUrl }\n"
        + "  OPTIONAL { ?movie movie:releaseDate ?releaseDate }\n"
        + "  OPTIONAL { ?movie bridge:compatibilityScore ?compatibilityScore }\n"
        + "  OPTIONAL { ?movie bridge:moodMatchScore ?moodMatchScore }\n"
        + "  OPTIONAL { ?movie bridge:socialMatchScore ?socialMatchScore }\n"
        + "  OPTIONAL { ?movie bridge:energyMatchScore ?energyMatchScore }\n"
        + "  OPTIONAL { ?movie bridge:timeMatchScore ?timeMatchScore }\n"
        + "  OPTIONAL { ?movie bridge:isKidFriendly ?kidFriendly }\n"
        + "}\n"
        + "ORDER BY DESC(?rating) DESC(?compatibilityScore)\n"
        + f"LIMIT {limit}"
    )


def build_strategy(ctx: UserContext, profile: UserProfile) -> list[tuple[str, str]]:
    """Return an ordered list of ``(name, sparql)`` attempts for the pipeline.

    The executor tries each in order until ``min_results`` rows are found.
    Strategies progress from most-specific (full ontology match) to broadest
    (no filters, sorted by rating).

    Cold-start users with no query signals get centrality-ranked results first.
    """
    excluded: set[str] = {str(e).strip().lower() for e in ctx.exclusions if str(e).strip()}

    # Translate English NLU values → Spanish bridge values
    mood_es = translate_mood(ctx.mood)
    companion_es = translate_companion(
        ctx.companion,
        ctx.has_children or ctx.children_age_hint == "young",
    )
    energy_es = translate_energy(ctx.energy)

    # Hard kid filter only for "young" (< 12). "teen" / None are handled via scoring.
    hard_kid_filter = ctx.children_age_hint == "young"

    has_strong_signal = bool(mood_es or companion_es or ctx.genres)

    # Cold start with no signal → just return high-quality broad results
    if profile.is_cold_start and not has_strong_signal:
        return [
            ("centrality_ranking", _centrality_ranking_sparql()),
            ("broad", _BROAD_SPARQL),
        ]

    attempts: list[tuple[str, str]] = []

    # ── 1. ontology_full: mood + companion + energy + optional kid filter ───
    if mood_es and companion_es:
        attempts.append((
            "ontology_full",
            build_cross_ontology_sparql_from_signals(
                mood_es=mood_es,
                companion_es=companion_es,
                energy_es=energy_es,
                has_children=hard_kid_filter,
                runtime_max=ctx.runtime_max,
                excluded_normalized=excluded,
                limit=30,
            ),
        ))

    # ── 2. ontology_mood_companion: mood + companion, relax energy/runtime ──
    if mood_es and companion_es:
        attempts.append((
            "ontology_mood_companion",
            build_cross_ontology_sparql_from_signals(
                mood_es=mood_es,
                companion_es=companion_es,
                energy_es=None,
                has_children=hard_kid_filter,
                runtime_max=None,
                excluded_normalized=excluded,
                limit=40,
            ),
        ))

    # ── 3. ontology_mood_only: just mood (drop companion) ───────────────────
    if mood_es:
        attempts.append((
            "ontology_mood_only",
            build_cross_ontology_sparql_from_signals(
                mood_es=mood_es,
                companion_es=None,
                energy_es=energy_es,
                has_children=hard_kid_filter,
                runtime_max=ctx.runtime_max,
                excluded_normalized=excluded,
                limit=40,
            ),
        ))

    # ── 4. ontology_companion_only: just companion (drop mood) ──────────────
    if companion_es:
        attempts.append((
            "ontology_companion_only",
            build_cross_ontology_sparql_from_signals(
                mood_es=None,
                companion_es=companion_es,
                energy_es=None,
                has_children=hard_kid_filter,
                runtime_max=None,
                excluded_normalized=excluded,
                limit=40,
            ),
        ))

    # ── 5. genre_filter: FILTER on genre names ───────────────────────────────
    if ctx.genres:
        attempts.append((
            "genre_filter",
            _genre_filter_sparql(
                genres=ctx.genres,
                excluded=excluded,
                hard_kid_filter=hard_kid_filter,
                runtime_max=ctx.runtime_max,
            ),
        ))

    # ── 6. centrality_ranking for cold-start users with genre signal ─────────
    if profile.is_cold_start and ctx.genres:
        attempts.append((
            "centrality_ranking",
            _centrality_ranking_sparql(genre=ctx.genres[0]),
        ))

    # ── 7. broad: absolute last resort ──────────────────────────────────────
    attempts.append(("broad", _BROAD_SPARQL))

    # Deduplicate: keep first occurrence of each unique SPARQL string
    seen: set[str] = set()
    unique: list[tuple[str, str]] = []
    for name, sparql in attempts:
        if sparql not in seen:
            seen.add(sparql)
            unique.append((name, sparql))

    return unique
