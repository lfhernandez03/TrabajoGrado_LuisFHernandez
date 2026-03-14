from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib import error, request

from app.core.fuseki_client import (
    execute_select_query,
    get_user_context_history,
    user_history_graph_exists,
)

BASE_URL = "http://127.0.0.1:8000/api/v1"
TEST_PASSWORD = "Test123456"


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


def export_results_json(
    checks: list[CheckResult],
    passed_count: int,
    total: int,
    user_id: str | None,
    snapshot_id: str | None,
) -> Path:
    reports_dir = Path(__file__).resolve().parent / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = reports_dir / f"roles_traceability_{timestamp}.json"

    payload = {
        "generatedAt": datetime.now().isoformat(),
        "summary": {
            "passed": passed_count,
            "total": total,
            "allPassed": passed_count == total,
        },
        "context": {
            "baseUrl": BASE_URL,
            "userId": user_id,
            "snapshotId": snapshot_id,
        },
        "checks": [
            {
                "name": item.name,
                "passed": item.passed,
                "detail": item.detail,
            }
            for item in checks
        ],
    }

    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def post_json(url: str, payload: dict, headers: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8")
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)

    req = request.Request(url, data=data, headers=req_headers, method="POST")
    try:
        with request.urlopen(req, timeout=60) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, {"error": body}


def get_json(url: str, headers: dict | None = None) -> tuple[int, dict]:
    req_headers = headers or {}
    req = request.Request(url, headers=req_headers, method="GET")
    try:
        with request.urlopen(req, timeout=60) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, {"error": body}


def graph_has_snapshot(snapshot_id: str, user_id: str) -> bool:
    query = f"""
PREFIX context: <http://www.semanticweb.org/movierecommendation/ontologies/2025/context-ontology#>
SELECT ?snapshot
WHERE {{
  GRAPH <http://users/{user_id}/history> {{
    ?snapshot a context:ContextSnapshot ;
              context:snapshotID \"{snapshot_id}\"^^<http://www.w3.org/2001/XMLSchema#string> .
  }}
}}
LIMIT 1
"""
    rows = execute_select_query(query)
    return len(rows) > 0


def session_graph_exists(snapshot_id: str) -> bool:
    query = f"""
SELECT ?s
WHERE {{
  GRAPH <http://session/{snapshot_id}> {{ ?s ?p ?o }}
}}
LIMIT 1
"""
    rows = execute_select_query(query)
    return len(rows) > 0


def main() -> int:
    checks: list[CheckResult] = []

    email = f"roles.trace.{int(datetime.now().timestamp())}@mail.com"
    register_payload = {
        "email": email,
        "password": TEST_PASSWORD,
        "name": "Roles Traceability Test",
    }

    status, register_response = post_json(f"{BASE_URL}/auth/register", register_payload)
    if status >= 400:
        print("[FATAL] register failed", register_response)
        return 1

    token = register_response.get("access_token")
    user = register_response.get("user", {})
    user_id = user.get("id")
    headers = {"Authorization": f"Bearer {token}"}

    checks.append(
        CheckResult(
            name="Auth register",
            passed=bool(token and user_id),
            detail=f"status={status}, user_id={user_id}",
        )
    )

    debug_query = "Quiero algo relajado para ver en familia"
    status, debug_response = post_json(
        f"{BASE_URL}/recommendation/debug",
        {"query": debug_query},
        headers=headers,
    )

    debug_block = debug_response.get("debug", {}) if isinstance(debug_response, dict) else {}
    recommendation_block = (
        debug_response.get("recommendation", {}) if isinstance(debug_response, dict) else {}
    )
    snapshot_id = (
        recommendation_block.get("contextExtracted", {}) or {}
    ).get("snapshotID")

    checks.append(
        CheckResult(
            name="Recommendation debug call",
            passed=status == 200,
            detail=f"status={status}",
        )
    )

    checks.append(
        CheckResult(
            name="Rol 1 injection flag",
            passed=bool(debug_block.get("contextGraphInjected")),
            detail=f"contextGraphInjected={debug_block.get('contextGraphInjected')}",
        )
    )

    history_exists = user_history_graph_exists(user_id)
    history_rows = get_user_context_history(user_id, limit=20)

    checks.append(
        CheckResult(
            name="Rol 2 history graph exists",
            passed=history_exists,
            detail=f"history_exists={history_exists}",
        )
    )

    checks.append(
        CheckResult(
            name="Rol 2 history rows",
            passed=len(history_rows) > 0,
            detail=f"rows={len(history_rows)}",
        )
    )

    if snapshot_id:
        checks.append(
            CheckResult(
                name="Rol 2 snapshot archived",
                passed=graph_has_snapshot(snapshot_id, user_id),
                detail=f"snapshot_id={snapshot_id}",
            )
        )

        checks.append(
            CheckResult(
                name="Rol 1 session cleanup",
                passed=not session_graph_exists(snapshot_id),
                detail=f"session_graph=http://session/{snapshot_id}",
            )
        )
    else:
        checks.append(
            CheckResult(
                name="Snapshot id present",
                passed=False,
                detail="No snapshotID in recommendation context",
            )
        )

    status, activity_response = get_json(f"{BASE_URL}/recommendation/activity", headers=headers)
    debug_payload = activity_response.get("debugPayload", {}) if isinstance(activity_response, dict) else {}

    checks.append(
        CheckResult(
            name="Activity recommendation call",
            passed=status == 200,
            detail=f"status={status}",
        )
    )

    checks.append(
        CheckResult(
            name="Activity profile source",
            passed=debug_payload.get("profileSource") in {"fuseki_history", "cold_start"},
            detail=f"debugPayload={debug_payload}",
        )
    )

    print("\n=== Roles Traceability Report ===")
    passed_count = 0
    for item in checks:
        tag = "PASS" if item.passed else "FAIL"
        print(f"[{tag}] {item.name} -> {item.detail}")
        if item.passed:
            passed_count += 1

    total = len(checks)
    print(f"\nSummary: {passed_count}/{total} checks passed")

    report_path = export_results_json(
        checks=checks,
        passed_count=passed_count,
        total=total,
        user_id=user_id,
        snapshot_id=snapshot_id,
    )
    print(f"JSON report: {report_path}")

    return 0 if passed_count == total else 2


if __name__ == "__main__":
    sys.exit(main())
