"""Event handlers for domain events"""
import logging
from app.domain.events.base import DomainEvent
from app.domain.events.recommendation_events import (
    RecommendationCreatedEvent,
    RecommendationCacheHitEvent,
    RecommendationCacheMissEvent,
)
from app.domain.events.history_events import HistoryEntryCreatedEvent

logger = logging.getLogger(__name__)


class RecommendationEventHandler:
    """Handles recommendation-related events"""
    
    async def on_recommendation_created(self, event: RecommendationCreatedEvent) -> None:
        """Called when a recommendation is created"""
        logger.info(
            f"Recommendation created",
            extra={
                "event_id": event.event_id,
                "user_id": event.user_id,
                "movies_found": event.movies_found,
                "execution_time_ms": event.execution_time_ms,
                "fallback_used": event.fallback_used,
            }
        )
        # Future: Publish to metrics collector, update user stats, etc.
    
    async def on_cache_hit(self, event: RecommendationCacheHitEvent) -> None:
        """Called when recommendation is served from cache"""
        logger.info(f"Recommendation cache hit for query: {event.query}")
        # Future: Update cache statistics
    
    async def on_cache_miss(self, event: RecommendationCacheMissEvent) -> None:
        """Called when recommendation cache miss occurs"""
        logger.info(f"Recommendation cache miss for query: {event.query}")
        # Future: Update cache statistics


class HistoryEventHandler:
    """Handles history-related events"""
    
    async def on_history_entry_created(self, event: HistoryEntryCreatedEvent) -> None:
        """Called when a history entry is created"""
        logger.info(
            f"History entry created",
            extra={
                "event_id": event.event_id,
                "user_id": event.user_id,
                "query": event.query,
                "was_successful": event.was_successful,
            }
        )
        # Future: Trigger analytics processing, update aggregations, etc.
