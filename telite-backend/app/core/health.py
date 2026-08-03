"""Production operational endpoints for monitoring and deployment."""

from __future__ import annotations

import logging
import os
import time
from datetime import UTC, datetime
from typing import Any

from fastapi import Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.runtime import is_production_like

logger = logging.getLogger("telite.ops")

# Application startup time for uptime calculation
_startup_time = time.time()

# Application metadata
APP_VERSION = "5.1.0"
APP_NAME = "Telite LMS API"

# HTTP metrics (maintained in main.py, accessible here)
_http_metrics = {"http_requests_total": 0, "http_errors_total": 0}

def update_http_metrics(requests_total: int, errors_total: int) -> None:
    """Update HTTP metrics from main app."""
    global _http_metrics
    _http_metrics = {
        "http_requests_total": requests_total,
        "http_errors_total": errors_total,
    }

def get_http_metrics() -> dict[str, int]:
    """Get current HTTP metrics."""
    return _http_metrics.copy()

# HTTP metrics (maintained in main.py, accessible here)
_http_metrics = {"http_requests_total": 0, "http_errors_total": 0}

def set_http_metrics(requests_total: int, errors_total: int) -> None:
    """Set HTTP metrics from main app."""
    global _http_metrics
    _http_metrics = {
        "http_requests_total": requests_total,
        "http_errors_total": errors_total,
    }

def get_http_metrics() -> dict[str, int]:
    """Get current HTTP metrics."""
    return _http_metrics.copy()


def get_uptime_seconds() -> float:
    """Get application uptime in seconds."""
    return time.time() - _startup_time


def get_git_commit() -> str | None:
    """Get git commit hash if available."""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__)),
        )
        if result.returncode == 0:
            return result.stdout.strip()[:8]  # Short hash
    except Exception:
        pass
    return None


def get_build_number() -> str | None:
    """Get build number from environment or git."""
    # Try environment variable first
    build_num = os.getenv("BUILD_NUMBER")
    if build_num:
        return build_num
    
    # Try git commit count as fallback
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__)),
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def get_build_date() -> str | None:
    """Get build date from environment or git."""
    # Try environment variable first
    build_date = os.getenv("BUILD_DATE")
    if build_date:
        return build_date
    
    # Try git commit date as fallback
    try:
        import subprocess
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ci", "--date=iso"],
            check=True,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__)),
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def get_environment() -> str:
    """Get current environment."""
    return os.getenv("ENVIRONMENT", "development")


def check_database_health(db: Session) -> tuple[bool, str]:
    """Check database connectivity."""
    try:
        db.execute(text("SELECT 1"))
        return True, "healthy"
    except Exception as exc:
        logger.error("Database health check failed", exc_info=True)
        return False, f"unhealthy: {str(exc)}"


def check_redis_health() -> tuple[bool, str]:
    """Check Redis connectivity."""
    if os.getenv("REDIS_ENABLED", "true").lower() not in ("true", "1", "yes"):
        return True, "skipped"
    
    try:
        from app.core.rate_limiter import _get_redis_client
        client = _get_redis_client()
        if client is None:
            return False, "unavailable"
        client.ping()
        return True, "healthy"
    except Exception as exc:
        logger.error("Redis health check failed", exc_info=True)
        return False, f"unhealthy: {str(exc)}"


def check_storage_health() -> tuple[bool, str]:
    """Check storage provider connectivity."""
    storage_provider = os.getenv("STORAGE_PROVIDER", "local")
    
    if storage_provider == "local":
        # Local storage is always available
        return True, "healthy"
    
    elif storage_provider == "s3":
        try:
            from app.services.storage import get_storage_provider
            storage = get_storage_provider()
            # Try a minimal operation to verify connectivity
            # For S3, we'll just check if the provider is configured
            if storage and hasattr(storage, 'bucket'):
                return True, "healthy"
            return False, "unavailable"
        except Exception as exc:
            logger.error("Storage health check failed", exc_info=True)
            return False, f"unhealthy: {str(exc)}"
    
    else:
        logger.warning(f"Unknown storage provider: {storage_provider}")
        return True, "skipped"


def check_celery_health() -> tuple[bool, str]:
    """Check Celery connectivity if configured."""
    try:
        from app.workers.celery_app import celery_app
        # Check if Celery is configured
        if celery_app.conf.broker_url:
            # Simple ping to broker
            try:
                celery_app.control.ping()
                return True, "healthy"
            except Exception as exc:
                logger.error("Celery health check failed", exc_info=True)
                return False, f"unhealthy: {str(exc)}"
        else:
            return True, "skipped"
    except ImportError:
        # Celery not configured
        return True, "skipped"
    except Exception as exc:
        logger.error("Celery health check failed", exc_info=True)
        return False, f"unhealthy: {str(exc)}"


def validate_startup_config() -> dict[str, Any]:
    """
    Validate startup configuration and dependencies.
    
    Returns a dictionary with validation results for each component.
    Logs failures clearly and provides detailed status.
    """
    results: dict[str, Any] = {
        "app_name": APP_NAME,
        "version": APP_VERSION,
        "environment": get_environment(),
        "timestamp": datetime.now(UTC).isoformat(),
        "components": {},
    }
    
    # Validate database connection
    try:
        from app.db.engine import get_engine
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        results["components"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful",
        }
        logger.info("Database connection validated successfully")
    except Exception as exc:
        results["components"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(exc)}",
        }
        logger.error("Database connection validation failed", exc_info=True)
    
    # Validate Redis connection
    try:
        redis_healthy, redis_status = check_redis_health()
        results["components"]["redis"] = {
            "status": redis_status,
            "message": f"Redis status: {redis_status}",
        }
        if redis_healthy:
            logger.info("Redis connection validated successfully")
        else:
            logger.warning(f"Redis validation returned: {redis_status}")
    except Exception as exc:
        results["components"]["redis"] = {
            "status": "unhealthy",
            "message": f"Redis validation failed: {str(exc)}",
        }
        logger.error("Redis validation failed", exc_info=True)
    
    # Validate storage provider
    try:
        storage_healthy, storage_status = check_storage_health()
        results["components"]["storage"] = {
            "status": storage_status,
            "message": f"Storage provider status: {storage_status}",
        }
        if storage_healthy:
            logger.info("Storage provider validated successfully")
        else:
            logger.warning(f"Storage provider validation returned: {storage_status}")
    except Exception as exc:
        results["components"]["storage"] = {
            "status": "unhealthy",
            "message": f"Storage validation failed: {str(exc)}",
        }
        logger.error("Storage validation failed", exc_info=True)
    
    # Validate critical environment variables
    critical_env_vars = {
        "TELITE_AUTH_SECRET": os.getenv("TELITE_AUTH_SECRET"),
        "TELITE_PASSWORD_SALT": os.getenv("TELITE_PASSWORD_SALT"),
    }
    
    env_validation = {}
    for var_name, var_value in critical_env_vars.items():
        if var_value:
            env_validation[var_name] = {
                "status": "set",
                "message": f"{var_name} is configured",
            }
        else:
            env_validation[var_name] = {
                "status": "missing",
                "message": f"{var_name} is not set (development mode)",
            }
            if is_production_like():
                logger.error(f"Critical environment variable {var_name} is missing in production")
    
    results["components"]["environment_variables"] = env_validation
    
    # Overall status
    all_healthy = all(
        comp.get("status") in ("healthy", "skipped") 
        for comp in results["components"].values()
        if isinstance(comp, dict) and "status" in comp
    )
    
    results["overall_status"] = "healthy" if all_healthy else "degraded"
    
    return results