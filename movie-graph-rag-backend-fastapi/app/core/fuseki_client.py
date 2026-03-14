from __future__ import annotations

import json
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

    try:
        with request.urlopen(req, timeout=25) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise FusekiQueryError("Failed to query Fuseki endpoint") from exc

    bindings = body.get("results", {}).get("bindings", [])
    parsed: list[dict[str, str]] = []
    for row in bindings:
        row_values: dict[str, str] = {}
        for key, value in row.items():
            if isinstance(value, dict) and "value" in value:
                row_values[key] = str(value["value"])
        parsed.append(row_values)
    return parsed
