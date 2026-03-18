from __future__ import annotations

import math
from datetime import datetime

from app.application.use_cases.query_history import QueryHistoryUseCase
from app.application.use_cases.user_favorites import UserFavoritesUseCase
from app.domain.entities.query_history import QueryHistory


class RecommendationSignalService:
    def __init__(
        self,
        favorites_use_case: UserFavoritesUseCase,
        history_use_case: QueryHistoryUseCase,
        *,
        signal_decay_lambda: float,
        explicit_signal_base: float,
        implicit_signal_base: float,
        profile_cache_ttl_seconds: int = 180,
    ) -> None:
        self.favorites_use_case = favorites_use_case
        self.history_use_case = history_use_case
        self.signal_decay_lambda = signal_decay_lambda
        self.explicit_signal_base = explicit_signal_base
        self.implicit_signal_base = implicit_signal_base
        self.profile_cache_ttl_seconds = profile_cache_ttl_seconds

        self._profile_cache: dict[str, dict[str, float]] = {}
        self._profile_cache_updated_at: dict[str, datetime] = {}
        self._activity_snapshot_cache: dict[str, dict] = {}
        self._activity_snapshot_updated_at: dict[str, datetime] = {}

    def decayed_signal_weight(
        self,
        *,
        base_weight: float,
        interaction_at: datetime | None,
        now_ts: datetime,
    ) -> float:
        if not interaction_at:
            return base_weight
        try:
            days_since = max(
                0.0,
                (now_ts - interaction_at.replace(tzinfo=None)).total_seconds() / 86400,
            )
        except Exception:
            return base_weight
        return base_weight * math.exp(-self.signal_decay_lambda * days_since)

    def build_recent_title_set(
        self,
        history_entries: list[QueryHistory],
        limit: int = 25,
    ) -> set[str]:
        recent_titles: set[str] = set()
        for entry in history_entries:
            results = entry.resultsFound or []
            if not isinstance(results, list):
                continue
            for result in results:
                if not isinstance(result, dict):
                    continue
                title = result.get("title")
                if not title:
                    continue
                normalized = str(title).strip().lower()
                if normalized:
                    recent_titles.add(normalized)
                if len(recent_titles) >= max(1, limit):
                    return recent_titles
        return recent_titles

    def _build_user_genre_profile(self, user_id: str, history_limit: int = 20) -> dict[str, float]:
        now_ts = datetime.utcnow()
        profile: dict[str, float] = {}

        def add_signal(raw_genre: str | None, weight: float) -> None:
            if not raw_genre:
                return
            genre = str(raw_genre).strip().lower()
            if not genre:
                return
            profile[genre] = profile.get(genre, 0.0) + weight

        try:
            favorites = self.favorites_use_case.get_my_favorites(user_id)
        except Exception:
            favorites = []
        for movie in favorites:
            weight = self.decayed_signal_weight(
                base_weight=self.explicit_signal_base,
                interaction_at=movie.addedAt,
                now_ts=now_ts,
            )
            for genre in movie.genres or []:
                add_signal(genre, weight)

        try:
            history = self.history_use_case.find_by_user(user_id=user_id, limit=history_limit)
        except Exception:
            history = []
        for entry in history:
            entry_weight = self.decayed_signal_weight(
                base_weight=self.implicit_signal_base,
                interaction_at=entry.createdAt,
                now_ts=now_ts,
            )
            for result in entry.resultsFound or []:
                if not isinstance(result, dict):
                    continue
                add_signal(result.get("genreName"), entry_weight * 0.7)
                result_genres = result.get("genres")
                if isinstance(result_genres, list):
                    for genre in result_genres:
                        add_signal(genre, entry_weight * 0.7)

        return profile

    def get_user_genre_profile(self, user_id: str, history_limit: int = 20) -> dict[str, float]:
        now = datetime.utcnow()
        last_updated = self._profile_cache_updated_at.get(user_id)
        is_stale = (
            last_updated is None
            or (now - last_updated).total_seconds() > self.profile_cache_ttl_seconds
        )

        if user_id not in self._profile_cache or is_stale:
            self._profile_cache[user_id] = self._build_user_genre_profile(
                user_id=user_id, history_limit=history_limit
            )
            self._profile_cache_updated_at[user_id] = now
        return self._profile_cache[user_id]

    def invalidate_profile_cache(self, user_id: str) -> None:
        self._profile_cache.pop(user_id, None)
        self._profile_cache_updated_at.pop(user_id, None)

    def get_cached_activity_snapshot(self, user_id: str, max_age_seconds: int = 43200) -> dict | None:
        cached = self._activity_snapshot_cache.get(user_id)
        if not cached:
            return None

        updated_at = self._activity_snapshot_updated_at.get(user_id)
        if not updated_at:
            return None

        age_seconds = (datetime.utcnow() - updated_at).total_seconds()
        if age_seconds > max(1, max_age_seconds):
            return None

        return cached

    def cache_activity_snapshot(self, user_id: str, payload: dict) -> None:
        self._activity_snapshot_cache[user_id] = payload
        self._activity_snapshot_updated_at[user_id] = datetime.utcnow()

    def collect_activity_snapshot(self, user_id: str) -> dict:
        favorites = self.favorites_use_case.get_my_favorites(user_id)
        history = self.history_use_case.find_by_user(user_id=user_id, limit=20)

        ignored_queries = {
            "busqueda de peliculas",
            "búsqueda de películas",
            "recomiéndame una película basada en mi actividad reciente",
        }
        ignored_prefixes = (
            "recomiéndame una película basada en mi actividad reciente",
            "recomiendame una pelicula basada en mi actividad reciente",
        )
        recent_queries: list[str] = []

        for entry in history:
            raw_query = (entry.query or "").strip()
            normalized = raw_query.lower()
            if not raw_query:
                continue
            if normalized in ignored_queries:
                continue
            if any(normalized.startswith(prefix) for prefix in ignored_prefixes):
                continue
            if normalized.startswith("connection "):
                continue
            if raw_query not in recent_queries and len(recent_queries) < 3:
                recent_queries.append(raw_query)

        return {
            "favorites": favorites,
            "history": history,
            "recent_queries": recent_queries,
        }
