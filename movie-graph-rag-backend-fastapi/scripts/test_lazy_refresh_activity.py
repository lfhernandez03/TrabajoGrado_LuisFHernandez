from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from datetime import datetime, timezone
from urllib import error, request


def _http_json(
    method: str,
    url: str,
    payload: dict | None = None,
    token: str | None = None,
) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    req = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} {method} {url}\n{body}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Smoke test for lazy refresh activity flow: "
            "CACHE_HIT -> RECALCULATED -> CACHE_HIT"
        )
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/api/v1")
    parser.add_argument("--password", default="Test1234!")
    parser.add_argument(
        "--json-out",
        default=None,
        help=(
            "Optional output path for JSON report. "
            "If omitted, report is stored in scripts/reports/."
        ),
    )
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    email = f"lazy_script_{stamp}@example.com"

    print(f"[INFO] Registering user: {email}")
    register_payload = {
        "name": "Lazy Refresh Script",
        "email": email,
        "password": args.password,
    }
    register = _http_json("POST", f"{base}/auth/register", register_payload)
    token = register.get("access_token")
    if not token:
        print("[FAIL] access_token not returned by /auth/register")
        return 1

    print("[INFO] Calling /recommendation/activity twice (baseline)")
    call1 = _http_json("GET", f"{base}/recommendation/activity", token=token)
    call2 = _http_json("GET", f"{base}/recommendation/activity", token=token)

    snap1 = (call1.get("contextExtracted") or {}).get("snapshotID")
    snap2 = (call2.get("contextExtracted") or {}).get("snapshotID")

    print("[INFO] Adding 3 favorites")
    favorites = [
        {
            "uri": f"urn:test:movie:{stamp}:1",
            "title": "Matrix",
            "genres": ["Action", "Science Fiction"],
            "rating": 8.7,
            "year": 1999,
            "runtime": 136,
        },
        {
            "uri": f"urn:test:movie:{stamp}:2",
            "title": "Interstellar",
            "genres": ["Science Fiction", "Drama"],
            "rating": 8.6,
            "year": 2014,
            "runtime": 169,
        },
        {
            "uri": f"urn:test:movie:{stamp}:3",
            "title": "Coco",
            "genres": ["Family", "Animation"],
            "rating": 8.4,
            "year": 2017,
            "runtime": 105,
        },
    ]

    for favorite in favorites:
        _http_json("POST", f"{base}/users/me/favorites", favorite, token=token)

    favorites_response = _http_json("GET", f"{base}/users/me/favorites", token=token)
    favorite_count = len((favorites_response.get("favorites") or []))

    print("[INFO] Calling /recommendation/activity twice (after profile change)")
    call3 = _http_json("GET", f"{base}/recommendation/activity", token=token)
    call4 = _http_json("GET", f"{base}/recommendation/activity", token=token)

    snap3 = (call3.get("contextExtracted") or {}).get("snapshotID")
    snap4 = (call4.get("contextExtracted") or {}).get("snapshotID")

    baseline_cache_hit = bool(snap1 and snap2 and snap1 == snap2)
    recalculated_after_change = bool(snap2 and snap3 and snap2 != snap3)
    post_change_cache_hit = bool(snap3 and snap4 and snap3 == snap4)
    enough_signals = favorite_count >= 3

    print("\n=== LAZY REFRESH SMOKE TEST ===")
    print(f"USER={email}")
    print(f"FAVORITES_COUNT={favorite_count}")
    print(f"SNAP1={snap1}")
    print(f"SNAP2={snap2}")
    print(f"SNAP3={snap3}")
    print(f"SNAP4={snap4}")
    print(f"BASELINE_CACHE_HIT={baseline_cache_hit}")
    print(f"RECALCULATED_AFTER_CHANGE={recalculated_after_change}")
    print(f"POST_CHANGE_CACHE_HIT={post_change_cache_hit}")

    passed = baseline_cache_hit and recalculated_after_change and post_change_cache_hit and enough_signals

    report = {
        "status": "PASS" if passed else "FAIL",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "baseUrl": base,
        "user": email,
        "favoritesCount": favorite_count,
        "snapshotIds": {
            "call1": snap1,
            "call2": snap2,
            "call3": snap3,
            "call4": snap4,
        },
        "checks": {
            "baselineCacheHit": baseline_cache_hit,
            "recalculatedAfterChange": recalculated_after_change,
            "postChangeCacheHit": post_change_cache_hit,
            "enoughSignals": enough_signals,
        },
    }

    if args.json_out:
        report_path = Path(args.json_out)
    else:
        report_path = Path(__file__).resolve().parent / "reports" / f"lazy_refresh_{stamp}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"JSON_REPORT={report_path}")

    if passed:
        print("PASS")
        return 0

    print("FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
