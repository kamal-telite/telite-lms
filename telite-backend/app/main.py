from __future__ import annotations

import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

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
from app.services.store import count_active_learners, count_pending_approvals, count_pending_signups, init_db, list_admins, list_categories


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
    init_db()
    logger.info("Database ready. Moodle mode: %s", moodle_mode())
    yield
    logger.info("Shutting down.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Telite LMS API",
        description="Role-aware backend for the Telite Systems LMS mockups",
        version="5.1.0",
        lifespan=lifespan,
    )

    # ── CORS — env-configurable with sensible defaults ────────────────────
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
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request tracing + logging middleware ─────────────────────────────────

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        # Generate or reuse an incoming trace ID
        trace_id = request.headers.get("x-request-id") or str(uuid.uuid4())[:12]
        start = time.time()
        response = await call_next(request)
        elapsed_ms = round((time.time() - start) * 1000, 1)
        logger.info(
            "[%s] %s %s → %d (%.1fms)",
            trace_id,
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        response.headers["X-Request-ID"] = trace_id
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
