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
from app.core.domain_context import resolve_domain_context
from app.core.logging_config import configure_logging
from app.core.rate_limiter import close_redis_connection
from app.core.request_context import reset_request_id, set_request_id
from app.core.runtime import is_production_like
from app.core.storage_paths import branding_upload_root, media_upload_root, upload_root
from app.db.engine import dispose_engine, db_session
from sqlalchemy.orm import Session
from app.db.init_db import run_phase3_init

configure_logging()
logger = logging.getLogger("telite.api")

_metrics = {"http_requests_total": 0, "http_errors_total": 0}


# ── App lifecycle ────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Initialising database …")
    run_phase3_init()
    logger.info("Database ready.")
    yield
    dispose_engine()
    close_redis_connection()
    logger.info("Shutting down.")


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
        token = set_request_id(request_id)
        start = time.perf_counter()
        client_ip = request.client.host if request.client else "-"
        query_string = f"?{request.url.query}" if request.url.query else ""
        route = f"{request.url.path}{query_string}"

        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
            logger.exception(
                "[%s] %s %s from %s -> 500 (%.1fms)",
                request_id,
                request.method,
                route,
                client_ip,
                elapsed_ms,
            )
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal Server Error"},
            )
        else:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
            _metrics["http_requests_total"] += 1
            if response.status_code >= 500:
                _metrics["http_errors_total"] += 1
            logger.info(
                "[%s] %s %s from %s -> %d (%.1fms)",
                request_id,
                request.method,
                route,
                client_ip,
                response.status_code,
                elapsed_ms,
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
    from app.api.routes.notifications import notifications_router
    from app.api.routes.certificates import cert_router, public_cert_router
    from app.api.routes.gradebook import gradebook_router
    
    app.include_router(auth_router)
    app.include_router(assignment_router, prefix="/api/v1")
    app.include_router(learner_router, prefix="/api/v1")
    app.include_router(player_router, prefix="/api/v1")
    app.include_router(v1_enrol_router, prefix="/api/v1")
    app.include_router(authoring_router)
    app.include_router(question_bank_router, prefix="/api/v1")
    app.include_router(notifications_router, prefix="/api/v1")
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

    uploads_dir = upload_root()
    media_dir = media_upload_root()
    branding_dir = branding_upload_root()
    media_dir.mkdir(parents=True, exist_ok=True)
    branding_dir.mkdir(parents=True, exist_ok=True)

    @app.get("/uploads/media/{org_id}/{filename:path}", include_in_schema=False)
    def secure_local_media(
        org_id: int,
        filename: str,
        current_user: TokenData = Depends(get_current_user),
    ):
        if not current_user.is_platform_admin and current_user.org_id != org_id:
            raise HTTPException(status_code=404, detail="Media not found")

        org_dir = (media_dir / str(org_id)).resolve()
        candidate = (org_dir / filename).resolve()
        try:
            candidate.relative_to(org_dir)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="Media not found") from exc
        if not candidate.is_file():
            raise HTTPException(status_code=404, detail="Media not found")
        return FileResponse(candidate)

    app.mount("/uploads/branding", StaticFiles(directory=branding_dir), name="branding_uploads")

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
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "api": "running",
            "version": "5.1.0",
            "database": "ok",
            "architecture": "pure_native",
        }

    @app.get("/health/liveness")
    def liveness():
        return {
            "status": "ok",
            "api": "running",
            "version": "5.1.0",
        }

    @app.get("/health/readiness")
    def readiness(db: Session = Depends(db_session)):
        from sqlalchemy import text

        checks: dict[str, str] = {}
        try:
            db.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception:
            logger.exception("Readiness check failed: database")
            checks["database"] = "error"

        redis_status = "skipped"
        if os.getenv("REDIS_ENABLED", "true").lower() in ("true", "1", "yes"):
            try:
                from app.core.rate_limiter import _get_redis_client

                client = _get_redis_client()
                if client is None:
                    redis_status = "unavailable"
                else:
                    client.ping()
                    redis_status = "ok"
            except Exception:
                logger.exception("Readiness check failed: redis")
                redis_status = "error"
        checks["redis"] = redis_status

        ready = checks["database"] == "ok" and redis_status in ("ok", "skipped")
        return JSONResponse(
            status_code=200 if ready else 503,
            content={
                "status": "ok" if ready else "degraded",
                "api": "running",
                "version": "5.1.0",
                "checks": checks,
            },
        )

    @app.get("/metrics")
    def metrics():
        lines = [
            "# HELP telite_http_requests_total Total HTTP requests handled by the API.",
            "# TYPE telite_http_requests_total counter",
            f"telite_http_requests_total {_metrics['http_requests_total']}",
            "# HELP telite_http_errors_total Total HTTP 5xx responses.",
            "# TYPE telite_http_errors_total counter",
            f"telite_http_errors_total {_metrics['http_errors_total']}",
        ]
        return PlainTextResponse("\n".join(lines) + "\n")

    return app


app = create_app()
