from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field

from app.core.fuseki_client import execute_select_query

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SPARQL prefix block shared by all queries
# ---------------------------------------------------------------------------
_PREFIXES = (
    "PREFIX movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>\n"
    "PREFIX bridge: <http://www.semanticweb.org/movierecommendation/ontologies/2025/bridge-ontology#>\n"
    "PREFIX schema1: <http://schema.org/>\n"
    "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
)


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ConnectionHop:
    """One hop on a path between two movies."""
    from_title: str
    to_title: str
    relation: str           # "same_genre", "same_director", "same_mood_profile"


@dataclass
class ConnectionPath:
    """Shortest path between two movies through the graph."""
    source: str
    target: str
    hops: list[ConnectionHop] = field(default_factory=list)
    found: bool = False

    @property
    def length(self) -> int:
        return len(self.hops)


@dataclass
class NetworkNode:
    uri: str
    title: str
    genre: str | None = None
    rating: float | None = None
    poster_url: str | None = None
    description: str | None = None
    runtime: int | None = None
    director: str | None = None
    year: int | None = None


@dataclass
class NetworkEdge:
    source_uri: str
    target_uri: str
    relation: str


@dataclass
class NetworkGraph:
    center_title: str
    nodes: list[NetworkNode] = field(default_factory=list)
    edges: list[NetworkEdge] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal SPARQL helpers
# ---------------------------------------------------------------------------

def _esc(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def _get_movie_info(title: str) -> dict | None:
    """Fetch URI, genre, director, and runtime for a movie by title (case-insensitive)."""
    query = (
        _PREFIXES
        + "SELECT ?movie ?title ?genreName ?directorUri ?runtime\n"
        + "WHERE {\n"
        + "  ?movie rdf:type movie:FeatureFilm ; movie:hasTitle ?title .\n"
        + f'  FILTER(LCASE(STR(?title)) = LCASE("{_esc(title)}"))\n'
        + "  OPTIONAL { ?movie movie:hasMainGenre/movie:genreName ?genreName }\n"
        + "  OPTIONAL { ?movie movie:hasDirector ?directorUri }\n"
        + "  OPTIONAL { ?movie movie:runtime ?runtime }\n"
        + "}\n"
        + "LIMIT 1"
    )
    try:
        rows = execute_select_query(query)
        return rows[0] if rows else None
    except Exception as exc:
        logger.warning("_get_movie_info failed for '%s': %s", title, exc)
        return None


def _movies_by_genre(genre: str, exclude_uris: set[str], limit: int = 30) -> list[dict]:
    """All movies sharing a genre URI, excluding already-visited ones."""
    excl = " ".join(f"<{u}>" for u in list(exclude_uris)[:50])
    excl_filter = f"  FILTER(?movie NOT IN ({excl}))\n" if excl else ""
    query = (
        _PREFIXES
        + "SELECT DISTINCT ?title ?rating ?imdbRating ?genreName ?posterUrl ?description ?runtime ?directorName ?releaseDate\n"
        + "WHERE {\n"
        + "  ?movie rdf:type movie:FeatureFilm ; movie:hasTitle ?title .\n"
        + f'  ?movie movie:hasMainGenre/movie:genreName "{_esc(genre)}" .\n'
        + "  OPTIONAL { ?movie movie:hasMainGenre/movie:genreName ?genreName }\n"
        + "  OPTIONAL { ?movie movie:hasAverageRating ?rating }\n"
        + "  OPTIONAL { ?movie movie:hasIMDbRating ?imdbRating }\n"
        + "  OPTIONAL { ?movie schema1:image ?posterUrl }\n"
        + "  OPTIONAL { ?movie movie:hasPlotSummary ?description }\n"
        + "  OPTIONAL { ?movie movie:runtime ?runtime }\n"
        + "  OPTIONAL { ?movie movie:hasDirector/movie:hasName ?directorName }\n"
        + "  OPTIONAL { ?movie movie:releaseDate ?releaseDate }\n"
        + excl_filter
        + "}\n"
        + f"LIMIT {limit}"
    )
    try:
        return execute_select_query(query)
    except Exception as exc:
        logger.warning("_movies_by_genre failed for '%s': %s", genre, exc)
        return []


def _movies_by_director(director_uri: str, exclude_uris: set[str], limit: int = 20) -> list[dict]:
    """All movies from the same director, excluding already-visited ones."""
    excl = " ".join(f"<{u}>" for u in list(exclude_uris)[:50])
    excl_filter = f"  FILTER(?movie NOT IN ({excl}))\n" if excl else ""
    query = (
        _PREFIXES
        + "SELECT DISTINCT ?movie ?title ?genreName ?rating ?imdbRating ?posterUrl ?description ?runtime ?directorName ?releaseDate\n"
        + "WHERE {\n"
        + "  ?movie rdf:type movie:FeatureFilm ; movie:hasTitle ?title .\n"
        + f"  ?movie movie:hasDirector <{director_uri}> .\n"
        + "  OPTIONAL { ?movie movie:hasMainGenre/movie:genreName ?genreName }\n"
        + "  OPTIONAL { ?movie movie:hasAverageRating ?rating }\n"
        + "  OPTIONAL { ?movie movie:hasIMDbRating ?imdbRating }\n"
        + "  OPTIONAL { ?movie schema1:image ?posterUrl }\n"
        + "  OPTIONAL { ?movie movie:hasPlotSummary ?description }\n"
        + "  OPTIONAL { ?movie movie:runtime ?runtime }\n"
        + f"  OPTIONAL {{ <{director_uri}> movie:hasName ?directorName }}\n"
        + "  OPTIONAL { ?movie movie:releaseDate ?releaseDate }\n"
        + excl_filter
        + "}\n"
        + f"LIMIT {limit}"
    )
    try:
        return execute_select_query(query)
    except Exception as exc:
        logger.warning("_movies_by_director failed for '%s': %s", director_uri, exc)
        return []


def _movies_by_mood_profile(mood: str, exclude_uris: set[str], limit: int = 20) -> list[dict]:
    """Movies sharing a bridge:compatibleMood value (Spanish)."""
    excl = " ".join(f"<{u}>" for u in list(exclude_uris)[:50])
    excl_filter = f"  FILTER(?movie NOT IN ({excl}))\n" if excl else ""
    query = (
        _PREFIXES
        + "SELECT DISTINCT ?movie ?title ?genreName ?rating ?imdbRating ?posterUrl ?description\n"
        + "WHERE {\n"
        + "  ?movie rdf:type movie:FeatureFilm ; movie:hasTitle ?title .\n"
        + f'  ?movie bridge:compatibleMood "{_esc(mood)}" .\n'
        + "  OPTIONAL { ?movie movie:hasMainGenre/movie:genreName ?genreName }\n"
        + "  OPTIONAL { ?movie movie:hasAverageRating ?rating }\n"
        + "  OPTIONAL { ?movie movie:hasIMDbRating ?imdbRating }\n"
        + "  OPTIONAL { ?movie schema1:image ?posterUrl }\n"
        + "  OPTIONAL { ?movie movie:hasPlotSummary ?description }\n"
        + excl_filter
        + "}\n"
        + f"LIMIT {limit}"
    )
    try:
        return execute_select_query(query)
    except Exception as exc:
        logger.warning("_movies_by_mood_profile failed for '%s': %s", mood, exc)
        return []


def _get_mood_profile(movie_uri: str) -> str | None:
    """Return the first compatibleMood value for a movie URI."""
    query = (
        _PREFIXES
        + "SELECT ?mood\n"
        + "WHERE {\n"
        + f"  <{movie_uri}> bridge:compatibleMood ?mood .\n"
        + "}\n"
        + "LIMIT 1"
    )
    try:
        rows = execute_select_query(query)
        return rows[0].get("mood") if rows else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# ConnectionExplorer
# ---------------------------------------------------------------------------

class ConnectionExplorer:
    """Graph traversal utilities over the movie knowledge graph.

    Uses SPARQL queries to find paths, neighbourhoods, and centrality rankings
    without loading the full graph into memory.
    """

    # ── Path finding ────────────────────────────────────────────────────────

    def find_path(self, title_a: str, title_b: str) -> ConnectionPath:
        """BFS — shortest path between two movies up to 3 hops.

        Hop types (in preference order):
          1. same_director
          2. same_genre
          3. same_mood_profile (bridge ontology)

        Returns a ConnectionPath with found=False if no path exists within
        the search limit, or if either title is not found.
        """
        info_a = _get_movie_info(title_a)
        info_b = _get_movie_info(title_b)

        if not info_a or not info_b:
            return ConnectionPath(source=title_a, target=title_b, found=False)

        uri_a = info_a["movie"]
        uri_b = info_b["movie"]

        if uri_a == uri_b:
            return ConnectionPath(source=title_a, target=title_b, hops=[], found=True)

        # BFS: each node = (movie_uri, title, path_so_far)
        queue: deque[tuple[str, str, list[ConnectionHop]]] = deque()
        queue.append((uri_a, info_a.get("title", title_a), []))
        visited: set[str] = {uri_a}
        max_depth = 3

        while queue:
            current_uri, current_title, path = queue.popleft()
            if len(path) >= max_depth:
                continue

            # Expand via director
            director_uri = info_a.get("directorUri") if current_uri == uri_a else None
            if director_uri:
                neighbours = _movies_by_director(director_uri, visited, limit=30)
                for row in neighbours:
                    n_uri = row.get("movie", "")
                    n_title = row.get("title", "")
                    if not n_uri or n_uri in visited:
                        continue
                    hop = ConnectionHop(current_title, n_title, "same_director")
                    new_path = path + [hop]
                    if n_uri == uri_b:
                        return ConnectionPath(title_a, title_b, new_path, found=True)
                    visited.add(n_uri)
                    queue.append((n_uri, n_title, new_path))

            # Expand via genre
            genre = info_a.get("genreName") if current_uri == uri_a else _get_movie_genre(current_uri)
            if genre:
                neighbours = _movies_by_genre(genre, visited, limit=30)
                for row in neighbours:
                    n_uri = row.get("movie", "")
                    n_title = row.get("title", "")
                    if not n_uri or n_uri in visited:
                        continue
                    hop = ConnectionHop(current_title, n_title, "same_genre")
                    new_path = path + [hop]
                    if n_uri == uri_b:
                        return ConnectionPath(title_a, title_b, new_path, found=True)
                    visited.add(n_uri)
                    queue.append((n_uri, n_title, new_path))

        return ConnectionPath(source=title_a, target=title_b, found=False)

    # ── Neighbourhood graph ─────────────────────────────────────────────────

    def get_neighborhood(self, title: str, depth: int = 2) -> NetworkGraph:
        """Return a NetworkGraph of movies connected to ``title`` within ``depth`` hops.

        depth=1 → direct genre/director neighbours.
        depth=2 → their neighbours as well (can be large; capped at 60 nodes).
        """
        graph = NetworkGraph(center_title=title)
        info = _get_movie_info(title)
        if not info:
            return graph

        center_uri = info["movie"]
        try:
            runtime = int(info["runtime"]) if info.get("runtime") else None
        except (ValueError, TypeError):
            runtime = None
        center_node = NetworkNode(
            uri=center_uri,
            title=info.get("title", title),
            genre=info.get("genreName"),
            runtime=runtime,
        )
        graph.nodes.append(center_node)

        visited: set[str] = {center_uri}
        frontier: list[str] = [center_uri]
        frontier_info: dict[str, dict] = {center_uri: info}

        for _d in range(depth):
            next_frontier: list[str] = []
            for uri in frontier:
                movie_info = frontier_info.get(uri, {})
                genre = movie_info.get("genreName")
                director = movie_info.get("directorUri")

                neighbours: list[dict] = []
                if genre:
                    neighbours += _movies_by_genre(genre, visited, limit=20)
                if director:
                    neighbours += _movies_by_director(director, visited, limit=10)

                for row in neighbours:
                    n_uri = row.get("movie", "")
                    if not n_uri or n_uri in visited:
                        continue
                    try:
                        rating = float(row["rating"]) if row.get("rating") else None
                    except (ValueError, TypeError):
                        rating = None
                    try:
                        runtime = int(row["runtime"]) if row.get("runtime") else None
                    except (ValueError, TypeError):
                        runtime = None
                    try:
                        year = int(str(row["releaseDate"])[:4]) if row.get("releaseDate") else None
                    except (ValueError, TypeError):
                        year = None
                    node = NetworkNode(
                        uri=n_uri,
                        title=row.get("title", ""),
                        genre=row.get("genreName"),
                        rating=rating,
                        poster_url=row.get("posterUrl"),
                        description=row.get("description"),
                        runtime=runtime,
                        director=row.get("directorName") or None,
                        year=year,
                    )
                    graph.nodes.append(node)
                    rel = "same_genre" if genre and row.get("genreName") == genre else "same_director"
                    graph.edges.append(NetworkEdge(source_uri=uri, target_uri=n_uri, relation=rel))
                    visited.add(n_uri)
                    next_frontier.append(n_uri)
                    frontier_info[n_uri] = row

                    if len(graph.nodes) >= 60:
                        break
                if len(graph.nodes) >= 60:
                    break

            frontier = next_frontier
            if not frontier or len(graph.nodes) >= 60:
                break

        return graph

    # ── Centrality ranking ──────────────────────────────────────────────────

    def get_centrality_ranking(self, genre: str | None = None, limit: int = 20) -> list[dict]:
        """Return the most 'central' movies in the graph.

        Centrality is approximated by (rating + bridge:compatibilityScore) — highly
        rated and contextually compatible movies tend to be the most broadly
        connected.  When ``genre`` is specified only that genre is ranked.

        Returns raw SPARQL row dicts compatible with Movie.from_fuseki_row().
        """
        genre_filter = (
            f'  FILTER(?genreName = "{_esc(genre)}")\n' if genre else ""
        )
        safe_limit = max(1, min(100, int(limit)))
        query = (
            "PREFIX movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#>\n"
            "PREFIX bridge: <http://www.semanticweb.org/movierecommendation/ontologies/2025/bridge-ontology#>\n"
            "PREFIX schema1: <http://schema.org/>\n"
            "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
            "SELECT DISTINCT ?movie ?title ?genreName ?runtime ?rating ?imdbRating ?posterUrl\n"
            "                ?releaseDate ?compatibilityScore ?moodMatchScore ?socialMatchScore\n"
            "                ?energyMatchScore ?timeMatchScore ?kidFriendly ?description\n"
            "WHERE {\n"
            "  ?movie rdf:type movie:FeatureFilm ; movie:hasTitle ?title .\n"
            "  ?movie movie:hasMainGenre/movie:genreName ?genreName .\n"
            + genre_filter
            + "  OPTIONAL { ?movie movie:runtime ?runtime }\n"
            "  OPTIONAL { ?movie movie:hasAverageRating ?rating }\n"
            "  OPTIONAL { ?movie movie:hasIMDbRating ?imdbRating }\n"
            "  OPTIONAL { ?movie schema1:image ?posterUrl }\n"
            "  OPTIONAL { ?movie movie:releaseDate ?releaseDate }\n"
            "  OPTIONAL { ?movie bridge:compatibilityScore ?compatibilityScore }\n"
            "  OPTIONAL { ?movie bridge:moodMatchScore ?moodMatchScore }\n"
            "  OPTIONAL { ?movie bridge:socialMatchScore ?socialMatchScore }\n"
            "  OPTIONAL { ?movie bridge:energyMatchScore ?energyMatchScore }\n"
            "  OPTIONAL { ?movie bridge:timeMatchScore ?timeMatchScore }\n"
            "  OPTIONAL { ?movie bridge:isKidFriendly ?kidFriendly }\n"
            "  OPTIONAL { ?movie movie:hasPlotSummary ?description }\n"
            "}\n"
            "ORDER BY DESC(?rating) DESC(?compatibilityScore)\n"
            f"LIMIT {safe_limit}"
        )
        try:
            return execute_select_query(query)
        except Exception as exc:
            logger.error("get_centrality_ranking failed: %s", exc)
            return []


# ---------------------------------------------------------------------------
# Additional helper (not in main class to keep it testable in isolation)
# ---------------------------------------------------------------------------

def _get_movie_genre(movie_uri: str) -> str | None:
    """Fetch the primary genre name for a movie URI."""
    query = (
        _PREFIXES
        + "SELECT ?genreName\n"
        + "WHERE {\n"
        + f"  <{movie_uri}> movie:hasMainGenre/movie:genreName ?genreName .\n"
        + "}\n"
        + "LIMIT 1"
    )
    try:
        rows = execute_select_query(query)
        return rows[0].get("genreName") if rows else None
    except Exception:
        return None
