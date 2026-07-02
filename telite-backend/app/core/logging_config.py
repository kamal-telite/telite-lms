"""Central logging configuration for Telite LMS."""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        request_id = getattr(record, "request_id", None)
        if request_id:
            payload["request_id"] = request_id
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

