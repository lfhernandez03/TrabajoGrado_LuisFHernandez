from __future__ import annotations

from app.core.fuseki_client import FusekiQueryError, execute_select_query


def parse_optional_float(value: object) -> float | None:
    try:
        if value is None:
            return None
        return float(str(value))
    except Exception:
        return None


def parse_optional_int(value: object) -> int | None:
    try:
        if value is None:
            return None
        return int(float(str(value)))
    except Exception:
        return None


def extract_release_year(value: object) -> str | None:
    if value is None:
        return None
    try:
        year = str(value)[:4]
        return year if year else None
    except Exception:
        return None


def map_fuseki_row_to_candidate(row: dict, strategy: str | None = None) -> dict | None:
    title = row.get("title")
    if not title:
        return None

    candidate = {
        "title": title,
        "posterUrl": row.get("posterUrl"),
        "runtime": parse_optional_int(row.get("runtime")),
        "genreName": row.get("genreName"),
        "releaseDate": extract_release_year(row.get("releaseDate")),
        "averageRating": parse_optional_float(row.get("rating")),
    }
    if strategy:
        candidate["queryStrategy"] = strategy
    return candidate


def safe_sparql_literal(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"').strip()


def safe_fallback_sparql_query(limit: int = 60) -> str:
    return (
        "PREFIX movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>\n"
        "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
        "SELECT DISTINCT ?movie ?title ?genreName ?runtime ?rating ?posterUrl ?releaseDate\n"
        "WHERE {\n"
        "  ?movie rdf:type movie:FeatureFilm ; movie:hasTitle ?title .\n"
        "  OPTIONAL { ?movie movie:hasMainGenre/movie:genreName ?genreName }\n"
        "  OPTIONAL { ?movie movie:runtime ?runtime }\n"
        "  OPTIONAL { ?movie movie:hasAverageRating ?rating }\n"
        "  OPTIONAL { ?movie movie:hasPosterUrl ?posterUrl }\n"
        "  OPTIONAL { ?movie movie:releaseDate ?releaseDate }\n"
        "}\n"
        "ORDER BY DESC(?rating) DESC(?releaseDate)\n"
        f"LIMIT {max(1, min(200, int(limit)))}"
    )


def is_valid_sparql_query(query_text: str) -> bool:
    normalized = query_text.strip()
    upper = normalized.upper()
    if not normalized:
        return False

    required = ["PREFIX", "SELECT", "WHERE", "LIMIT"]
    if any(token not in upper for token in required):
        return False

    if normalized.count("{") != normalized.count("}"):
        return False

    forbidden = [
        "INSERT", "DELETE", "DROP", "CLEAR", "CREATE", "LOAD", "MOVE", "COPY", "ADD",
    ]
    if any(f" {token} " in f" {upper} " for token in forbidden):
        return False

    return True


def build_sparql_query(
    *,
    genres: list[str],
    runtime_max: int | None,
    director: str | None,
    year_min: int | None,
    year_max: int | None,
    exclude_titles: list[str],
    limit: int,
) -> str:
    genre_filter = ""
    if genres:
        genre_values = ", ".join(
            f'"{safe_sparql_literal(g)}"' for g in genres if str(g).strip()
        )
        genre_filter = f"FILTER(?genreName IN ({genre_values}))"

    runtime_filter = ""
    if runtime_max is not None:
        runtime_filter = f"FILTER(!BOUND(?runtime) || ?runtime <= {int(runtime_max)})"

    director_filter = ""
    if director:
        safe_dir = safe_sparql_literal(director)
        director_filter = f'FILTER(CONTAINS(LCASE(STR(?directorName)), LCASE("{safe_dir}")))'

    exclude_filter = ""
    if exclude_titles:
        exclusion_clauses = [
            f'!CONTAINS(LCASE(STR(?title)), LCASE("{safe_sparql_literal(title)}"))'
            for title in exclude_titles
            if str(title).strip()
        ]
        if exclusion_clauses:
            exclude_filter = f"FILTER({' && '.join(exclusion_clauses)})"

    year_filter = ""
    if year_min is not None:
        year_filter += f"FILTER(YEAR(?releaseDate) >= {int(year_min)})\n  "
    if year_max is not None:
        year_filter += f"FILTER(YEAR(?releaseDate) <= {int(year_max)})"

    director_block = ""
    if director:
        director_block = "  OPTIONAL { ?movie movie:hasDirector/movie:directorName ?directorName }\n"

    candidate = (
        "PREFIX movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>\n"
        "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
        "SELECT DISTINCT ?movie ?title ?genreName ?runtime ?rating ?posterUrl ?releaseDate\n"
        "WHERE {\n"
        "  ?movie rdf:type movie:FeatureFilm ;\n"
        "         movie:hasTitle ?title .\n"
        "  OPTIONAL { ?movie movie:hasMainGenre/movie:genreName ?genreName }\n"
        "  OPTIONAL { ?movie movie:runtime ?runtime }\n"
        "  OPTIONAL { ?movie movie:hasAverageRating ?rating }\n"
        "  OPTIONAL { ?movie movie:hasPosterUrl ?posterUrl }\n"
        "  OPTIONAL { ?movie movie:releaseDate ?releaseDate }\n"
        f"{director_block}"
        f"  {genre_filter}\n"
        f"  {runtime_filter}\n"
        f"  {year_filter}\n"
        f"  {director_filter}\n"
        f"  {exclude_filter}\n"
        "}\n"
        "ORDER BY DESC(?rating) DESC(?releaseDate)\n"
        f"LIMIT {limit}"
    )

    if not is_valid_sparql_query(candidate):
        return safe_fallback_sparql_query(limit=limit)
    return candidate


def build_query_attempts(
    *,
    preferred_genres: list[str],
    runtime_max: int | None,
    director_hint: str | None,
    year_min: int | None,
    year_max: int | None,
    excluded_titles: set[str],
) -> list[tuple[str, str]]:
    query_attempts: list[tuple[str, str]] = []
    has_genre_constraint = bool(preferred_genres)
    has_runtime_constraint = bool(runtime_max)
    excluded_for_query = sorted(excluded_titles)[:10]

    query_attempts.append((
        "strict",
        build_sparql_query(
            genres=preferred_genres if has_genre_constraint else [],
            runtime_max=runtime_max if has_runtime_constraint else None,
            director=director_hint,
            year_min=year_min,
            year_max=year_max,
            exclude_titles=excluded_for_query,
            limit=30,
        ),
    ))

    if has_genre_constraint and has_runtime_constraint:
        query_attempts.append((
            "relaxed_runtime",
            build_sparql_query(
                genres=preferred_genres,
                runtime_max=None,
                director=director_hint,
                year_min=year_min,
                year_max=year_max,
                exclude_titles=excluded_for_query,
                limit=40,
            ),
        ))

    if has_genre_constraint:
        query_attempts.append((
            "relaxed_genre",
            build_sparql_query(
                genres=[],
                runtime_max=runtime_max,
                director=director_hint,
                year_min=year_min,
                year_max=year_max,
                exclude_titles=excluded_for_query,
                limit=40,
            ),
        ))

    query_attempts.append((
        "broad",
        build_sparql_query(
            genres=[],
            runtime_max=None,
            director=None,
            year_min=None,
            year_max=None,
            exclude_titles=[],
            limit=60,
        ),
    ))

    unique_attempts: list[tuple[str, str]] = []
    seen_queries: set[str] = set()
    for attempt_name, attempt_query in query_attempts:
        if attempt_query in seen_queries:
            continue
        seen_queries.add(attempt_query)
        unique_attempts.append((attempt_name, attempt_query))

    return unique_attempts


def safe_rdf_literal(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", " ")
        .replace("\r", " ")
    )


def build_rdf_context(
    *,
    snapshot_id: str,
    query: str,
    social_context: dict | None,
    emotional_context: dict | None,
    requirement_context: dict | None,
    preferred_genres: list[str],
) -> str:
    social_companion = social_context["companionType"] if social_context else "unknown"
    mood = emotional_context["moodDescription"] if emotional_context else "neutral"
    energy = emotional_context["desiredEnergyLevel"] if emotional_context else "medium"
    available_time = (
        str(requirement_context["availableTime"])
        if requirement_context and requirement_context.get("availableTime")
        else "unknown"
    )
    genres_literal = ", ".join(preferred_genres) if preferred_genres else "none"
    safe_query = safe_rdf_literal(query)
    return (
        "@prefix ctx: <http://www.semanticweb.org/movierecommendation/context/> .\n"
        f"ctx:{snapshot_id} ctx:userIntent \"{safe_query}\" ;\n"
        f"    ctx:companionType \"{social_companion}\" ;\n"
        f"    ctx:mood \"{mood}\" ;\n"
        f"    ctx:energy \"{energy}\" ;\n"
        f"    ctx:availableTime \"{available_time}\" ;\n"
        f"    ctx:preferredGenres \"{genres_literal}\" ."
    )


def fetch_fuseki_candidates(
    *,
    query_attempts: list[tuple[str, str]],
    excluded_titles: set[str],
    minimum_candidates: int = 5,
) -> tuple[list[dict], int, str, str]:
    fuseki_candidates: list[dict] = []
    fuseki_rows_count = 0
    fuseki_strategy = "strict"
    selected_query = query_attempts[0][1] if query_attempts else ""
    seen_titles: set[str] = set()

    for attempt_name, attempt_query in query_attempts:
        selected_query = attempt_query
        try:
            raw_rows = execute_select_query(attempt_query)
        except FusekiQueryError:
            continue
        fuseki_rows_count += len(raw_rows)

        for row in raw_rows:
            candidate = map_fuseki_row_to_candidate(row=row, strategy=attempt_name)
            if not candidate:
                continue

            normalized_title = str(candidate["title"]).strip().lower()
            if normalized_title in excluded_titles:
                continue
            if normalized_title in seen_titles:
                continue

            fuseki_candidates.append(candidate)
            seen_titles.add(normalized_title)

        if len(fuseki_candidates) >= minimum_candidates:
            fuseki_strategy = attempt_name
            break

    return fuseki_candidates, fuseki_rows_count, fuseki_strategy, selected_query
