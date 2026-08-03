"""Production operational endpoints router."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.orm import Session

from app.core.health import (
    APP_NAME,
    APP_VERSION,
    check_celery_health,
    check_database_health,
    check_redis_health,
    check_storage_health,
    get_build_date,
    get_build_number,
    get_environment,
    get_git_commit,
    get_http_metrics,
    get_uptime_seconds,
)
from app.db.engine import db_session

logger = logging.getLogger("telite.ops")

ops_router = APIRouter(prefix="/ops", tags=["Operations"])


@ops_router.get("/health")
def health_check() -> dict[str, Any]:
    """
    Simple liveness endpoint.
    
    Returns basic application status without database queries.
    Used by Kubernetes liveness probes to check if the application is running.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "uptime_seconds": get_uptime_seconds(),
        "version": APP_VERSION,
        "environment": get_environment(),
        "application": APP_NAME,
    }


@ops_router.get("/ready")
def readiness_check(db: Session = Depends(db_session)) -> JSONResponse:
    """
    Readiness endpoint.
    
    Verifies all dependencies (database, Redis, storage, Celery) are available.
    Returns HTTP 503 if any critical dependency is unavailable.
    Used by Kubernetes readiness probes to check if the application can handle traffic.
    """
    checks: dict[str, dict[str, Any]] = {}
    
    # Database check (critical)
    db_healthy, db_status = check_database_health(db)
    checks["database"] = {
        "status": db_status,
        "healthy": db_healthy,
    }
    
    # Redis check (non-critical)
    redis_healthy, redis_status = check_redis_health()
    checks["redis"] = {
        "status": redis_status,
        "healthy": redis_healthy,
    }
    
    # Storage check (critical)
    storage_healthy, storage_status = check_storage_health()
    checks["storage"] = {
        "status": storage_status,
        "healthy": storage_healthy,
    }
    
    # Celery check (non-critical)
    celery_healthy, celery_status = check_celery_health()
    checks["celery"] = {
        "status": celery_status,
        "healthy": celery_healthy,
    }
    
    # Determine overall readiness
    # Critical dependencies: database, storage
    critical_healthy = db_healthy and storage_healthy
    all_healthy = critical_healthy and redis_healthy and celery_healthy
    
    overall_status = "ready" if critical_healthy else "not_ready"
    
    return JSONResponse(
        status_code=200 if critical_healthy else 503,
        content={
            "status": overall_status,
            "timestamp": datetime.now(UTC).isoformat(),
            "version": APP_VERSION,
            "environment": get_environment(),
            "checks": checks,
        },
    )


@ops_router.get("/version")
def version_info() -> dict[str, Any]:
    """
    Version information endpoint.
    
    Returns application version, git commit, build number, build date, and environment.
    """
    return {
        "application": APP_NAME,
        "version": APP_VERSION,
        "git_commit": get_git_commit(),
        "build_number": get_build_number(),
        "build_date": get_build_date(),
        "environment": get_environment(),
        "timestamp": datetime.now(UTC).isoformat(),
    }


@ops_router.get("/metrics")
def metrics() -> PlainTextResponse:
    """
    Prometheus metrics endpoint.
    
    Returns Prometheus-compatible metrics for monitoring.
    Current metrics: HTTP requests, HTTP errors, uptime, application info.
    """
    # Get HTTP metrics from health module
    http_metrics = get_http_metrics()
    http_requests_total = http_metrics.get("http_requests_total", 0)
    http_errors_total = http_metrics.get("http_errors_total", 0)
    
    lines = [
        "# HELP telite_http_requests_total Total HTTP requests handled by the API.",
        "# TYPE telite_http_requests_total counter",
        f"telite_http_requests_total {http_requests_total}",
        "# HELP telite_http_errors_total Total HTTP 5xx responses.",
        "# TYPE telite_http_errors_total counter",
        f"telite_http_errors_total {http_errors_total}",
        "# HELP telite_uptime_seconds Application uptime in seconds.",
        "# TYPE telite_uptime_seconds gauge",
        f"telite_uptime_seconds {get_uptime_seconds()}",
        "# HELP telite_info Application information.",
        "# TYPE telite_info gauge",
        f'telite_info{{version="{APP_VERSION}",environment="{get_environment()}"}} 1',
    ]
    return PlainTextResponse("\n".join(lines) + "\n")


@ops_router.get("/status")
def status_check(db: Session = Depends(db_session)) -> dict[str, Any]:
    """
    Comprehensive status endpoint.
    
    Returns detailed status including health, version, and dependency checks.
    """
    db_healthy, db_status = check_database_health(db)
    redis_healthy, redis_status = check_redis_health()
    storage_healthy, storage_status = check_storage_health()
    celery_healthy, celery_status = check_celery_health()
    
    return {
        "status": "healthy" if db_healthy and storage_healthy else "degraded",
        "timestamp": datetime.now(UTC).isoformat(),
        "uptime_seconds": get_uptime_seconds(),
        "version": APP_VERSION,
        "environment": get_environment(),
        "application": APP_NAME,
        "dependencies": {
            "database": {
                "status": db_status,
                "healthy": db_healthy,
            },
            "redis": {
                "status": redis_status,
                "healthy": redis_healthy,
            },
            "storage": {
                "status": storage_status,
                "healthy": storage_healthy,
            },
            "celery": {
                "status": celery_status,
                "healthy": celery_healthy,
            },
        },
    }