"""Circuit Breaker implementation for resilience patterns"""
import logging
from enum import Enum
from datetime import datetime, timedelta
from typing import Callable, Any, TypeVar, Optional
from dataclasses import dataclass, field
import asyncio

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "CLOSED"          # Normal operation
    OPEN = "OPEN"              # Failure threshold exceeded, blocking calls
    HALF_OPEN = "HALF_OPEN"    # Recovery attempt in progress


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5          # Failures before opening circuit
    recovery_timeout_sec: int = 30      # Seconds before attempting recovery
    success_threshold: int = 2           # Successes in HALF_OPEN before closing
    max_retries: int = 3                # Max retry attempts per call


@dataclass
class CircuitBreakerMetrics:
    """Metrics tracked by circuit breaker"""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    total_calls: int = 0
    last_failure_time: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    
    def reset(self):
        """Reset all metrics"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.opened_at = None


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for fault tolerance.
    
    States:
    - CLOSED: Normal operation (forward all requests)
    - OPEN: Circuit is broken (fail immediately, don't call upstream)
    - HALF_OPEN: Testing if upstream is recovered (limited requests)
    
    Transitions:
    - CLOSED → OPEN: When failure threshold exceeded
    - OPEN → HALF_OPEN: After timeout expires
    - HALF_OPEN → CLOSED: When success threshold reached
    - HALF_OPEN → OPEN: When a failure occurs in HALF_OPEN
    
    Usage:
        breaker = CircuitBreaker(
            name="fuseki_breaker",
            failure_threshold=5,
            recovery_timeout_sec=30
        )
        
        result = await breaker.call(execute_query_function, query)
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.metrics = CircuitBreakerMetrics()
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call a function through the circuit breaker.
        
        Args:
            func: Async callable to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
        
        Returns:
            Result from func if successful
        
        Raises:
            CircuitBreakerOpenError: If circuit is OPEN
            CircuitBreakerError: If max retries exceeded
        """
        if self.metrics.state == CircuitState.OPEN:
            if self._should_attempt_recovery():
                self.metrics.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker '{self.name}' transitioning to HALF_OPEN")
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN"
                )
        
        # Attempt call with retries
        last_exception = None
        for attempt in range(1, self.config.max_retries + 1):
            try:
                result = await func(*args, **kwargs)
                await self._on_success()
                return result
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Circuit breaker '{self.name}' attempt {attempt}/{self.config.max_retries} failed: {e}"
                )
                
                if attempt < self.config.max_retries:
                    # Exponential backoff: 0.5s, 1s, 2s
                    wait_time = 0.5 * (2 ** (attempt - 1))
                    await asyncio.sleep(wait_time)
        
        # All retries exhausted
        await self._on_failure()
        raise CircuitBreakerError(
            f"Circuit breaker '{self.name}' failed after {self.config.max_retries} attempts",
            original_error=last_exception
        )
    
    async def _on_success(self):
        """Handle successful call"""
        if self.metrics.state == CircuitState.HALF_OPEN:
            self.metrics.success_count += 1
            if self.metrics.success_count >= self.config.success_threshold:
                self._close_circuit()
        elif self.metrics.state == CircuitState.CLOSED:
            self.metrics.failure_count = max(0, self.metrics.failure_count - 1)
        
        self.metrics.total_calls += 1
    
    async def _on_failure(self):
        """Handle failed call"""
        self.metrics.failure_count += 1
        self.metrics.total_calls += 1
        self.metrics.last_failure_time = datetime.utcnow()
        
        if self.metrics.state == CircuitState.CLOSED:
            if self.metrics.failure_count >= self.config.failure_threshold:
                self._open_circuit()
        elif self.metrics.state == CircuitState.HALF_OPEN:
            self._open_circuit()
    
    def _open_circuit(self):
        """Transition to OPEN state"""
        self.metrics.state = CircuitState.OPEN
        self.metrics.opened_at = datetime.utcnow()
        self.metrics.success_count = 0
        logger.error(f"Circuit breaker '{self.name}' opened after {self.metrics.failure_count} failures")
    
    def _close_circuit(self):
        """Transition to CLOSED state"""
        logger.info(f"Circuit breaker '{self.name}' closed after recovery")
        self.metrics.reset()
    
    def _should_attempt_recovery(self) -> bool:
        """Check if enough time has passed to attempt recovery"""
        if not self.metrics.opened_at:
            return False
        
        elapsed = datetime.utcnow() - self.metrics.opened_at
        timeout = timedelta(seconds=self.config.recovery_timeout_sec)
        return elapsed >= timeout
    
    def get_state(self) -> str:
        """Get current circuit state"""
        return self.metrics.state.value
    
    def get_metrics(self) -> dict:
        """Get circuit breaker metrics"""
        return {
            "name": self.name,
            "state": self.metrics.state.value,
            "failure_count": self.metrics.failure_count,
            "success_count": self.metrics.success_count,
            "total_calls": self.metrics.total_calls,
            "last_failure_time": self.metrics.last_failure_time.isoformat() if self.metrics.last_failure_time else None,
            "opened_at": self.metrics.opened_at.isoformat() if self.metrics.opened_at else None,
        }


class CircuitBreakerError(Exception):
    """Raised when circuit breaker fails after all retries"""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        self.message = message
        self.original_error = original_error
        super().__init__(message)


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is OPEN and rejects the call immediately"""
    pass


# Global circuit breaker instances
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
    """
    Get or create a circuit breaker instance by name.
    
    Args:
        name: Unique name for the breaker
        config: Optional CircuitBreakerConfig
    
    Returns:
        CircuitBreaker instance
    """
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name, config)
    return _circuit_breakers[name]


def reset_circuit_breaker(name: str) -> bool:
    """Reset a circuit breaker manually"""
    if name in _circuit_breakers:
        _circuit_breakers[name].metrics.reset()
        return True
    return False


def get_all_circuit_breakers_metrics() -> dict:
    """Get metrics for all circuit breakers"""
    return {name: breaker.get_metrics() for name, breaker in _circuit_breakers.items()}
