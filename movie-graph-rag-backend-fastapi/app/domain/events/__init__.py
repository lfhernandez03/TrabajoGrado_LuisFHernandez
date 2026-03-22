"""Domain events - core events that happen in the business logic"""
from .base import DomainEvent
from .recommendation_events import (
    RecommendationCreatedEvent,
    RecommendationCacheHitEvent,
    RecommendationCacheMissEvent,
)
from .history_events import HistoryEntryCreatedEvent
from .user_events import UserPreferencesUpdatedEvent

__all__ = [
    "DomainEvent",
    "RecommendationCreatedEvent",
    "RecommendationCacheHitEvent",
    "RecommendationCacheMissEvent",
    "HistoryEntryCreatedEvent",
    "UserPreferencesUpdatedEvent",
]
