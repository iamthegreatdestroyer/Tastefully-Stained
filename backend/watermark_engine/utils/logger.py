"""
Logging Configuration Module
============================

Structured logging setup for Tastefully Stained services.

This module provides:
- Structured JSON logging for production
- Human-readable console logging for development
- Log level configuration
- Request ID correlation
- Performance metric logging

Features:
---------
- JSON structured output for log aggregation
- Color-coded console output
- Configurable log levels per module
- Context injection (request_id, user_id)

Example:
--------
    >>> from watermark_engine.utils import setup_logging, get_logger
    >>> 
    >>> setup_logging(level="DEBUG", json_output=False)
    >>> 
    >>> logger = get_logger(__name__)
    >>> logger.info("Processing started", extra={"image_id": "123"})

Copyright (c) 2024-2026 Tastefully Stained
All rights reserved.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from typing import Any

# Try to import optional dependencies
try:
    import json
    JSON_AVAILABLE = True
except ImportError:
    JSON_AVAILABLE = False


class StructuredFormatter(logging.Formatter):
    """
    JSON structured log formatter for production.
    
    Outputs logs in JSON format for easy parsing by log aggregators
    like ELK Stack, Datadog, or Splunk.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add any additional fields from extra
        for key, value in record.__dict__.items():
            if key not in (
                "name", "msg", "args", "levelname", "levelno",
                "pathname", "filename", "module", "exc_info",
                "exc_text", "stack_info", "lineno", "funcName",
                "created", "msecs", "relativeCreated", "thread",
                "threadName", "processName", "process", "message",
                "request_id"
            ):
                log_data[key] = value
        
        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """
    Color-coded console formatter for development.
    
    Uses ANSI colors for improved readability during development.
    """
    
    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        color = self.COLORS.get(record.levelname, self.RESET)
        
        # Format timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Build formatted message
        formatted = (
            f"{color}[{timestamp}] "
            f"{record.levelname:8s}{self.RESET} "
            f"{record.name}: {record.getMessage()}"
        )
        
        # Add exception if present
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
        
        return formatted


def setup_logging(
    level: str = "INFO",
    json_output: bool = False,
    log_file: str | None = None,
    module_levels: dict[str, str] | None = None
) -> None:
    """
    Configure logging for the application.
    
    Args:
        level: Default log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_output: Use JSON structured output (for production)
        log_file: Optional file path for logging
        module_levels: Dict of module-specific log levels
    
    Example:
        >>> setup_logging(
        ...     level="DEBUG",
        ...     json_output=False,
        ...     module_levels={"watermark_engine.core": "DEBUG"}
        ... )
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Select formatter
    if json_output:
        formatter = StructuredFormatter()
    else:
        formatter = ColoredFormatter()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(StructuredFormatter())  # Always JSON for files
        root_logger.addHandler(file_handler)
    
    # Set module-specific levels
    if module_levels:
        for module, mod_level in module_levels.items():
            logging.getLogger(module).setLevel(getattr(logging, mod_level.upper()))
    
    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    logging.getLogger(__name__).info(
        f"Logging configured: level={level}, json={json_output}"
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured logger instance
    
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Hello, world!")
    """
    return logging.getLogger(name)


class LogContext:
    """
    Context manager for adding context to log records.
    
    Adds fields like request_id to all log messages within the context.
    
    Example:
        >>> with LogContext(request_id="abc123"):
        ...     logger.info("Processing")  # Will include request_id
    """
    
    def __init__(self, **context: Any) -> None:
        """Initialize with context fields."""
        self.context = context
        self._old_factory = None
    
    def __enter__(self) -> "LogContext":
        """Enter context and inject fields."""
        self._old_factory = logging.getLogRecordFactory()
        context = self.context
        
        def record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
            record = self._old_factory(*args, **kwargs)
            for key, value in context.items():
                setattr(record, key, value)
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, *args: Any) -> None:
        """Exit context and restore factory."""
        if self._old_factory:
            logging.setLogRecordFactory(self._old_factory)
