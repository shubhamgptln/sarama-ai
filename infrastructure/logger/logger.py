"""
infrastructure/logger.py

Structured logging for Python services.
Mirrors Go logger: infrastructure/logger/logger.go
"""

import logging
import json
from typing import Any, Dict
from datetime import datetime


class StructuredLogger:
    """Structured logger with JSON output and contextual fields"""

    def __init__(self, name: str, level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # Create console handler with JSON formatter
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        self.logger.addHandler(handler)

    def info(self, message: str, **fields: Any):
        """Log info level message with fields"""
        self._log_with_fields(logging.INFO, message, fields)

    def debug(self, message: str, **fields: Any):
        """Log debug level message with fields"""
        self._log_with_fields(logging.DEBUG, message, fields)

    def warn(self, message: str, **fields: Any):
        """Log warning level message with fields"""
        self._log_with_fields(logging.WARNING, message, fields)

    def error(self, message: str, **fields: Any):
        """Log error level message with fields"""
        self._log_with_fields(logging.ERROR, message, fields)

    def _log_with_fields(self, level: int, message: str, fields: Dict[str, Any]):
        """Internal method to log with fields"""
        log_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": logging.getLevelName(level),
            "message": message,
            **fields,
        }
        self.logger.log(level, json.dumps(log_record))


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs JSON"""

    def format(self, record: logging.LogRecord) -> str:
        return record.getMessage()


# Global logger instance
_global_logger = StructuredLogger("sarama-ai")


def get_logger(name: str) -> StructuredLogger:
    """Get a logger instance"""
    return StructuredLogger(name)


def set_log_level(level: int):
    """Set global log level"""
    _global_logger.logger.setLevel(level)
