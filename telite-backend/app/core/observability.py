"""Observability and monitoring utilities for Telite LMS."""

from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager
from typing import Callable

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.request_context import (
    get_endpoint,
    get_http_method,
    get_org_id,
    get_request_id,
    get_user_id,
    set_endpoint,
    set_http_method,
    set_org_id,
    set_user_id,
)

logger = logging.getLogger("telite.observability")

# Configuration thresholds
SLOW_REQUEST_THRESHOLD_MS = int(os.getenv("SLOW_REQUEST_THRESHOLD_MS", "500"))
SLOW_QUERY_THRESHOLD_MS = int(os.getenv("SLOW_QUERY_THRESHOLD_MS", "300"))


def log_slow_request(
    endpoint: str,
    http_method: str,
    duration_ms: float,
    request_id: str,
    user_id: str | None = None,
    org_id: int | None = None,
) -> None:
    """Log slow requests for performance monitoring."""
    log_data = {
        "endpoint": endpoint,
        "http_method": http_method,
        "duration_ms": duration_ms,
        "request_id": request_id,
    }
    if user_id:
        log_data["user_id"] = user_id
    if org_id:
        log_data["org_id"] = org_id
    
    logger.warning(
        "Slow request detected",
        extra=log_data,
    )


def log_slow_query(
    duration_ms: float,
    statement: str,
    request_id: str | None = None,
) -> None:
    """Log slow database queries for performance monitoring."""
    # Extract statement type (SELECT, INSERT, UPDATE, DELETE)
    statement_type = statement.strip().split()[0] if statement.strip() else "UNKNOWN"
    
    # Try to extract table name (simple extraction)
    table = "UNKNOWN"
    if "FROM" in statement.upper():
        from_idx = statement.upper().find("FROM")
        after_from = statement[from_idx + 4:].strip()
        table = after_from.split()[0] if after_from else "UNKNOWN"
    
    log_data = {
        "duration_ms": duration_ms,
        "statement_type": statement_type,
        "table": table,
    }
    if request_id:
        log_data["request_id"] = request_id
    
    logger.warning(
        "Slow database query detected",
        extra=log_data,
    )


def setup_query_logging(engine: Engine) -> None:
    """Set up SQLAlchemy event listeners for slow query logging."""
    
    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        context._query_start_time = time.perf_counter()
    
    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        if hasattr(context, "_query_start_time"):
            duration_ms = (time.perf_counter() - context._query_start_time) * 1000
            if duration_ms > SLOW_QUERY_THRESHOLD_MS:
                request_id = get_request_id()
                log_slow_query(duration_ms, statement, request_id)


def get_safe_exception_info(exception: Exception) -> dict:
    """Extract safe exception information without exposing sensitive data."""
    return {
        "exception_type": type(exception).__name__,
        "exception_message": str(exception),
    }


def log_background_task_failure(
    task_name: str,
    exception: Exception,
    context: dict | None = None,
) -> None:
    """Log background task failures with full context."""
    log_data = {
        "task_name": task_name,
        "request_id": get_request_id(),
        "org_id": get_org_id(),
        "user_id": get_user_id(),
    }
    
    # Add exception info
    exc_info = get_safe_exception_info(exception)
    log_data.update(exc_info)
    
    # Add additional context if provided
    if context:
        # Sanitize context to remove sensitive data
        sanitized = {}
        sensitive_keys = {'password', 'token', 'secret', 'api_key', 'private_key'}
        for key, value in context.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        log_data.update(sanitized)
    
    logger.error(
        f"Background task failed: {task_name}",
        extra=log_data,
        exc_info=True,
    )


def log_startup_validation(
    app_version: str,
    environment: str,
    database_connected: bool,
    redis_connected: bool,
    storage_provider: str | None = None,
) -> None:
    """Log startup validation without exposing secrets."""
    logger.info(
        "Application startup validation",
        extra={
            "app_version": app_version,
            "environment": environment,
            "database_connected": database_connected,
            "redis_connected": redis_connected,
            "storage_provider": storage_provider or "unknown",
        },
    )


@contextmanager
def request_context(
    request_id: str,
    org_id: int | None = None,
    user_id: str | None = None,
    endpoint: str | None = None,
    http_method: str | None = None,
):
    """Context manager for request-scoped logging context."""
    from app.core.request_context import (
        set_endpoint,
        set_http_method,
        set_org_id,
        set_user_id,
    )
    
    tokens = []
    try:
        if org_id:
            tokens.append(set_org_id(org_id))
        if user_id:
            tokens.append(set_user_id(user_id))
        if endpoint:
            tokens.append(set_endpoint(endpoint))
        if http_method:
            tokens.append(set_http_method(http_method))
        yield
    finally:
        # Context will be reset by the middleware
        pass