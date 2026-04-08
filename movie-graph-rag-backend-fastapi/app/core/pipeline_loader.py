"""Pipeline loader — moves ontology + metrics loading out of the Docker entrypoint.

Public API:
    trigger() -> tuple[bool, str]   start background load; returns (accepted, message)
    get_status() -> PipelineState   snapshot of current state
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
from copy import copy
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from urllib import error, request

from app.core.config import settings
from app.core.fuseki_client import _build_auth_headers, execute_select_query

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Ontology files (same order as the original shell script)
# ---------------------------------------------------------------------------
ONTOLOGY_FILES: list[str] = [
    "/ontologies/base/movie-ontology.ttl",
    "/ontologies/base/context-ontology.ttl",
    "/ontologies/bridge/bridge-ontology.ttl",
    "/ontologies/instances/movies_data.ttl",
    "/ontologies/instances/bridge_data.ttl",
]

_METRICS_SCRIPT = "/app/backend-scripts/compute_network_metrics.py"
_TRIPLE_COUNT_THRESHOLD = 1000

PipelineStatus = Literal["idle", "loading_ontologies", "running_metrics", "done", "error"]


# ---------------------------------------------------------------------------
# State dataclass
# ---------------------------------------------------------------------------

@dataclass
class PipelineState:
    status: PipelineStatus = "idle"
    step: str = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    ontologies_loaded: int = 0
    ontologies_total: int = field(default_factory=lambda: len(ONTOLOGY_FILES))
    skipped_load: bool = False


# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

_state = PipelineState()
_lock = threading.Lock()       # protects _state mutations (brief sections)
_run_lock = threading.Lock()   # held for the entire pipeline run


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_status() -> PipelineState:
    """Return a snapshot copy of the current pipeline state."""
    with _lock:
        return copy(_state)


def trigger() -> tuple[bool, str]:
    """Start the data-loading pipeline in a background thread.

    Returns (True, 'Pipeline started') if accepted.
    Returns (False, 'Pipeline already running') if a run is in progress.
    """
    if not _run_lock.acquire(blocking=False):
        return False, "Pipeline already running"

    # _run_lock is now held; the background thread releases it in finally.
    with _lock:
        _state.status = "loading_ontologies"
        _state.step = "Initializing"
        _state.started_at = datetime.utcnow()
        _state.finished_at = None
        _state.error = None
        _state.ontologies_loaded = 0
        _state.skipped_load = False

    t = threading.Thread(target=_run_pipeline, daemon=True, name="pipeline-loader")
    t.start()
    return True, "Pipeline started"


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------

def _run_pipeline() -> None:
    try:
        _step_load_ontologies()
        _step_run_metrics()
        with _lock:
            _state.status = "done"
            _state.step = "Completed"
            _state.finished_at = datetime.utcnow()
        logger.info("Pipeline completed successfully.")
    except Exception as exc:
        logger.exception("Pipeline failed: %s", exc)
        with _lock:
            _state.status = "error"
            _state.step = "Failed"
            _state.error = str(exc)
            _state.finished_at = datetime.utcnow()
    finally:
        _run_lock.release()


# ---------------------------------------------------------------------------
# Step 1: load TTL ontology files
# ---------------------------------------------------------------------------

def _step_load_ontologies() -> None:
    with _lock:
        _state.step = "Checking existing triple count"

    # Reuse the cached SELECT client; _NO_CACHE_PATTERNS excludes this query
    # (it has no INSERT/DELETE/history substrings) so it may be cached —
    # that's fine because we only call this once per pipeline run.
    rows = execute_select_query("SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }")
    count = int(rows[0].get("n", "0")) if rows else 0
    logger.info("Fuseki triple count: %d", count)

    if count > _TRIPLE_COUNT_THRESHOLD:
        logger.info("Data already loaded (%d triples), skipping TTL upload.", count)
        with _lock:
            _state.skipped_load = True
            _state.step = "Ontologies already present, skipped"
        return

    data_endpoint = (
        f"{settings.fuseki_url.rstrip('/')}"
        f"/{settings.fuseki_dataset.strip('/')}/data"
    )
    auth_headers = _build_auth_headers()

    for path in ONTOLOGY_FILES:
        filename = os.path.basename(path)
        with _lock:
            _state.step = f"Loading {filename}"

        if not os.path.isfile(path):
            logger.warning("Ontology file not found, skipping: %s", path)
            continue

        logger.info("  Loading %s ...", filename)
        with open(path, "rb") as fh:
            body = fh.read()

        headers = {"Content-Type": "text/turtle"}
        headers.update(auth_headers)

        req = request.Request(data_endpoint, data=body, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=120) as resp:
                status_code = getattr(resp, "status", 0)
                if status_code not in (200, 201, 204):
                    raise RuntimeError(
                        f"Unexpected HTTP {status_code} loading {filename}"
                    )
        except error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="ignore")[:500]
            raise RuntimeError(
                f"HTTP {exc.code} loading {filename}: {body_text}"
            ) from exc

        with _lock:
            _state.ontologies_loaded += 1
        logger.info("  ✅ %s loaded", filename)


# ---------------------------------------------------------------------------
# Step 2: compute network metrics
# ---------------------------------------------------------------------------

def _step_run_metrics() -> None:
    with _lock:
        _state.step = "Running compute_network_metrics.py"
        _state.status = "running_metrics"

    if not os.path.isfile(_METRICS_SCRIPT):
        logger.warning("Metrics script not found at %s, skipping.", _METRICS_SCRIPT)
        return

    logger.info("Running compute_network_metrics.py ...")
    result = subprocess.run(
        [sys.executable, _METRICS_SCRIPT],
        capture_output=True,
        text=True,
        timeout=600,   # 10-minute hard cap
    )
    if result.returncode != 0:
        # Non-critical: log warning but let the pipeline reach "done"
        logger.warning(
            "compute_network_metrics.py exited %d. Last stderr:\n%s",
            result.returncode,
            result.stderr[-2000:] if result.stderr else "(no stderr)",
        )
    else:
        logger.info("compute_network_metrics.py completed successfully.")
