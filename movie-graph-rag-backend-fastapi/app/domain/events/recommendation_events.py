"""Recommendation domain events"""
from dataclasses import dataclass
from typing import Optional, Any
from .base import DomainEvent


@dataclass
class RecommendationCreatedEvent(DomainEvent):
    """Fired when a recommendation is successfully created"""
    user_id: str = ""
    query: str = ""
    movies_found: int = 0
    execution_time_ms: int = 0
    fallback_used: bool = False
    
    def __post_init__(self):
        super().__post_init__()
        self.aggregate_id = self.user_id


@dataclass
class RecommendationCacheHitEvent(DomainEvent):
    """Fired when a recommendation was served from cache"""
    user_id: str = ""
    query: str = ""
    cache_key: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        self.aggregate_id = self.user_id


@dataclass
class RecommendationCacheMissEvent(DomainEvent):
    """Fired when a recommendation cache miss occurred"""
    user_id: str = ""
    query: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        self.aggregate_id = self.user_id
