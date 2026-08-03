"""Central logging configuration for Telite LMS."""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime


class JsonLogFormatter(logging.Formatter):
    """Structured JSON formatter with production observability fields."""
    
    # Fields to never log (sensitive data)
    SENSITIVE_FIELDS = {
        'password', 'token', 'jwt', 'cookie', 'authorization', 
        'secret', 'api_key', 'private_key', 'upload', 'answer'
    }
    
    def _sanitize_extra(self, extra: dict) -> dict:
        """Remove sensitive data from extra fields."""
        sanitized = {}
        for key, value in extra.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in self.SENSITIVE_FIELDS):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, str) and any(sensitive in value.lower() for sensitive in self.SENSITIVE_FIELDS):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        return sanitized
    
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add request context if available
        request_id = getattr(record, "request_id", None)
        if request_id:
            payload["request_id"] = request_id
        
        org_id = getattr(record, "org_id", None)
        if org_id:
            payload["org_id"] = org_id
        
        user_id = getattr(record, "user_id", None)
        if user_id:
            payload["user_id"] = user_id
        
        # Add HTTP context for ERROR logs
        if record.levelname == "ERROR":
            endpoint = getattr(record, "endpoint", None)
            if endpoint:
                payload["endpoint"] = endpoint
            
            http_method = getattr(record, "http_method", None)
            if http_method:
                payload["http_method"] = http_method
            
            exception_type = getattr(record, "exception_type", None)
            if exception_type:
                payload["exception_type"] = exception_type
            
            exception_message = getattr(record, "exception_message", None)
            if exception_message:
                payload["exception_message"] = exception_message
        
        # Add exception info if present
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        
        # Add sanitized extra fields
        if hasattr(record, 'extra') and record.extra:
            payload.update(self._sanitize_extra(record.extra))
        
        return json.dumps(payload, ensure_ascii=True)


def configure_logging() -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    log_format = os.getenv("LOG_FORMAT", "text").lower().strip()

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)

    # Stream Handler
    stream_handler = logging.StreamHandler()
    if log_format == "json":
        stream_handler.setFormatter(JsonLogFormatter())
    else:
        stream_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
    root.addHandler(stream_handler)

    # File Handler for debugging
    try:
        log_dir = os.path.dirname(os.path.abspath(__file__))
        debug_log_path = os.path.join(os.path.dirname(os.path.dirname(log_dir)), "debug_server.log")
        file_handler = logging.FileHandler(debug_log_path, mode="a", encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        root.addHandler(file_handler)
    except Exception:
        pass

