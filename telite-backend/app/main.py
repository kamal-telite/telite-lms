from __future__ import annotations

import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.auth import auth_router
from app.api.routes.dashboard import dashboard_router
from app.api.routes.enrolments import enrol_router
from app.api.routes.management import management_router
from app.integrations.moodle_bridge import moodle_health_check, moodle_health_detail, moodle_mode
from app.api.routes.pal import pal_router
from app.api.routes.payments import payment_router
from app.api.routes.platform import invitation_router, platform_router
from app.api.routes.signup import signup_router
from app.api.routes.tasks import task_router
from app.api.routes.branding import branding_router
from app.api.routes.admin_branding import admin_branding_router
from app.api.routes.sessions import sessions_router
from app.api.routes.moodle_sync import moodle_sync_router  # Phase 5: async Moodle sync observability
from app.core.request_context import reset_request_id, set_request_id
from app.core.domain_context import resolve_domain_context
from app.core.rate_limiter import close_redis_connection
from app.services.store import (
    close_postgres_pool,
    count_active_learners,
    count_pending_approvals,
    count_pending_signups,
    init_db,
    list_admins,
    list_categories,
    verify_database_connection,
)
from app.db.init_db import run_phase3_init
from app.db.engine import dispose_engine


# ── Structured logging ───────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("telite.api")


# ── App lifecycle ────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Initialising database …")
    # Phase 1-2: legacy store.py init (raw SQL, existing tables)
    init_db()
    verify_database_connection()
    # Phase 3: SQLAlchemy ORM tables + RLS
    run_phase3_init()
    logger.info("Database ready. Moodle mode: %s", moodle_mode())
    yield
    close_postgres_pool()
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

    # ── CORS — env-configurable with sensible defaults ────────────────────
    # allow_credentials=True is required for HttpOnly cookie auth.
    # Wildcard origins ("*") are NOT allowed when allow_credentials=True —
    # origins must be explicitly listed.
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
        allow_credentials=True,          # required for HttpOnly cookie auth
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"], # let frontend read trace IDs
    )

    # ── Request tracing + logging middleware ─────────────────────────────────

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

    # ── Routers ──────────────────────────────────────────────────────────

    app.include_router(auth_router)
    app.include_router(dashboard_router)
    app.include_router(management_router)
    app.include_router(enrol_router)
    app.include_router(task_router)
    app.include_router(pal_router)
    app.include_router(payment_router)
    app.include_router(signup_router)
    app.include_router(platform_router)
    app.include_router(invitation_router)
    app.include_router(branding_router)   # Phase 3: public branding endpoint
    app.include_router(admin_branding_router) # Phase 7: admin branding configuration
    app.include_router(sessions_router)   # Phase 4: session revocation/device tracking
    app.include_router(moodle_sync_router)  # Phase 5: async Moodle sync observability

    # ── Static Files (Phase 7: Branding Uploads) ─────────────────────────
    uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

    # ── Root ─────────────────────────────────────────────────────────────

    @app.get("/")
    def root():
        return {
            "status": "ok",
            "message": "Telite LMS API",
            "version": "5.1.0",
            "docs": "/docs",
            "health": "/health",
            "moodle_health": "/moodle/health",
        }

    # ── Health ───────────────────────────────────────────────────────────

    @app.get("/health")
    def health():
        mode = moodle_mode()
        moodle_ok = moodle_health_check()
        return {
            "status": "ok",
            "api": "running",
            "version": "5.1.0",
            "database": "ok",
            "moodle_mode": mode,
            "moodle_connection": (
                "mock mode enabled for local development"
                if mode == "mock"
                else ("ok" if moodle_ok else "failed")
            ),
            "categories_loaded": len(list_categories(include_archived=True)),
            "students_loaded": count_active_learners(),
            "faculty_loaded": len(list_admins()),
            "pending_enrollment_requests": count_pending_approvals(),
            "pending_signups": count_pending_signups(),
        }

    # ── Liveness (lightweight — no Moodle call) ──────────────────────────

    @app.get("/health/liveness")
    def liveness():
        """Lightweight liveness probe that skips Moodle connectivity.

        Use this for Kubernetes/load-balancer liveness checks.
        Use /health for full readiness checks.
        """
        return {
            "status": "ok",
            "api": "running",
            "version": "5.1.0",
        }

    # ── Moodle health (detailed) ─────────────────────────────────────────

    @app.get("/moodle/health")
    def moodle_health():
        """Detailed Moodle connectivity check.

        Returns connection status, token validity, site name,
        available function count, and response time.
        """
        return moodle_health_detail()

    return app


app = create_app()
