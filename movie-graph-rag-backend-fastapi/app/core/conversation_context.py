from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from app.domain.entities.recommendation_models import (
    ConversationSession,
    ConversationTurn,
    UserContext,
)

if TYPE_CHECKING:
    from app.domain.entities.query_context import QueryContext

# ---------------------------------------------------------------------------
# Time-of-day inference (server clock — never from the LLM)
# ---------------------------------------------------------------------------

def get_time_of_day(now: datetime | None = None) -> str:
    """Infer the current time-of-day bucket from the server clock."""
    hour = (now or datetime.utcnow()).hour
    if 6 <= hour < 12:
        return "morning"
    if 12 <= hour < 18:
        return "afternoon"
    if 18 <= hour < 23:
        return "evening"
    return "night"


# ---------------------------------------------------------------------------
# children_age_hint keyword extraction
# ---------------------------------------------------------------------------

_YOUNG_TOKENS = re.compile(
    r"pequeñ|beb[eé]|infante|niño chic|niña chic|preescolar|jardín", re.IGNORECASE
)
_TEEN_TOKENS = re.compile(
    r"adolescen|teenager|pre-adolescen|secundari", re.IGNORECASE
)
_ADULT_TOKENS = re.compile(
    r"universitari|mayor de edad|adulto|adult", re.IGNORECASE
)


def infer_children_age_hint(raw_query: str) -> str | None:
    """Detect children age group from the raw query text.

    Returns "young" (<12), "teen" (12-17), "adult" (18+), or None (unknown).
    Public so adapters and tests can call it directly.
    """
    if _YOUNG_TOKENS.search(raw_query):
        return "young"
    if _TEEN_TOKENS.search(raw_query):
        return "teen"
    if _ADULT_TOKENS.search(raw_query):
        return "adult"
    return None


# ---------------------------------------------------------------------------
# Bridge: QueryContext (legacy LLM model) → UserContext (domain model)
# ---------------------------------------------------------------------------

def query_context_to_user_context(
    qctx: "QueryContext",
    *,
    raw_query: str = "",
    session_id: str | None = None,
    now: datetime | None = None,
) -> UserContext:
    """Convert a legacy QueryContext (returned by GeminiAdapter) to UserContext.

    This bridge is temporary until Phase 3 updates the LLM adapter to return
    UserContext directly.  It maps the nested social_context dict to flat fields
    and injects server-clock time_of_day.

    ``raw_query`` must be the original user text so that ``infer_children_age_hint``
    can detect keywords like "niños pequeños" — qctx.intent is a category label
    ("family", "horror") and would never match those patterns.
    """
    social = qctx.social_context or {}
    companion = social.get("companionType")
    has_children = bool(social.get("hasChildren", False))
    children_age_hint = infer_children_age_hint(raw_query)

    return UserContext(
        mood=qctx.mood,
        companion=companion,
        has_children=has_children,
        energy=None,                # QueryContext has no separate energy field
        genres=list(qctx.genres or []),
        runtime_max=qctx.runtime_max,
        exclusions=list(qctx.exclusions or []),
        confidence=0.9,             # assume LLM succeeded; adapter falls back internally
        time_of_day=get_time_of_day(now),
        children_age_hint=children_age_hint,
        session_id=session_id,
        raw_query=raw_query,
    )


# ---------------------------------------------------------------------------
# Context merge rules
# ---------------------------------------------------------------------------

def merge_contexts(accumulated: UserContext | None, new: UserContext) -> UserContext:
    """Merge a new UserContext into the accumulated session context.

    Rules:
    - Non-None fields in ``new`` overwrite ``accumulated``.
    - None fields in ``new`` preserve the previous value.
    - ``exclusions`` accumulate (union, preserving order).
    - ``time_of_day`` always taken from ``new`` (server clock).
    - ``confidence`` grows with each turn (capped at 0.95).
    - ``session_id`` preserved from ``accumulated`` if present.
    """
    if accumulated is None:
        return new

    def pick(old, new_val):
        return new_val if new_val is not None else old

    merged_exclusions = list(dict.fromkeys(
        accumulated.exclusions + [e for e in new.exclusions if e not in accumulated.exclusions]
    ))

    new_confidence = min(0.95, max(accumulated.confidence, new.confidence) + 0.05)

    return UserContext(
        mood=pick(accumulated.mood, new.mood),
        companion=pick(accumulated.companion, new.companion),
        has_children=new.has_children or accumulated.has_children,
        energy=pick(accumulated.energy, new.energy),
        genres=new.genres if new.genres else accumulated.genres,
        runtime_max=pick(accumulated.runtime_max, new.runtime_max),
        exclusions=merged_exclusions,
        confidence=new_confidence,
        time_of_day=new.time_of_day,                # always current turn
        children_age_hint=pick(accumulated.children_age_hint, new.children_age_hint),
        session_id=accumulated.session_id or new.session_id,
        raw_query=new.raw_query,
    )


# ---------------------------------------------------------------------------
# In-memory session store
# ---------------------------------------------------------------------------

_SESSION_TTL = timedelta(hours=2)


class SessionStore:
    """In-process store for ConversationSession objects.

    Sessions expire after 2 hours of inactivity.  A restart clears all sessions
    (acceptable for a prototype; replace with Redis for production).
    """

    def __init__(self) -> None:
        self._store: dict[str, ConversationSession] = {}

    def get_or_create(self, session_id: str, user_id: str) -> ConversationSession:
        """Return an existing session or create a new one."""
        self._evict_expired()
        if session_id not in self._store:
            now = datetime.utcnow()
            self._store[session_id] = ConversationSession(
                session_id=session_id,
                user_id=user_id,
                created_at=now,
                last_updated=now,
            )
        return self._store[session_id]

    def update(self, session: ConversationSession) -> None:
        """Persist an updated session back to the store."""
        self._store[session.session_id] = session

    def _evict_expired(self) -> None:
        cutoff = datetime.utcnow() - _SESSION_TTL
        expired = [
            sid for sid, sess in self._store.items()
            if sess.last_updated < cutoff
        ]
        for sid in expired:
            del self._store[sid]


# Module-level singleton — shared across all requests in the same process.
session_store = SessionStore()
