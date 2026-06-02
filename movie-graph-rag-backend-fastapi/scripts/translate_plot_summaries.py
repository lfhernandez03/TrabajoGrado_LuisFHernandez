"""
Translates Spanish plot summaries in movies_data.ttl to English using Google Translate
(via deep-translator, free, no API key required).

Summaries are grouped into ~4500-char chunks to maximise throughput.
Progress is saved after every chunk — safe to interrupt and re-run.

Usage:
    py translate_plot_summaries.py               # translate everything remaining
    py translate_plot_summaries.py --offset 500  # resume from entry 500
    py translate_plot_summaries.py --dry-run     # preview without writing
"""
from __future__ import annotations

import argparse
import os
import re
import time

from deep_translator import GoogleTranslator

TTL_PATH = os.path.join(
    os.path.dirname(__file__),
    "../../movie-graph-rag-ontologies/data/ontologies/instances/movies_data.ttl",
)

MAX_CHARS_PER_REQUEST = 4500   # Google Translate limit is 5000; leave headroom
SEPARATOR = "\n||||\n"         # Unlikely to appear in plot summaries
SLEEP_BETWEEN_REQUESTS = 0.5  # seconds — avoids soft rate-limiting


def looks_english(text: str) -> bool:
    spanish_chars = sum(text.count(c) for c in "áéíóúüñÁÉÍÓÚÜÑ¿¡")
    return spanish_chars == 0


def extract_summaries(content: str) -> list[tuple[int, str]]:
    """Return (line_index, raw_value) for every hasPlotSummary line."""
    results = []
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if "hasPlotSummary" not in line:
            continue
        m = re.search(r'movie:hasPlotSummary\s+"((?:[^"\\]|\\.)*)"\s*[;.]', line)
        if m:
            results.append((i, m.group(1)))
    return results


def build_chunks(entries: list[tuple[int, str]]) -> list[list[tuple[int, str]]]:
    """Group entries into chunks that stay within MAX_CHARS_PER_REQUEST."""
    chunks: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    current_len = 0

    for line_idx, text in entries:
        entry_len = len(text) + len(SEPARATOR)
        if current and current_len + entry_len > MAX_CHARS_PER_REQUEST:
            chunks.append(current)
            current = []
            current_len = 0
        current.append((line_idx, text))
        current_len += entry_len

    if current:
        chunks.append(current)
    return chunks


def translate_chunk(texts: list[str], translator: GoogleTranslator) -> list[str]:
    """Translate a batch of texts joined by the separator, then split back."""
    joined = SEPARATOR.join(texts)
    translated = translator.translate(joined)
    parts = translated.split("||||")
    # Strip whitespace/newlines added around the separator
    return [p.strip().strip("\n") for p in parts]


def escape_turtle(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("\r", " ")


def save(ttl_path: str, lines: list[str]) -> None:
    with open(ttl_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offset", type=int, default=0, help="Skip first N non-English entries")
    parser.add_argument("--dry-run", action="store_true", help="Translate but do not write to file")
    args = parser.parse_args()

    ttl_path = os.path.abspath(TTL_PATH)
    print(f"Reading: {ttl_path}")
    with open(ttl_path, "r", encoding="utf-8") as f:
        content = f.read()

    all_summaries = extract_summaries(content)
    print(f"Total hasPlotSummary entries: {len(all_summaries)}")

    to_translate = [(idx, val) for idx, val in all_summaries if not looks_english(val)]
    print(f"Entries needing translation: {len(to_translate)}")

    chunk_slice = to_translate[args.offset:]
    chunks = build_chunks(chunk_slice)
    print(f"Chunks to process: {len(chunks)} (offset={args.offset})")

    if not chunks:
        print("Nothing to translate.")
        return

    translator = GoogleTranslator(source="es", target="en")
    lines = content.split("\n")
    translated_count = 0
    errors = 0

    for chunk_idx, chunk in enumerate(chunks):
        texts = [val for _, val in chunk]
        chunk_num = chunk_idx + 1

        print(f"  Chunk {chunk_num}/{len(chunks)}: {len(chunk)} entries, "
              f"{sum(len(t) for t in texts)} chars...", end=" ", flush=True)

        try:
            translations = translate_chunk(texts, translator)
        except Exception as exc:
            print(f"ERROR: {exc}")
            errors += len(chunk)
            time.sleep(3)
            continue

        if len(translations) != len(chunk):
            print(f"WARNING: expected {len(chunk)}, got {len(translations)} — skipping")
            errors += len(chunk)
            continue

        for (line_idx, _original), translation in zip(chunk, translations):
            safe = escape_turtle(translation)
            old_line = lines[line_idx]
            new_line = re.sub(
                r'(movie:hasPlotSummary\s+)"(?:[^"\\]|\\.)*"(\s*[;.])',
                lambda m, s=safe: f'{m.group(1)}"{s}"{m.group(2)}',
                old_line,
                count=1,
            )
            lines[line_idx] = new_line
            translated_count += 1

        if not args.dry_run:
            save(ttl_path, lines)

        print(f"saved ({args.offset + translated_count}/{len(to_translate)} total done)")
        time.sleep(SLEEP_BETWEEN_REQUESTS)

    print(f"\nFinished. Translated: {translated_count}, Errors: {errors}")
    if args.dry_run:
        print("DRY RUN — no changes written to disk.")


if __name__ == "__main__":
    main()
