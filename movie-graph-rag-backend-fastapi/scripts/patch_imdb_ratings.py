"""
Patches Fuseki with movie:hasIMDbRating triples from the source CSV.

The rdf_generator.py intentionally collapses all ratings into a single
movie:hasRating property to simplify Gemini queries, so movie:hasIMDbRating
was never written. This script reads the source CSV, reconstructs each
movie's URI (using the same logic as RDFMovieGenerator), and inserts
movie:hasIMDbRating triples for every movie that has an IMDb rating.

Run once from the backend venv:
    .\.venv\Scripts\python scripts/patch_imdb_ratings.py
"""

import os
import re
import base64
import logging
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
FUSEKI_URL: str = os.getenv("FUSEKI_URL", "http://localhost:3030")
FUSEKI_DATASET: str = os.getenv("FUSEKI_DATASET", "Cine")
FUSEKI_USER: str = os.getenv("FUSEKI_USER", "admin")
FUSEKI_PASSWORD: str = os.getenv("FUSEKI_PASSWORD", "admin")

MOVIE_DATA_NS = "http://www.semanticweb.org/movierecommendation/data/movie/"
MOVIE_ONT_NS = "http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#"

CSV_PATH = Path(__file__).resolve().parents[2] / (
    "movie-graph-rag-ontologies/data/data/processed/movies_enriched.csv"
)

BATCH_SIZE = 200  # movies per SPARQL UPDATE


# ── Helpers (mirrors RDFMovieGenerator logic) ─────────────────────────────────

def _sanitize_uri(text: str) -> str | None:
    if pd.isna(text) or str(text).strip() == "":
        return None
    text = str(text).strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s]+", "_", text)
    return quote(text)


def _movie_uri(movie_id: str | int, title: str) -> str | None:
    safe = _sanitize_uri(title)
    if not safe:
        return None
    return f"{MOVIE_DATA_NS}movie_{movie_id}_{safe}"


def _auth_header() -> dict:
    token = base64.b64encode(f"{FUSEKI_USER}:{FUSEKI_PASSWORD}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def _update_url() -> str:
    return f"{FUSEKI_URL.rstrip('/')}/{FUSEKI_DATASET.strip('/')}/update"


def fuseki_update(sparql: str) -> None:
    resp = requests.post(
        _update_url(),
        data=sparql.encode(),
        headers={**_auth_header(), "Content-Type": "application/sparql-update"},
        timeout=60,
    )
    if not resp.ok:
        raise RuntimeError(f"Fuseki UPDATE failed {resp.status_code}: {resp.text[:300]}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if not CSV_PATH.exists():
        log.error("CSV not found: %s", CSV_PATH)
        return

    log.info("Loading CSV: %s", CSV_PATH.name)
    df = pd.read_csv(CSV_PATH, dtype={"movieId": str})

    # Keep only rows with a valid imdb_rating
    df["_imdb"] = pd.to_numeric(df["imdb_rating"], errors="coerce")
    df_valid = df[df["_imdb"].notna()].copy()
    log.info("Movies with imdb_rating in CSV: %d / %d", len(df_valid), len(df))

    # Build (uri, rating) pairs
    pairs: list[tuple[str, float]] = []
    for _, row in df_valid.iterrows():
        uri = _movie_uri(row["movieId"], row["clean_title"])
        if uri:
            pairs.append((uri, float(row["_imdb"])))

    log.info("Reconstructed %d movie URIs", len(pairs))

    # First delete any stale hasIMDbRating triples
    log.info("Deleting existing hasIMDbRating triples…")
    delete_sparql = (
        f"PREFIX movie: <{MOVIE_ONT_NS}>\n"
        "DELETE WHERE { ?m movie:hasIMDbRating ?v }"
    )
    fuseki_update(delete_sparql)
    log.info("Delete done.")

    # Insert in batches
    inserted = 0
    for i in range(0, len(pairs), BATCH_SIZE):
        batch = pairs[i : i + BATCH_SIZE]
        triples = "\n  ".join(
            f"<{uri}> movie:hasIMDbRating \"{rating}\"^^<http://www.w3.org/2001/XMLSchema#float> ."
            for uri, rating in batch
        )
        sparql = (
            f"PREFIX movie: <{MOVIE_ONT_NS}>\n"
            f"INSERT DATA {{\n  {triples}\n}}"
        )
        fuseki_update(sparql)
        inserted += len(batch)
        log.info("  Inserted %d / %d", inserted, len(pairs))

    log.info("Done. %d movie:hasIMDbRating triples written to Fuseki.", inserted)


if __name__ == "__main__":
    main()
