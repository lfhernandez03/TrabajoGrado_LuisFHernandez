from __future__ import annotations

import json
import time
from urllib import error, parse, request

from app.core.config import settings


class FusekiQueryError(RuntimeError):
    pass


def _build_query_endpoint() -> str:
    base = settings.fuseki_url.rstrip("/")
    dataset = settings.fuseki_dataset.strip("/")
    return f"{base}/{dataset}/query"


def execute_select_query(sparql_query: str) -> list[dict[str, str]]:
    endpoint = _build_query_endpoint()
    payload = parse.urlencode({"query": sparql_query}).encode("utf-8")

    req = request.Request(
        endpoint,
        data=payload,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/sparql-results+json",
        },
        method="POST",
    )

    retries = max(0, settings.fuseki_max_retries)
    timeout_seconds = max(1, settings.fuseki_timeout_seconds)
    last_error: Exception | None = None

    for attempt in range(retries + 1):
        try:
            with request.urlopen(req, timeout=timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
                break
        except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(0.2 * (attempt + 1))
                continue
            raise FusekiQueryError(
                f"Failed to query Fuseki endpoint ({endpoint})"
            ) from exc

    if last_error is not None and "body" not in locals():
        raise FusekiQueryError(f"Failed to query Fuseki endpoint ({endpoint})")

    bindings = body.get("results", {}).get("bindings", [])
    parsed: list[dict[str, str]] = []
    for row in bindings:
        row_values: dict[str, str] = {}
        for key, value in row.items():
            if isinstance(value, dict) and "value" in value:
                row_values[key] = str(value["value"])
        parsed.append(row_values)
    return parsed
