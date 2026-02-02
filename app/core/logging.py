"""Structured JSON logging configuration for the application.

Provides JSON logging with trace_id support for distributed tracing.
Logs can be written to stdout and/or file.
"""
import json
import logging
import sys
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from contextvars import ContextVar

# Context variable to store trace_id for the current request
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="unknown")


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,

            "message": record.getMessage(),
            "logger": record.name,
            "trace_id": trace_id_var.get(),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data) + "\n=============================================="


def setup_logging(level: str = "DEBUG", log_file: Optional[str] = "logs/app.log") -> None:
    """Configure application logging with JSON formatter.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file. If None, only stdout logging.
                 Defaults to 'logs/app.log'.
    """
    # Create logs directory if needed
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

    # Create logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler with JSON formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(console_handler)

    # Create file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(file_handler)

    # Reduce noisy loggers
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def set_trace_id(trace_id: str) -> None:
    """Set trace_id for current request context.

    Args:
        trace_id: Unique trace ID for the request
    """
    trace_id_var.set(trace_id)


def get_trace_id() -> str:
    """Get trace_id from current request context.

    Returns:
        Current trace ID or 'unknown' if not set
    """
    return trace_id_var.get()
