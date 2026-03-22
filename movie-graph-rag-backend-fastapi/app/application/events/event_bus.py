"""Event Bus - In-memory pub/sub for domain events"""
import asyncio
from abc import ABC, abstractmethod
from typing import Callable, List, Dict, Type
import logging

from app.domain.events.base import DomainEvent

logger = logging.getLogger(__name__)


class EventHandler(ABC):
    """Base class for event handlers"""
    
    @abstractmethod
    async def handle(self, event: DomainEvent) -> None:
        pass


class EventBus:
    """
    In-memory event bus for publishing and subscribing to domain events.
    
    Key principles:
    - Simple pub/sub: handlers register for specific event types
    - Async-ready: all handlers are awaited
    - Fire-and-forget: events are published immediately
    - Type-safe: handlers registered per event type
    
    Example:
        event_bus = EventBus()
        
        # Subscribe
        handler = RecommendationEventHandler()
        event_bus.subscribe(RecommendationCreatedEvent, handler.handle)
        
        # Publish (anywhere in business logic)
        event = RecommendationCreatedEvent(user_id="123", movies_found=5)
        await event_bus.publish(event)
    """
    
    def __init__(self):
        self._handlers: Dict[Type[DomainEvent], List[Callable]] = {}
    
    def subscribe(self, event_type: Type[DomainEvent], handler: Callable) -> None:
        """
        Subscribe a handler to an event type.
        
        Args:
            event_type: The event class to subscribe to
            handler: Async callable(event) that handles the event
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        
        self._handlers[event_type].append(handler)
        logger.debug(f"Handler {handler.__name__} subscribed to {event_type.__name__}")
    
    async def publish(self, event: DomainEvent) -> None:
        """
        Publish an event to all subscribed handlers.
        
        Args:
            event: The event instance to publish
        """
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])
        
        if not handlers:
            logger.debug(f"No handlers for event {event_type.__name__}")
            return
        
        logger.info(f"Publishing {event_type.__name__} to {len(handlers)} handler(s)")
        
        # Execute all handlers in parallel
        try:
            await asyncio.gather(
                *[handler(event) for handler in handlers],
                return_exceptions=True
            )
        except Exception as e:
            logger.error(f"Error publishing event {event_type.__name__}: {e}", exc_info=True)
    
    def get_handlers_count(self, event_type: Type[DomainEvent]) -> int:
        """Get count of handlers for an event type (useful for testing)"""
        return len(self._handlers.get(event_type, []))
    
    def clear(self) -> None:
        """Clear all handlers (useful for testing)"""
        self._handlers.clear()


# Global singleton instance
_event_bus: EventBus = None


def get_event_bus() -> EventBus:
    """Get or create the global event bus instance"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus
