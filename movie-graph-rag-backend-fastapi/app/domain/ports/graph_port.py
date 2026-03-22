from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.domain.entities.recommendation_models import UserContext, UserProfile


class GraphPort(Protocol):
    """Port for executing SPARQL queries against the knowledge graph."""

    def execute_select(self, sparql: str) -> list[dict]:
        """Execute a SPARQL SELECT query. Returns list of row dicts. Raises on connection failure."""
        ...

    def execute_update(self, sparql: str) -> bool:
        """Execute a SPARQL UPDATE query. Returns True on success, False on failure. Never raises."""
        ...

    def run_strategy(
        self,
        attempts: list[tuple[str, str]],
        min_results: int = 5,
    ) -> tuple[list[dict], str]:
        """Execute attempts in order until min_results rows are found. Returns (rows, strategy_name). Returns ([], 'empty') if all attempts fail."""
        ...


class ProfilePort(Protocol):
    """Port for reading and updating user preference profiles."""

    def get(self, user_id: str) -> "UserProfile":
        """Return the user profile. Returns UserProfile.cold_start(user_id) if no data exists."""
        ...

    def archive_context(self, user_id: str, context: "UserContext") -> None:
        """Persist a UserContext snapshot to the user history graph. Never raises."""
        ...

    def invalidate_cache(self, user_id: str) -> None:
        """Clear cached profile for this user."""
        ...
