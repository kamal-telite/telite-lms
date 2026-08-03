from __future__ import annotations

import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.auth import TokenData, auth_router, get_current_user
from app.api.routes.dashboard import dashboard_router
from app.api.routes.enrolments import enrol_router, v1_enrol_router
from app.api.routes.management import management_router
from app.api.routes.pal import pal_router
from app.api.routes.payments import payment_router
from app.api.routes.platform import invitation_router, platform_router
from app.api.routes.signup import signup_router
from app.api.routes.tasks import task_router
from app.api.routes.branding import branding_router
from app.api.routes.admin_branding import admin_branding_router
from app.api.routes.sessions import sessions_router
from app.api.routes.builder import builder_router
from app.api.routes.publishing import publishing_router
from app.api.routes.media import media_router
from app.api.routes.permissions import permissions_router
from app.api.routes.learning_paths import learning_paths_router
from app.api.routes.announcements import announcements_router
from app.api.routes.audit import audit_router
from app.api.routes.ops import ops_router
from app.core.domain_context import resolve_domain_context
from app.core.logging_config import configure_logging
from app.core.observability import log_slow_request, setup_query_logging
from app.core.rate_limiter import close_redis_connection
from app.core.health import set_http_metrics, update_http_metrics
from app.core.request_context import (
    get_org_id,
    get_request_id,
    get_user_id,
    reset_request_id,
    set_endpoint,
    set_http_method,
    set_org_id,
    set_request_id,
    set_user_id,
)
from app.core.runtime import is_production_like
from app.core.storage_paths import branding_upload_root, certificate_upload_root, media_upload_root, upload_root
from app.core.health import validate_startup_config
from app.core.deployment import fail_deployment_if_invalid, update_http_metrics
from app.db.engine import dispose_engine, db_session
from sqlalchemy.orm import Session
from app.db.init_db import run_phase3_init

configure_logging()
logger = logging.getLogger("telite.api")

_metrics = {"http_requests_total": 0, "http_errors_total": 0}

def get_metrics() -> dict[str, int]:
    """Get current HTTP metrics (for operational endpoints)."""
    return _metrics.copy()


# ── App lifecycle ────────────────────────────────────────────────────────────


def _validate_security_config():
    """Validate critical security configuration during startup."""
    from app.core.runtime import is_production_like
    
    is_prod = is_production_like()
    
    # Validate AUTH_SECRET
    auth_secret = os.getenv("TELITE_AUTH_SECRET", "").strip()
    if not auth_secret:
        if is_prod:
            raise RuntimeError(
                "TELITE_AUTH_SECRET environment variable is required in production. "
                "Set a secure random string (minimum 32 characters)."
            )
        else:
            logger.warning(
                "TELITE_AUTH_SECRET not set. Using development fallback. "
                "This is not secure and should never be used in production."
            )
    elif len(auth_secret) < 32:
        if is_prod:
            raise RuntimeError(
                f"TELITE_AUTH_SECRET is too short ({len(auth_secret)} characters). "
                "Minimum 32 characters required for production security."
            )
        else:
            logger.warning(
                f"TELITE_AUTH_SECRET is too short ({len(auth_secret)} characters). "
                "Minimum 32 characters recommended for production security."
            )
    
    # Validate PASSWORD_SALT
    password_salt = os.getenv("TELITE_PASSWORD_SALT", "").strip()
    if not password_salt:
        if is_prod:
            raise RuntimeError(
                "TELITE_PASSWORD_SALT environment variable is required in production. "
                "Set a secure random string (minimum 16 characters)."
            )
        else:
            logger.warning(
                "TELITE_PASSWORD_SALT not set. Using development fallback. "
                "This is not secure and should never be used in production."
            )
    elif len(password_salt) < 16:
        if is_prod:
            raise RuntimeError(
                f"TELITE_PASSWORD_SALT is too short ({len(password_salt)} characters). "
                "Minimum 16 characters required for production security."
            )
        else:
            logger.warning(
                f"TELITE_PASSWORD_SALT is too short ({len(password_salt)} characters). "
                "Minimum 16 characters recommended for production security."
            )
    
    logger.info("Security configuration validated successfully.")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Step 1: Validate deployment configuration
    logger.info("Step 1: Validating deployment configuration...")
    fail_deployment_if_invalid()
    logger.info("Deployment configuration validated successfully")
    
    # Step 2: Validate critical security configuration
    logger.info("Step 2: Validating security configuration...")
    _validate_security_config()
    logger.info("Security configuration validated successfully")
    
    # Step 3: Set up database query logging
    logger.info("Step 3: Setting up database query logging...")
    from app.db.engine import get_engine
    engine = get_engine()
    setup_query_logging(engine)
    logger.info("Database query logging configured")
    
    # Step 4: Initialize database
    logger.info("Step 4: Initializing database...")
    run_phase3_init()
    logger.info("Database initialized successfully")
    
    # Step 5: Validate startup configuration and dependencies
    logger.info("Step 5: Validating startup dependencies...")
    from app.core.health import validate_startup_config
    startup_validation = validate_startup_config()
    
    # Log startup validation results
    logger.info(
        "Application startup validation",
        extra={
            "app_version": startup_validation["version"],
            "environment": startup_validation["environment"],
            "overall_status": startup_validation["overall_status"],
            "components": startup_validation["components"],
        },
    )
    
    if startup_validation["overall_status"] != "healthy":
        logger.warning("Startup validation completed with degraded status; continuing in development mode.")
        logger.warning(f"Component status: {startup_validation['components']}")
    
    logger.info("=== Application startup sequence completed successfully ===")
    logger.info("Application is ready to accept traffic")
    
    yield
    
    # Graceful shutdown sequence
    logger.info("=== Graceful shutdown sequence started ===")
    logger.info("Step 1: Closing database connections...")
    dispose_engine()
    logger.info("Database connections closed")
    
    logger.info("Step 2: Closing Redis connections...")
    close_redis_connection()
    logger.info("Redis connections closed")
    
    logger.info("=== Graceful shutdown completed ===")
    logger.info("Application stopped gracefully")


def create_app() -> FastAPI:
    _prod = is_production_like()
    app = FastAPI(
        title="Telite LMS API",
        description="Role-aware backend for the Telite Systems LMS",
        version="5.1.0",
        lifespan=lifespan,
        docs_url=None if _prod else "/docs",
        redoc_url=None if _prod else "/redoc",
        openapi_url=None if _prod else "/openapi.json",
    )

    frontend_port = os.getenv("FRONTEND_PORT") or os.getenv("VITE_FRONTEND_DEV_PORT", "3000")
    frontend_dev_port = os.getenv("VITE_DEV_SERVER_PORT", "5173")
    _default_origins = [
        f"http://localhost:{frontend_port}",
        f"http://127.0.0.1:{frontend_port}",
        f"http://localhost:{frontend_dev_port}",
        f"http://127.0.0.1:{frontend_dev_port}",
    ]
    _env_origins = os.getenv("TELITE_CORS_ORIGINS", "").strip()
    cors_origins = (
        [origin.strip() for origin in _env_origins.split(",") if origin.strip()]
        if _env_origins
        else _default_origins
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        request.state.started_at = time.time()
        request.state.domain_context = resolve_domain_context(request)
        
        # Set request context for logging
        token = set_request_id(request_id)
        start = time.perf_counter()
        client_ip = request.client.host if request.client else "-"
        query_string = f"?{request.url.query}" if request.url.query else ""
        route = f"{request.url.path}{query_string}"
        
        # Set HTTP context for error logging
        set_endpoint(request.url.path)
        set_http_method(request.method)

        try:
            response = await call_next(request)
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
            
            # Extract exception info for structured logging
            exc_info = get_safe_exception_info(e)
            
            # Log with full context
            logger.error(
                f"Request failed: {request.method} {route}",
                extra={
                    "request_id": request_id,
                    "endpoint": request.url.path,
                    "http_method": request.method,
                    "org_id": get_org_id(),
                    "user_id": get_user_id(),
                    "exception_type": exc_info["exception_type"],
                    "exception_message": exc_info["exception_message"],
                    "duration_ms": elapsed_ms,
                },
                exc_info=True,
            )
            
            # Keep legacy exception logging for compatibility
            try:
                import traceback
                log_path = Path(__file__).parent.parent / "exception.log"
                with open(log_path, "a") as f:
                    f.write(f"=== Request: {request.method} {route} ===\n")
                    traceback.print_exc(file=f)
                    f.write("\n")
            except Exception:
                pass
            
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal Server Error"},
            )
        else:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
            _metrics["http_requests_total"] += 1
            if response.status_code >= 500:
                _metrics["http_errors_total"] += 1
            # Sync metrics to health module for operational endpoints
            update_http_metrics(_metrics["http_requests_total"], _metrics["http_errors_total"])
            # Sync metrics to health module
            set_http_metrics(_metrics["http_requests_total"], _metrics["http_errors_total"])
            
            # Log slow requests
            if elapsed_ms > 500:  # 500ms threshold
                log_slow_request(
                    endpoint=request.url.path,
                    http_method=request.method,
                    duration_ms=elapsed_ms,
                    request_id=request_id,
                    user_id=get_user_id(),
                    org_id=get_org_id(),
                )
            
            # Standard request logging
            logger.info(
                f"{request.method} {route} -> {response.status_code}",
                extra={
                    "request_id": request_id,
                    "endpoint": request.url.path,
                    "http_method": request.method,
                    "status_code": response.status_code,
                    "duration_ms": elapsed_ms,
                    "org_id": get_org_id(),
                    "user_id": get_user_id(),
                },
            )
        finally:
            reset_request_id(token)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Telite-Domain-Mode"] = (
            "platform" if request.state.domain_context.is_platform else "tenant"
        )
        return response

    from app.api.routes.learner import learner_router
    from app.api.routes.assignments import assignment_router
    from app.api.routes.player_api import player_router
    from app.api.routes.authoring import authoring_router
    from app.api.routes.question_bank import question_bank_router
    from app.api.routes.quiz_authoring import quiz_authoring_router
    from app.api.routes.quiz_execution import quiz_execution_router
    from app.api.routes.quiz_grading import quiz_grading_router
    from app.api.routes.notifications import notifications_router
    from app.api.routes.notification_preferences import router as notification_preferences_router
    from app.api.routes.certificates import cert_router, public_cert_router
    from app.api.routes.gradebook import gradebook_router
    
    app.include_router(auth_router)
    app.include_router(assignment_router, prefix="/api/v1")
    app.include_router(learner_router, prefix="/api/v1")
    app.include_router(player_router, prefix="/api/v1")
    app.include_router(v1_enrol_router, prefix="/api/v1")
    app.include_router(authoring_router)
    app.include_router(question_bank_router, prefix="/api/v1")
    app.include_router(quiz_authoring_router)
    app.include_router(quiz_execution_router)
    app.include_router(quiz_grading_router)
    app.include_router(notifications_router, prefix="/api/v1")
    app.include_router(notification_preferences_router, prefix="/api/v1")
    app.include_router(cert_router, prefix="/api")
    app.include_router(public_cert_router)
    app.include_router(gradebook_router, prefix="/api/v1")
    app.include_router(dashboard_router)
    app.include_router(management_router)
    app.include_router(enrol_router)
    app.include_router(task_router)
    app.include_router(pal_router)
    app.include_router(payment_router)
    app.include_router(signup_router)
    app.include_router(platform_router)
    app.include_router(invitation_router)
    app.include_router(branding_router)
    app.include_router(admin_branding_router)
    app.include_router(sessions_router)
    app.include_router(builder_router)
    app.include_router(publishing_router)
    app.include_router(media_router)
    app.include_router(permissions_router)
    app.include_router(learning_paths_router)
    app.include_router(announcements_router, prefix="/api/v1")
    app.include_router(audit_router)
    app.include_router(ops_router)

    uploads_dir = upload_root()
    media_dir = media_upload_root()
    branding_dir = branding_upload_root()
    certificate_dir = certificate_upload_root()
    media_dir.mkdir(parents=True, exist_ok=True)
    branding_dir.mkdir(parents=True, exist_ok=True)
    certificate_dir.mkdir(parents=True, exist_ok=True)

    @app.get("/uploads/media/{org_id}/{filename:path}", include_in_schema=False)
    def secure_local_media(
        org_id: str,
        filename: str,
        current_user: TokenData = Depends(get_current_user),
    ):
        try:
            if org_id.startswith("org_"):
                url_org_id = int(org_id.split("_")[1])
            else:
                url_org_id = int(org_id)
        except (ValueError, IndexError):
            raise HTTPException(status_code=404, detail="Media not found")

        if not current_user.is_platform_admin and current_user.org_id != url_org_id:
            raise HTTPException(status_code=404, detail="Media not found")

        org_dir = (media_dir / org_id).resolve()
        candidate = (org_dir / filename).resolve()
        try:
            candidate.relative_to(org_dir)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="Media not found") from exc
        if not candidate.is_file():
            raise HTTPException(status_code=404, detail="Media not found")
        
        # Set appropriate Content-Type for PDFs
        media_type = None
        if filename.lower().endswith('.pdf'):
            media_type = 'application/pdf'
        
        return FileResponse(candidate, media_type=media_type)

    app.mount("/uploads/branding", StaticFiles(directory=branding_dir), name="branding_uploads")
    app.mount("/uploads/certificates", StaticFiles(directory=certificate_dir), name="certificate_uploads")

    @app.get("/")
    def root():
        payload = {
            "status": "ok",
            "message": "Telite LMS API",
            "version": "5.1.0",
            "health": "/health",
        }
        if not is_production_like():
            payload["docs"] = "/docs"
        return payload

    @app.get("/health")
    def health(db: Session = Depends(db_session)):
        """Health check endpoint (legacy - for backward compatibility)."""
        from app.core.health import check_database_health, get_uptime_seconds, APP_VERSION
        
        db_healthy, db_status = check_database_health(db)
        
        return {
            "status": "ok" if db_healthy else "error",
            "api": "running",
            "version": APP_VERSION,
            "database": db_status,
            "architecture": "pure_native",
            "uptime_seconds": get_uptime_seconds(),
        }

    @app.get("/health/liveness")
    def liveness():
        """Liveness endpoint (legacy - for backward compatibility)."""
        from app.core.health import get_uptime_seconds, APP_VERSION
        
        return {
            "status": "ok",
            "api": "running",
            "version": APP_VERSION,
            "uptime_seconds": get_uptime_seconds(),
        }

    @app.get("/health/readiness")
    def readiness(db: Session = Depends(db_session)):
        """Readiness endpoint (legacy - for backward compatibility)."""
        from app.core.health import check_database_health, check_redis_health, APP_VERSION
        
        checks: dict[str, str] = {}
        
        db_healthy, db_status = check_database_health(db)
        checks["database"] = db_status
        
        redis_healthy, redis_status = check_redis_health()
        checks["redis"] = redis_status
        
        ready = db_healthy and redis_healthy
        return JSONResponse(
            status_code=200 if ready else 503,
            content={
                "status": "ok" if ready else "degraded",
                "api": "running",
                "version": APP_VERSION,
                "checks": checks,
            },
        )

    @app.get("/metrics")
    def metrics():
        """Prometheus metrics endpoint (legacy - for backward compatibility)."""
        from app.core.health import get_uptime_seconds, APP_VERSION, get_environment
        
        lines = [
            "# HELP telite_http_requests_total Total HTTP requests handled by the API.",
            "# TYPE telite_http_requests_total counter",
            f"telite_http_requests_total {_metrics['http_requests_total']}",
            "# HELP telite_http_errors_total Total HTTP 5xx responses.",
            "# TYPE telite_http_errors_total counter",
            f"telite_http_errors_total {_metrics['http_errors_total']}",
            "# HELP telite_uptime_seconds Application uptime in seconds.",
            "# TYPE telite_uptime_seconds gauge",
            f"telite_uptime_seconds {get_uptime_seconds()}",
            "# HELP telite_info Application information.",
            "# TYPE telite_info gauge",
            f'telite_info{{version="{APP_VERSION}",environment="{get_environment()}"}} 1',
        ]
        return PlainTextResponse("\n".join(lines) + "\n")

    return app


app = create_app()
