"""User domain events"""
from dataclasses import dataclass
from typing import Optional
from .base import DomainEvent


@dataclass
class UserPreferencesUpdatedEvent(DomainEvent):
    """Fired when user preferences are updated based on recommendations"""
    user_id: str = ""
    preference_type: str = ""  # "genre", "director", "rating", etc.
    change: float = 0.0  # delta change
    
    def __post_init__(self):
        super().__post_init__()
        self.aggregate_id = self.user_id
