from __future__ import annotations

import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.auth import auth_router
from app.api.routes.dashboard import dashboard_router
from app.api.routes.enrolments import enrol_router
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
from app.api.routes.audit import audit_router
from app.core.request_context import reset_request_id, set_request_id
from app.core.domain_context import resolve_domain_context
from app.core.rate_limiter import close_redis_connection
from app.db.engine import dispose_engine, db_session
from sqlalchemy.orm import Session

# ── Structured logging ───────────────────────────────────────────────────────

import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, "%Y-%m-%d %H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)

env_mode = os.getenv("ENVIRONMENT", "development").lower()

if env_mode in ("production", "prod", "staging"):
    # Set up root logger with JSON formatter for production
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)
else:
    # Development friendly plain-text formatting
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

logger = logging.getLogger("telite.api")


# ── App lifecycle ────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting up FastAPI application...")
    yield
    dispose_engine()
    close_redis_connection()
    logger.info("Shutting down.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Telite LMS API",
        description="Role-aware backend for the Telite Systems LMS mockups",
        version="5.1.0",
        lifespan=lifespan,
    )

    _default_origins = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:8080",
        "http://localhost:8082",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:8082",
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
    from app.api.routes.player_api import player_router
    from app.api.routes.authoring import authoring_router
    app.include_router(auth_router)
    app.include_router(learner_router, prefix="/api/v1")
    app.include_router(player_router, prefix="/api/v1")
    app.include_router(authoring_router)
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
    app.include_router(audit_router)

    uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

    @app.get("/")
    def root():
        return {
            "status": "ok",
            "message": "Telite LMS API",
            "version": "5.1.0",
            "docs": "/docs",
            "health": "/health",
        }

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

    return app


app = create_app()
