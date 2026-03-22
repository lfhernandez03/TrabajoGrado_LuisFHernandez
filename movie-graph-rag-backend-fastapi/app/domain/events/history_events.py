"""History domain events"""
from dataclasses import dataclass
from typing import Optional
from .base import DomainEvent


@dataclass
class HistoryEntryCreatedEvent(DomainEvent):
    """Fired when a new history entry is created"""
    user_id: str = ""
    query: str = ""
    was_successful: bool = False
    
    def __post_init__(self):
        super().__post_init__()
        self.aggregate_id = self.user_id
