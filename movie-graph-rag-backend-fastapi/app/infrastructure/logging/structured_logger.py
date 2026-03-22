"""Logging infrastructure - structured logging with trace IDs"""
import logging
import json
from typing import Any, Optional
from datetime import datetime
from uuid import uuid4
from contextvars import ContextVar

# Context variable for trace ID - shared across async tasks
trace_id_context: ContextVar[str] = ContextVar("trace_id", default="")


class StructuredLogger:
    """
    Structured logger that outputs JSON with trace IDs and contextual information.
    
    Features:
    - JSON formatted output for log aggregation
    - Automatic trace ID injection
    - Contextual logging with correlation IDs
    - Log level filtering
    
    Usage:
        logger = StructuredLogger("app.modules.recommendation")
        logger.info("Recommendation created", user_id="123", movies_found=5)
        
        # Output: {"timestamp": "...", "level": "INFO", "logger": "...", 
        #          "message": "Recommendation created", "trace_id": "...", 
        #          "user_id": "123", "movies_found": 5}
    """
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.name = name
    
    def _build_log_context(self, level: str, message: str, **context) -> dict:
        """Build structured log entry"""
        trace_id = trace_id_context.get() or str(uuid4())
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "logger": self.name,
            "message": message,
            "trace_id": trace_id,
            **context,
        }
    
    def info(self, message: str, **context):
        """Log info level"""
        log_entry = self._build_log_context("INFO", message, **context)
        self.logger.info(json.dumps(log_entry))
    
    def warning(self, message: str, **context):
        """Log warning level"""
        log_entry = self._build_log_context("WARNING", message, **context)
        self.logger.warning(json.dumps(log_entry))
    
    def error(self, message: str, error: Optional[Exception] = None, **context):
        """Log error level"""
        context_copy = context.copy()
        if error:
            context_copy["error"] = str(error)
            context_copy["error_type"] = type(error).__name__
        
        log_entry = self._build_log_context("ERROR", message, **context_copy)
        self.logger.error(json.dumps(log_entry))
    
    def debug(self, message: str, **context):
        """Log debug level"""
        log_entry = self._build_log_context("DEBUG", message, **context)
        self.logger.debug(json.dumps(log_entry))


def set_trace_id(trace_id: str) -> None:
    """Set the current trace ID in context"""
    trace_id_context.set(trace_id)


def get_trace_id() -> str:
    """Get the current trace ID"""
    return trace_id_context.get()


def generate_trace_id() -> str:
    """Generate a new trace ID"""
    return str(uuid4())
