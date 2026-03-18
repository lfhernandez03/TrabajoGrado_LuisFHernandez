from __future__ import annotations

import base64
import json
import logging
import time
from urllib import error, parse, request

from app.core.config import settings


logger = logging.getLogger(__name__)


class FusekiQueryError(RuntimeError):
    pass


def _build_query_endpoint() -> str:
    base = settings.fuseki_url.rstrip("/")
    dataset = settings.fuseki_dataset.strip("/")
    return f"{base}/{dataset}/query"


def _build_update_endpoint() -> str:
    endpoint = _build_query_endpoint().rstrip("/")
    if endpoint.endswith("/sparql"):
        return f"{endpoint[:-7]}/update"
    if endpoint.endswith("/query"):
        return f"{endpoint[:-6]}/update"
    return f"{endpoint}/update"


def _build_auth_headers() -> dict[str, str]:
    user = settings.fuseki_user.strip()
    password = settings.fuseki_password
    if not user:
        return {}
    credentials = f"{user}:{password}".encode("utf-8")
    token = base64.b64encode(credentials).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def execute_select_query(sparql_query: str) -> list[dict[str, str]]:
    endpoint = _build_query_endpoint()
    payload = parse.urlencode({"query": sparql_query}).encode("utf-8")

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/sparql-results+json",
    }
    headers.update(_build_auth_headers())

    req = request.Request(
        endpoint,
        data=payload,
        headers=headers,
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


def execute_update_query(sparql_update: str) -> bool:
    endpoint = _build_update_endpoint()
    payload = sparql_update.encode("utf-8")
    headers = {
        "Content-Type": "application/sparql-update",
    }
    headers.update(_build_auth_headers())

    req = request.Request(
        endpoint,
        data=payload,
        headers=headers,
        method="POST",
    )

    retries = max(0, settings.fuseki_max_retries)
    timeout_seconds = max(1, settings.fuseki_timeout_seconds)
    last_error: Exception | None = None

    for attempt in range(retries + 1):
        try:
            with request.urlopen(req, timeout=timeout_seconds) as response:
                return int(getattr(response, "status", 0)) in (200, 204)
        except (error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(0.2 * (attempt + 1))
                continue
            logger.error(
                "Fuseki update failed at %s after %d retries: %s",
                endpoint,
                retries + 1,
                exc,
            )
            return False
        except Exception as exc:
            logger.error("Fuseki update failed at %s: %s", endpoint, exc)
            return False


def copy_graph_to_user_history(snapshot_id: str, user_id: str) -> bool:
    try:
        return execute_update_query(
            f"ADD SILENT <http://session/{snapshot_id}> TO <http://users/{user_id}/history>"
        )
    except Exception as exc:
        logger.error(
            "Failed to copy session graph %s into user history %s: %s",
            snapshot_id,
            user_id,
            exc,
        )
        return False


def get_user_context_history(user_id: str, limit: int = 20) -> list[dict]:
    safe_limit = max(1, min(200, int(limit)))
    query = f"""
PREFIX context: <http://www.semanticweb.org/movierecommendation/ontologies/2025/context-ontology#>

SELECT ?moodDescription ?companionType ?desiredEnergyLevel
       ?availableTime ?snapshotID ?requestTimestamp
WHERE {{
  GRAPH <http://users/{user_id}/history> {{
    ?snapshot a context:ContextSnapshot ;
              context:snapshotID ?snapshotID .
    OPTIONAL {{ ?snapshot context:requestTimestamp ?requestTimestamp }}
    OPTIONAL {{
      ?snapshot context:feelsMood ?mood .
      ?mood context:moodDescription ?moodDescription .
      OPTIONAL {{ ?mood context:desiredEnergyLevel ?desiredEnergyLevel }}
    }}
    OPTIONAL {{
      ?snapshot context:withCompanion ?social .
      ?social context:companionType ?companionType .
    }}
    OPTIONAL {{
      ?snapshot context:hasRequirement ?req .
      ?req context:availableTime ?availableTime .
    }}
  }}
}}
ORDER BY DESC(?requestTimestamp)
LIMIT {safe_limit}
"""
    try:
        return execute_select_query(query)
    except Exception as exc:
        logger.error("Failed to get user context history for %s: %s", user_id, exc)
        return []


def user_history_graph_exists(user_id: str) -> bool:
    query = f"ASK {{ GRAPH <http://users/{user_id}/history> {{ ?s ?p ?o }} }}"
    try:
        endpoint = _build_query_endpoint()
        payload = parse.urlencode({"query": query}).encode("utf-8")
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/sparql-results+json",
        }
        headers.update(_build_auth_headers())

        req = request.Request(
            endpoint,
            data=payload,
            headers=headers,
            method="POST",
        )

        timeout_seconds = max(1, settings.fuseki_timeout_seconds)
        with request.urlopen(req, timeout=timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
            return bool(body.get("boolean", False))
    except Exception as exc:
        logger.error("Failed to check user history graph for %s: %s", user_id, exc)
        return False
