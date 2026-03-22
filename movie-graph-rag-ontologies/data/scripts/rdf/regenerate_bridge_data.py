#!/usr/bin/env python3
"""
Regenerate bridge_data.ttl with correct predicate structure.

Reads:
  - bridge_data.ttl (via --bridge)
  - movies_data.ttl (via --movies) — optional, for certification data

Outputs:
  - bridge_data.ttl with enriched predicates

Features:
  - Parses compatibleMood, compatibleCompanion, compatibleEnergyLevel
  - Infers compatibleTimeOfDay from mood/companion values
  - Calculates timeMatchScore (0.0-1.0)
  - Computes isKidFriendly using certification + genre signals
"""

import argparse
import re
import tempfile
from pathlib import Path


# Map mood values to compatible times of day
MOOD_TO_TIME = {
    "feliz": ["morning", "afternoon"],
    "relajado": ["morning", "afternoon"],
    "aburrido": ["morning", "afternoon"],
    "emocionado": ["afternoon", "evening"],
    "estresado": ["evening", "night"],
    "nervioso": ["evening", "night"],
    "curioso": ["afternoon", "evening"],
    "concentrado": ["evening"],
    "triste": ["evening", "night"],
    "romantico": ["evening", "night"],
    "nostalgico": ["afternoon", "evening"],
    "aventurero": ["afternoon", "evening"],
}

# Map companion values to compatible times
COMPANION_TO_TIME = {
    "solo": ["afternoon", "evening", "night"],
    "pareja": ["evening", "night"],
    "familia": ["morning", "afternoon"],
    "familia con ninos": ["morning", "afternoon"],
    "amigos": ["afternoon", "evening"],
}

# Define ordering of time of day (for deduplication)
TIME_ORDER = ["morning", "afternoon", "evening", "night"]

# Genre-to-mood mapping (simplified from full bridge generator)
GENRE_TO_MOODS = {
    "Comedy": ["feliz", "relajado", "aburrido"],
    "Romance": ["romantico", "feliz", "emocionado"],
    "Drama": ["concentrado", "triste", "curioso"],
    "Action": ["emocionado", "estresado", "aventurero"],
    "Thriller": ["estresado", "emocionado", "curioso"],
    "Horror": ["nervioso", "emocionado", "aventurero"],
    "Science Fiction": ["curioso", "concentrado", "aventurero"],
    "Fantasy": ["aventurero", "curioso", "nostalgico"],
    "Animation": ["feliz", "nostalgico", "relajado"],
    "Documentary": ["curioso", "concentrado", "aburrido"],
    "Crime": ["curioso", "estresado", "concentrado"],
    "Mystery": ["curioso", "concentrado", "emocionado"],
    "Adventure": ["aventurero", "emocionado", "feliz"],
    "War": ["concentrado", "estresado", "curioso"],
    "History": ["curioso", "concentrado", "nostalgico"],
    "Music": ["feliz", "emocionado", "nostalgico"],
    "Family": ["feliz", "relajado", "nostalgico"],
}

# Genre-to-companion mapping
GENRE_TO_COMPANIONS = {
    "Romance": ["pareja", "solo"],
    "Comedy": ["amigos", "familia", "pareja"],
    "Horror": ["amigos", "pareja", "solo"],
    "Action": ["amigos", "solo"],
    "Drama": ["solo", "pareja"],
    "Animation": ["familia", "familia con ninos"],
    "Family": ["familia", "familia con ninos"],
    "Documentary": ["solo", "pareja"],
    "Science Fiction": ["amigos", "solo"],
    "Fantasy": ["amigos", "familia"],
    "Adventure": ["amigos", "familia"],
    "Thriller": ["amigos", "pareja", "solo"],
    "Crime": ["solo", "amigos"],
    "Mystery": ["solo", "pareja"],
}

# Genre-to-energy mapping
GENRE_TO_ENERGY = {
    "Horror": ["alto"],
    "Thriller": ["alto", "medio"],
    "Romance": ["bajo", "medio"],
    "Comedy": ["medio"],
    "Action": ["alto"],
    "Drama": ["bajo", "medio"],
    "Documentary": ["bajo"],
    "Animation": ["medio", "bajo"],
    "Family": ["medio"],
    "Science Fiction": ["medio", "alto"],
    "Fantasy": ["medio", "alto"],
    "Adventure": ["alto", "medio"],
    "Crime": ["medio"],
    "Mystery": ["medio", "bajo"],
    "War": ["medio", "alto"],
    "Music": ["medio", "alto"],
}

# Base scoring constants
BASE_SCORE = {
    "mood": 0.9,
    "companion": 0.9,
    "energy": 0.9,
}

# Kid-friendly certification logic
KID_FRIENDLY_CERTS = {"G"}
PG_KID_GENRES = {"Animation", "Children"}
KID_FRIENDLY_FALLBACK_GENRES = {"Animation", "Children", "Family"}
ADULT_CERTS = {"R", "NC-17", "PG-13"}


def _is_kid_friendly(genres: list[str], certification: str | None) -> bool:
    """Determine kid-friendliness using certification as primary signal.

    Rules:
    - G                    → always True
    - PG + Animation/Children genre → True
    - PG without those genres → False
    - PG-13, R, NC-17      → always False
    - No certification     → True if Animation, Children, or Family present
    """
    if certification in KID_FRIENDLY_CERTS:
        return True
    if certification == "PG":
        return bool(set(genres) & PG_KID_GENRES)
    if certification in ADULT_CERTS:
        return False
    return bool(set(genres) & KID_FRIENDLY_FALLBACK_GENRES)


def parse_bridge_data(path: Path) -> dict:
    """Parse bridge_data.ttl and return movie blocks.
    
    Returns:
        {movie_uri: {parsed movie data}}
    """
    content = path.read_text(encoding="utf-8")
    movies = {}

    # Split into movie blocks
    blocks = re.split(r"\n(?=moviedata:movie_)", content)
    for block in blocks:
        uri_match = re.match(r"(moviedata:\S+)\s+a\s+movie:Movie", block)
        if not uri_match:
            continue

        uri = uri_match.group(1)
        movie = {
            "uri": uri,
            "block": block,
            "moods": [],
            "companions": [],
            "energy": [],
            "main_genre": "",
        }

        # Extract existing predicates
        moods = re.findall(r'bridge:bestCompatibleMood "([^"]+)"', block)
        if moods:
            movie["moods"] = moods

        companions = re.findall(r'bridge:bestCompatibleCompanion "([^"]+)"', block)
        if companions:
            movie["companions"] = companions

        energy = re.findall(r'bridge:bestCompatibleEnergyLevel "([^"]+)"', block)
        if energy:
            movie["energy"] = energy

        # Extract main genre (for enrichment if needed)
        genre_match = re.search(r'movie:hasMainGenre\s+(?:genre:(\w[\w-]*)|[^;]+)', block)
        if genre_match:
            movie["main_genre"] = genre_match.group(1) or ""

        movies[uri] = movie

    return movies


def parse_movies_data(path: Path) -> tuple[dict[str, list[str]], dict[str, str]]:
    """Parse movies_data.ttl for genres and certifications.

    Returns:
        genre_map: {movie_uri: [genre_name_strings]}
        cert_map:  {movie_uri: certification_string}  e.g. "G", "PG", "R"
    """
    content = path.read_text(encoding="utf-8")
    genre_map: dict[str, list[str]] = {}
    cert_map: dict[str, str] = {}

    blocks = re.split(r"\n(?=moviedata:movie_)", content)
    for block in blocks:
        uri_match = re.match(r"(moviedata:\S+)\s+a\s+movie:FeatureFilm", block)
        if not uri_match:
            continue

        uri = uri_match.group(1)

        genres = re.findall(r"genre:(\w[\w-]*)", block)
        if genres:
            genre_map[uri] = list(set(genres))

        cert_match = re.search(
            r"movie:hasCertification\s+moviedata:certification_(\S+)", block
        )
        if cert_match:
            cert_map[uri] = cert_match.group(1).rstrip(".")

    return genre_map, cert_map


def infer_times_of_day(moods: list[str], companions: list[str]) -> list[str]:
    """Infer compatible times of day from moods and companions."""
    times_set = set()

    for mood in moods:
        if mood in MOOD_TO_TIME:
            times_set.update(MOOD_TO_TIME[mood])

    for companion in companions:
        if companion in COMPANION_TO_TIME:
            times_set.update(COMPANION_TO_TIME[companion])

    # Default to all times if no inference possible
    if not times_set:
        times_set = set(TIME_ORDER)

    # Return in canonical order
    return sorted(times_set, key=lambda t: TIME_ORDER.index(t))


def enrich(
    movie: dict, genres: list[str], certification: str | None
) -> dict:
    """Enrich movie with inferred predicates."""
    enriched = movie.copy()

    # Infer times of day from existing moods/companions
    times = infer_times_of_day(movie["moods"], movie["companions"])
    enriched["times"] = times

    # Compute kid-friendly flag
    is_kid = _is_kid_friendly(genres, certification)
    enriched["is_kid_friendly"] = is_kid

    return enriched


def to_ttl(movie: dict) -> str:
    """Convert enriched movie to TTL block."""
    lines = [f"{movie['uri']} a movie:Movie ;"]

    # Add title if available
    title_match = re.search(
        r"movie:hasTitle\s+[\"']([^\"']+)[\"']", movie["block"]
    )
    if title_match:
        title = title_match.group(1)
        lines.append(f'    movie:hasTitle "{title}" ;')

    # Add runtime if available
    runtime_match = re.search(r"movie:runtime\s+(\d+)", movie["block"])
    if runtime_match:
        runtime = runtime_match.group(1)
        lines.append(f"    movie:runtime {runtime} ;")

    # Add moods
    for mood in movie["moods"]:
        lines.append(f'    bridge:compatibleMood "{mood}" ;')

    # Add companions
    for companion in movie["companions"]:
        lines.append(f'    bridge:compatibleCompanion "{companion}" ;')

    # Add energy levels
    for energy in movie["energy"]:
        lines.append(f'    bridge:compatibleEnergyLevel "{energy}" ;')

    # Add times of day
    for time_of_day in movie["times"]:
        lines.append(f'    bridge:compatibleTimeOfDay "{time_of_day}" ;')

    # Add timeMatchScore
    time_match_score = round(len(movie["times"]) / 4.0, 2)
    lines.append(f'    bridge:timeMatchScore "{time_match_score}"^^xsd:float ;')

    # Add isKidFriendly
    kid_friendly_str = "true" if movie["is_kid_friendly"] else "false"
    lines.append(f"    bridge:isKidFriendly {kid_friendly_str} .")

    return "\n".join(lines)


def _validate_output(path: Path) -> None:
    """Print validation report for output file."""
    content = path.read_text(encoding="utf-8")

    total = content.count("a movie:Movie ;")
    kid_true = content.count("bridge:isKidFriendly true")
    familia_ninos = len(re.findall(r'bridge:compatibleCompanion "familia con ninos"', content))
    has_mood = len(re.findall(r"bridge:compatibleMood ", content))
    has_companion = len(re.findall(r"bridge:compatibleCompanion ", content))
    has_energy = len(re.findall(r"bridge:compatibleEnergyLevel ", content))
    has_time = len(re.findall(r"bridge:compatibleTimeOfDay ", content))
    has_time_score = content.count("bridge:timeMatchScore ")

    def unique_vals(predicate: str) -> list[str]:
        return sorted(set(re.findall(rf'bridge:{predicate} "([^"]+)"', content)))

    print("\n=== VALIDATION REPORT ===")
    print(f"Total movie blocks:                {total}")
    print(f"compatibleMood triples:            {has_mood}")
    print(f"compatibleCompanion triples:       {has_companion}")
    print(f"compatibleEnergyLevel triples:     {has_energy}")
    print(f"compatibleTimeOfDay triples:       {has_time}")
    print(f"timeMatchScore triples:            {has_time_score}")
    print(f"isKidFriendly true:                {kid_true}")
    print(f"'familia con ninos' triples:       {familia_ninos}")
    print(f"Unique moods:      {unique_vals('compatibleMood')}")
    print(f"Unique companions: {unique_vals('compatibleCompanion')}")
    print(f"Unique energy:     {unique_vals('compatibleEnergyLevel')}")
    print(f"Unique times:      {unique_vals('compatibleTimeOfDay')}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Regenerate bridge_data.ttl with correct predicate structure"
    )
    parser.add_argument("--bridge", required=True, help="Path to bridge_data.ttl")
    parser.add_argument(
        "--movies",
        required=True,
        help="Path to movies_data.ttl (for certification data)",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to output TTL file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run enrichment and print validation without writing output file",
    )
    args = parser.parse_args()

    bridge_path = Path(args.bridge)
    movies_path = Path(args.movies)
    output_path = Path(args.output)

    print(f"Reading {bridge_path}...")
    bridge_movies = parse_bridge_data(bridge_path)
    print(f"  Found {len(bridge_movies)} movie blocks")

    genre_map: dict[str, list[str]] = {}
    cert_map: dict[str, str] = {}
    if movies_path.exists():
        print(f"Reading {movies_path}...")
        genre_map, cert_map = parse_movies_data(movies_path)
        print(f"  Found genres for {len(genre_map)} movies")
        print(f"  Found certifications for {len(cert_map)} movies")
    else:
        print(f"WARNING: {movies_path} not found — using mood/companion signals only")

    print("Enriching...")
    ttl_blocks: list[str] = []
    stats = {"kid": 0, "familia_ninos": 0, "total": 0}

    for uri, movie in bridge_movies.items():
        genres = genre_map.get(uri, [])
        certification = cert_map.get(uri)
        enriched = enrich(movie, genres, certification)
        if enriched["is_kid_friendly"]:
            stats["kid"] += 1
        if "familia con ninos" in enriched["companions"]:
            stats["familia_ninos"] += 1
        stats["total"] += 1
        ttl_blocks.append(to_ttl(enriched))

    header = (
        "@prefix bridge: <http://www.semanticweb.org/movierecommendation/ontologies/2025/bridge-ontology#> .\n"
        "@prefix movie: <http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#> .\n"
        "@prefix moviedata: <http://www.semanticweb.org/movierecommendation/data/movie/> .\n"
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n"
    )
    full_content = header + "\n" + "\n\n".join(ttl_blocks) + "\n"

    if args.dry_run:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ttl", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(full_content)
            tmp_path = Path(tmp.name)
        print("[DRY RUN] No output file written.")
        _validate_output(tmp_path)
        tmp_path.unlink()
    else:
        output_path.write_text(full_content, encoding="utf-8")
        print(f"\nOutput written to: {output_path}")
        print(
            f"  Total: {stats['total']} | Kid-friendly: {stats['kid']} | Familia con ninos: {stats['familia_ninos']}"
        )
        _validate_output(output_path)


if __name__ == "__main__":
    main()
