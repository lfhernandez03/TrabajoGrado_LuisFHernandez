"""Base class for all domain events"""
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4
from typing import Any


@dataclass
class DomainEvent:
    """Base class for domain events - immutable events that represent business-significant occurrences"""
    
    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: str = field(default="")
    timestamp: datetime = field(default_factory=datetime.utcnow)
    aggregate_id: str = ""  # ID del agregado que generó el evento
    
    def __post_init__(self):
        if not self.event_type:
            self.event_type = self.__class__.__name__
