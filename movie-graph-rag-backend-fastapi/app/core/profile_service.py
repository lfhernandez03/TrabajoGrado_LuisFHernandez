from __future__ import annotations

import logging
import math
from collections import Counter
from datetime import datetime, timedelta
from uuid import uuid4

from app.domain.entities.recommendation_models import UserContext, UserProfile
from app.core.fuseki_client import (
    execute_select_query,
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
    """Escape string for use in SPARQL string literals."""
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def _esc_uri(value: str) -> str:
    """Escape string for use in SPARQL local names / URIs."""
    # Remove/replace problematic characters for local names
    s = str(value).replace("\\", "").replace('"', "").replace("/", "_").replace(":", "_").replace("#", "_").replace(" ", "_")
    return s


def _build_archive_sparql(snapshot_id: str, ctx: UserContext, user_id: str, now: datetime) -> str:
    """Build a SPARQL INSERT DATA that writes a UserContext snapshot directly into
    the user's permanent history named graph.

    The triple structure mirrors what ``get_user_context_history`` reads back
    (context:ContextSnapshot / context:feelsMood / context:withCompanion /
    context:hasRequirement) so profiles can be rebuilt from history.
    """
    sid_safe = _esc_uri(snapshot_id)  # For use in URIs
    sid_str = _esc(snapshot_id)       # For use in string literals
    user_id_safe = _esc_uri(user_id)
    iso_ts = now.replace(microsecond=0).isoformat() + "Z"
    iso_ts_safe = _esc(iso_ts)
    day_name = now.strftime("%A")
    day_name_safe = _esc(day_name)
    hour_int = int(now.hour)
    graph_uri = f"http://users/{user_id_safe}/history"
    
    logger.debug(
        "_build_archive_sparql: snapshot_id=%s, user_id=%s, iso_ts=%s, has_mood=%s, has_companion=%s, has_runtime=%s",
        snapshot_id,
        user_id,
        iso_ts,
        bool(ctx.mood),
        bool(ctx.companion),
        ctx.runtime_max,
    )

    lines: list[str] = [
        f"PREFIX context: <{_CONTEXT_NS}>",
        f"PREFIX contextdata: <{_CONTEXTDATA_NS}>",
        "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>",
        "",
        "INSERT DATA {",
        f"  GRAPH <{graph_uri}> {{",
        f"    contextdata:Session_{sid_safe} a context:ContextSnapshot ;",
        f"        context:snapshotID \"{sid_str}\"^^xsd:string ;",
        f"        context:requestTimestamp \"{iso_ts_safe}\"^^xsd:dateTime ;",
        f'        context:hourOfDay "{hour_int}"^^xsd:integer ;',
        f"        context:dayOfWeek \"{day_name_safe}\"^^xsd:string .",
    ]

    mood_es = translate_mood(ctx.mood)
    energy_es = translate_energy(ctx.energy) or translate_energy(ctx.mood) or "medium"
    if mood_es:
        mood_es_safe = _esc(mood_es)
        energy_es_safe = _esc(energy_es)
        lines += [
            f"    contextdata:Session_{sid_safe} context:feelsMood contextdata:Mood_{sid_safe} .",
            f"    contextdata:Mood_{sid_safe} a context:EmotionalContext ;",
            f"        context:moodDescription \"{mood_es_safe}\"^^xsd:string ;",
            f"        context:desiredEnergyLevel \"{energy_es_safe}\"^^xsd:string .",
        ]

    companion_es = translate_companion(
        ctx.companion,
        ctx.has_children or ctx.children_age_hint == "young",
    )
    if companion_es:
        companion_es_safe = _esc(companion_es)
        has_children_str = "true" if ctx.has_children else "false"
        lines += [
            f"    contextdata:Session_{sid_safe} context:withCompanion contextdata:Social_{sid_safe} .",
            f"    contextdata:Social_{sid_safe} a context:SocialContext ;",
            f"        context:companionType \"{companion_es_safe}\"^^xsd:string ;",
            f'        context:hasChildren "{has_children_str}"^^xsd:boolean .',
        ]

    if ctx.runtime_max is not None:
        runtime_int = int(ctx.runtime_max)
        lines += [
            f"    contextdata:Session_{sid_safe} context:hasRequirement contextdata:Req_{sid_safe} .",
            f"    contextdata:Req_{sid_safe} a context:RequirementContext ;",
            f'        context:availableTime "{runtime_int}"^^xsd:integer .',
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
        # {user_id: last_archived_context} — for change detection
        self._last_contexts: dict[str, "UserContext"] = {}

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
        graph, but ONLY if the context has changed significantly since the last
        archival.

        Change detection compares:
        - mood, energy, companion, has_children, children_age_hint
        - runtime_max (if present)

        Never raises — failures are logged and silently swallowed so a failed
        archive never crashes the recommendation pipeline.
        """
        import threading
        
        def _has_significant_change(old_ctx: "UserContext | None", new_ctx: UserContext) -> bool:
            """Return True if any key fields have changed meaningfully."""
            if old_ctx is None:
                return True
            
            # Compare key fields
            if old_ctx.mood != new_ctx.mood:
                return True
            if old_ctx.energy != new_ctx.energy:
                return True
            if old_ctx.companion != new_ctx.companion:
                return True
            if old_ctx.has_children != new_ctx.has_children:
                return True
            if old_ctx.children_age_hint != new_ctx.children_age_hint:
                return True
            if old_ctx.runtime_max != new_ctx.runtime_max:
                return True
            
            return False
        
        def _do_archive():
            try:
                # Check if context has changed significantly
                old_ctx = self._last_contexts.get(user_id)
                if not _has_significant_change(old_ctx, ctx):
                    logger.debug("archive_context: No significant change for user %s, skipping", user_id)
                    return
                
                # Record this as the last archived context
                self._last_contexts[user_id] = ctx
                
                snapshot_id = (
                    ctx.session_id
                    or f"ctx_{user_id}_{uuid4().hex[:8]}"
                )
                now = datetime.utcnow()
                sparql = _build_archive_sparql(snapshot_id, ctx, user_id, now)
                logger.info("archive_context SPARQL (user=%s):\n%s", user_id, sparql)
                ok = execute_update_query(sparql)
                if not ok:
                    logger.warning("archive_context: INSERT failed for user %s", user_id)
            except Exception as exc:
                logger.error("archive_context error for user %s: %s", user_id, exc)
            finally:
                self.invalidate_cache(user_id)
        
        # Run in background thread to avoid blocking
        thread = threading.Thread(target=_do_archive, daemon=True)
        thread.start()

    def invalidate_cache(self, user_id: str) -> None:
        """Evict the user from the profile cache."""
        self._cache.pop(user_id, None)

    def get_topological_profile(
        self,
        user_id: str,
        favorites: list,           # list[FavoriteMovie] — avoid importing entity here
    ) -> "TopologicalProfileResponse":
        """Build a topological user profile from the user's favorite movies.

        Maps each favorite to its Louvain community (Phase 6 data), computes
        a cluster weight distribution, and derives exploration metrics from it.

        Returns a ``TopologicalProfileResponse`` (Pydantic schema).  The import
        is local to avoid a hard dependency on the API layer at module load time.
        """
        from app.api.schemas.topology_profile import (
            ClusterWeight,
            TopologicalProfileResponse,
            UnexploredCluster,
        )

        _MOVIE_NS = "http://www.semanticweb.org/movierecommendation/ontologies/2025/movie-ontology#"

        total = len(favorites)

        # ── Step 1: map favorite URIs → cluster IDs via SPARQL ─────────────
        uris = [f.uri for f in favorites if getattr(f, "uri", "")]
        cluster_of: dict[str, str] = {}   # {uri: clusterId}
        cluster_labels: dict[str, str] = {}

        if uris:
            values_clause = " ".join(f"<{u}>" for u in uris)
            try:
                rows = execute_select_query(
                    f"PREFIX movie: <{_MOVIE_NS}>\n"
                    "SELECT ?movie ?clusterId ?label WHERE {\n"
                    f"  VALUES ?movie {{ {values_clause} }}\n"
                    "  ?movie movie:belongsToCluster ?clusterId .\n"
                    "  OPTIONAL { ?movie movie:clusterLabel ?label }\n"
                    "}"
                )
                for row in rows:
                    uri = row.get("movie", "")
                    cid = str(row.get("clusterId", "")).strip()
                    if uri and cid:
                        cluster_of[uri] = cid
                        label = str(row.get("label", "")).strip()
                        if label and cid not in cluster_labels:
                            cluster_labels[cid] = label
            except Exception as exc:
                logger.warning("get_topological_profile: cluster lookup failed: %s", exc)

        # Fill missing labels
        for cid in set(cluster_of.values()):
            cluster_labels.setdefault(cid, f"Cluster {cid}")

        # ── Step 2: cluster counts and weights ──────────────────────────────
        cluster_counts: Counter[str] = Counter()
        for fav in favorites:
            uri = getattr(fav, "uri", "")
            cid = cluster_of.get(uri)
            if cid:
                cluster_counts[cid] += 1

        clustered = sum(cluster_counts.values())
        weights: dict[str, float] = {}
        if clustered > 0:
            weights = {cid: cnt / clustered for cid, cnt in cluster_counts.items()}

        # ── Step 3: exploration index (Shannon entropy, normalized) ─────────
        exploration_index = _entropy_index(list(weights.values()))

        if exploration_index < 0.3:
            user_type = "specialist"
        elif exploration_index > 0.7:
            user_type = "explorer"
        else:
            user_type = "balanced"

        # ── Step 4: temporal trend (compare older half vs. recent half) ─────
        temporal_trend, trend_explanation = _compute_temporal_trend(
            favorites, cluster_of, clustered
        )

        # ── Step 5: dominant clusters (top 5, descending by weight) ─────────
        dominant = [
            ClusterWeight(
                clusterId=cid,
                label=cluster_labels.get(cid, f"Cluster {cid}"),
                weight=round(weights[cid], 4),
                moviesSeen=cluster_counts[cid],
            )
            for cid, _ in cluster_counts.most_common(5)
        ]

        # ── Step 6: unexplored adjacent clusters ────────────────────────────
        unexplored = _find_unexplored(
            dominant_cluster_id=dominant[0].clusterId if dominant else None,
            visited_ids=set(cluster_counts.keys()),
            cluster_labels=cluster_labels,
            movie_ns=_MOVIE_NS,
        )

        return TopologicalProfileResponse(
            userId=user_id,
            explorationIndex=exploration_index,
            userType=user_type,
            dominantClusters=dominant,
            unexploredAdjacent=unexplored,
            temporalTrend=temporal_trend,
            trendExplanation=trend_explanation,
            totalFavorites=total,
            clusteredFavorites=clustered,
        )

    # ── Public helpers ──────────────────────────────────────────────────────

    @staticmethod
    def build_genre_weights(favorites: list) -> dict[str, float]:
        """Compute normalized genre weights from a list of FavoriteMovie objects.

        Each favorite may carry multiple genres (FavoriteMovie.genres: list[str]).
        Counts occurrences of every genre across all favorites and normalises to
        [0, 1] so the heaviest genre = 1.0.  Returns {} when favorites is empty
        or none of them have genre data.
        """
        from collections import Counter

        counts: Counter[str] = Counter()
        for fav in favorites:
            for g in getattr(fav, "genres", []) or []:
                g = str(g).strip()
                if g:
                    counts[g] += 1

        if not counts:
            return {}

        max_count = max(counts.values())
        return {g: round(cnt / max_count, 4) for g, cnt in counts.items()}

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


# ---------------------------------------------------------------------------
# Phase 11 helpers
# ---------------------------------------------------------------------------

def _entropy_index(weights: list[float]) -> float:
    """Shannon entropy of a weight distribution, normalized to [0, 1].

    0 = all weight on one cluster (specialist).
    1 = uniform distribution (explorer).
    """
    values = [w for w in weights if w > 0]
    if not values:
        return 0.5
    entropy = -sum(p * math.log2(p) for p in values)
    max_entropy = math.log2(len(values)) if len(values) > 1 else 1.0
    return round(entropy / max_entropy, 4)


def _compute_temporal_trend(
    favorites: list,
    cluster_of: dict[str, str],
    clustered: int,
) -> tuple[str, str]:
    """Compare cluster diversity of older vs. recent favorites.

    Requires favorites with ``addedAt`` timestamps and at least 4 clustered
    favorites.  Falls back to "stable" when insufficient data is available.
    """
    dated = sorted(
        [f for f in favorites if getattr(f, "addedAt", None) and f.uri in cluster_of],
        key=lambda f: f.addedAt,
    )
    n = len(dated)
    if n < 4:
        return "stable", f"Insufficient dated favorites to compute trend ({n} available)."

    mid = n // 2
    older = dated[:mid]
    recent = dated[mid:]

    def _weights(subset: list) -> list[float]:
        counts: Counter[str] = Counter(cluster_of[f.uri] for f in subset)
        total = sum(counts.values())
        return [c / total for c in counts.values()] if total else []

    older_idx = _entropy_index(_weights(older))
    recent_idx = _entropy_index(_weights(recent))

    delta = recent_idx - older_idx
    if delta < -0.10:
        return (
            "specializing",
            f"Your {mid} most recent favorites are concentrated in fewer communities "
            f"(index {recent_idx:.2f}) than the earlier ones (index {older_idx:.2f}).",
        )
    if delta > 0.10:
        return (
            "diversifying",
            f"Your {mid} most recent favorites are spread across more communities "
            f"(index {recent_idx:.2f}) than the earlier ones (index {older_idx:.2f}).",
        )
    return (
        "stable",
        f"Your exploration pattern is stable (recent {recent_idx:.2f} vs. earlier {older_idx:.2f}).",
    )


def _find_unexplored(
    dominant_cluster_id: str | None,
    visited_ids: set[str],
    cluster_labels: dict[str, str],
    movie_ns: str,
    limit: int = 5,
) -> list:
    """Return clusters adjacent to the dominant cluster that the user has not visited."""
    from app.api.schemas.topology_profile import UnexploredCluster

    if not dominant_cluster_id:
        return []

    try:
        # Get top genres of the dominant cluster
        genre_rows = execute_select_query(
            f"PREFIX movie: <{movie_ns}>\n"
            "SELECT ?genreName (COUNT(?m) AS ?cnt) WHERE {\n"
            f'  ?m movie:belongsToCluster "{dominant_cluster_id}" ;\n'
            "     movie:hasMainGenre/movie:genreName ?genreName .\n"
            "} GROUP BY ?genreName ORDER BY DESC(?cnt) LIMIT 5"
        )
        top_genres = [r["genreName"] for r in genre_rows if r.get("genreName")]
        if not top_genres:
            return []

        genre_values = " ".join(f'"{g}"' for g in top_genres)
        adj_rows = execute_select_query(
            f"PREFIX movie: <{movie_ns}>\n"
            "SELECT ?otherClusterId ?otherLabel (COUNT(DISTINCT ?m) AS ?cnt) WHERE {\n"
            f"  VALUES ?g {{ {genre_values} }}\n"
            "  ?m movie:hasMainGenre/movie:genreName ?g ;\n"
            "     movie:belongsToCluster ?otherClusterId .\n"
            "  OPTIONAL { ?m movie:clusterLabel ?otherLabel }\n"
            f'  FILTER(?otherClusterId != "{dominant_cluster_id}")\n'
            "} GROUP BY ?otherClusterId ?otherLabel ORDER BY DESC(?cnt)"
        )

        seen: set[str] = set()
        result: list[UnexploredCluster] = []
        for row in adj_rows:
            cid = str(row.get("otherClusterId", "")).strip()
            if not cid or cid in seen or cid in visited_ids:
                continue
            seen.add(cid)
            label = str(row.get("otherLabel", "")).strip() or cluster_labels.get(cid, f"Cluster {cid}")
            result.append(UnexploredCluster(clusterId=cid, label=label, distanceToDominant=1))
            if len(result) >= limit:
                break
        return result
    except Exception as exc:
        logger.warning("_find_unexplored: %s", exc)
        return []
