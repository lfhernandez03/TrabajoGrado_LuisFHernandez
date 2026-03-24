from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timedelta
from uuid import uuid4

from app.domain.entities.recommendation_models import UserContext, UserProfile
from app.core.fuseki_client import (
    execute_update_query,
    get_user_context_history,
)
from app.core.ontology_query_builder import translate_mood, translate_companion, translate_energy

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_CACHE_TTL = timedelta(minutes=3)
_COLD_START_THRESHOLD = 3       # fewer than this many snapshots → cold start
_CONTEXT_NS = "http://www.semanticweb.org/movierecommendation/ontologies/2025/context-ontology#"
_CONTEXTDATA_NS = "http://www.semanticweb.org/movierecommendation/data/context/"


# ---------------------------------------------------------------------------
# SPARQL helpers
# ---------------------------------------------------------------------------

def _esc(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def _build_archive_sparql(snapshot_id: str, ctx: UserContext, user_id: str, now: datetime) -> str:
    """Build a SPARQL INSERT DATA that writes a UserContext snapshot directly into
    the user's permanent history named graph.

    The triple structure mirrors what ``get_user_context_history`` reads back
    (context:ContextSnapshot / context:feelsMood / context:withCompanion /
    context:hasRequirement) so profiles can be rebuilt from history.
    """
    sid = _esc(snapshot_id)
    iso_ts = now.replace(microsecond=0).isoformat()
    day_name = now.strftime("%A")
    graph_uri = f"http://users/{_esc(user_id)}/history"

    lines: list[str] = [
        f"PREFIX context: <{_CONTEXT_NS}>",
        f"PREFIX contextdata: <{_CONTEXTDATA_NS}>",
        "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>",
        "",
        f"INSERT DATA {{",
        f"  GRAPH <{graph_uri}> {{",
        f"    contextdata:Session_{sid} a context:ContextSnapshot ;",
        f'        context:snapshotID "{sid}"^^xsd:string ;',
        f'        context:requestTimestamp "{_esc(iso_ts)}"^^xsd:dateTime ;',
        f"        context:hourOfDay {now.hour}^^xsd:integer ;",
        f'        context:dayOfWeek "{_esc(day_name)}"^^xsd:string .',
    ]

    mood_es = translate_mood(ctx.mood)
    energy_es = translate_energy(ctx.energy) or translate_energy(ctx.mood) or "medio"
    if mood_es:
        lines += [
            f"    contextdata:Session_{sid} context:feelsMood contextdata:Mood_{sid} .",
            f"    contextdata:Mood_{sid} a context:EmotionalContext ;",
            f'        context:moodDescription "{_esc(mood_es)}"^^xsd:string ;',
            f'        context:desiredEnergyLevel "{_esc(energy_es)}"^^xsd:string .',
        ]

    companion_es = translate_companion(
        ctx.companion,
        ctx.has_children or ctx.children_age_hint == "young",
    )
    if companion_es:
        has_children_str = "true" if ctx.has_children else "false"
        lines += [
            f"    contextdata:Session_{sid} context:withCompanion contextdata:Social_{sid} .",
            f"    contextdata:Social_{sid} a context:SocialContext ;",
            f'        context:companionType "{_esc(companion_es)}"^^xsd:string ;',
            f"        context:hasChildren {has_children_str}^^xsd:boolean .",
        ]

    if ctx.runtime_max is not None:
        lines += [
            f"    contextdata:Session_{sid} context:hasRequirement contextdata:Req_{sid} .",
            f"    contextdata:Req_{sid} a context:RequirementContext ;",
            f"        context:availableTime {int(ctx.runtime_max)}^^xsd:integer .",
        ]

    lines += ["  }", "}"]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# ProfileService
# ---------------------------------------------------------------------------

class ProfileService:
    """Builds and caches UserProfile from Fuseki context history.

    Implements the ProfilePort protocol so it can be injected into the
    RecommendationUseCase (Phase 3).

    Cache TTL: 3 minutes per user.  The cache is in-process only; a restart
    clears it (acceptable for a prototype).
    """

    def __init__(self) -> None:
        # {user_id: (UserProfile, expires_at)}
        self._cache: dict[str, tuple[UserProfile, datetime]] = {}

    # ── ProfilePort interface ───────────────────────────────────────────────

    def get(self, user_id: str) -> UserProfile:
        """Return a UserProfile, building it from Fuseki history when the cache
        is cold or expired."""
        now = datetime.utcnow()
        if user_id in self._cache:
            profile, expires = self._cache[user_id]
            if now < expires:
                return profile

        profile = self._build_profile(user_id)
        self._cache[user_id] = (profile, now + _CACHE_TTL)
        return profile

    def archive_context(self, user_id: str, ctx: UserContext) -> None:
        """Write a UserContext snapshot to the user's permanent Fuseki history
        graph and invalidate the cached profile.

        Never raises — failures are logged and silently swallowed so a failed
        archive never crashes the recommendation pipeline.
        """
        try:
            snapshot_id = (
                ctx.session_id
                or f"ctx_{user_id}_{uuid4().hex[:8]}"
            )
            now = datetime.utcnow()
            sparql = _build_archive_sparql(snapshot_id, ctx, user_id, now)
            ok = execute_update_query(sparql)
            if not ok:
                logger.warning("archive_context: INSERT failed for user %s", user_id)
        except Exception as exc:
            logger.error("archive_context error for user %s: %s", user_id, exc)
        finally:
            self.invalidate_cache(user_id)

    def invalidate_cache(self, user_id: str) -> None:
        """Evict the user from the profile cache."""
        self._cache.pop(user_id, None)

    # ── Internal ────────────────────────────────────────────────────────────

    def _build_profile(self, user_id: str) -> UserProfile:
        """Reconstruct a UserProfile from the user's Fuseki context history.

        Returns UserProfile.cold_start() on any read failure or when no
        history exists.
        """
        try:
            rows = get_user_context_history(user_id, limit=50)
        except Exception as exc:
            logger.warning("_build_profile: could not read history for %s: %s", user_id, exc)
            rows = []

        if not rows:
            return UserProfile.cold_start(user_id)

        mood_counter: Counter[str] = Counter()
        companion_counter: Counter[str] = Counter()
        energy_counter: Counter[str] = Counter()
        time_of_day_counter: Counter[str] = Counter()
        children_age_hints: list[str] = []

        for row in rows:
            if mood := str(row.get("moodDescription") or "").strip():
                mood_counter[mood] += 1
            if companion := str(row.get("companionType") or "").strip():
                companion_counter[companion] += 1
            if energy := str(row.get("desiredEnergyLevel") or "").strip():
                energy_counter[energy] += 1
            # hourOfDay → time_of_day bucket
            hour_raw = row.get("hourOfDay")
            if hour_raw is not None:
                try:
                    hour = int(float(str(hour_raw)))
                    tod = _hour_to_time_of_day(hour)
                    if tod:
                        time_of_day_counter[tod] += 1
                except (ValueError, TypeError):
                    pass

        dominant_mood = mood_counter.most_common(1)[0][0] if mood_counter else None
        dominant_companion = companion_counter.most_common(1)[0][0] if companion_counter else None
        dominant_time_of_day = time_of_day_counter.most_common(1)[0][0] if time_of_day_counter else None

        snapshot_count = len(rows)
        is_cold_start = snapshot_count < _COLD_START_THRESHOLD

        return UserProfile(
            user_id=user_id,
            genre_weights={},       # populated by Scorer when favorites are available
            dominant_mood=dominant_mood,
            dominant_companion=dominant_companion,
            dominant_time_of_day=dominant_time_of_day,
            children_age_hint=children_age_hints[-1] if children_age_hints else None,
            snapshot_count=snapshot_count,
            is_cold_start=is_cold_start,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hour_to_time_of_day(hour: int) -> str | None:
    if 6 <= hour < 12:
        return "morning"
    if 12 <= hour < 18:
        return "afternoon"
    if 18 <= hour < 23:
        return "evening"
    if hour >= 23 or hour < 6:
        return "night"
    return None
