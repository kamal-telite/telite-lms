"""
SQLAlchemy engine, session factory, and RLS context manager.

PHASE 3: Replaces the raw psycopg connection pool in store.py with a
proper SQLAlchemy 2.x engine that supports:
- Sync sessions for FastAPI route handlers
- PostgreSQL Row-Level Security via SET LOCAL
- Connection pooling with health checks
- SQLite fallback for local development
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger("telite.db.engine")

# ── DSN resolution ────────────────────────────────────────────────────────────

def _build_dsn() -> str:
    """Build the database connection string from environment variables."""
    # Explicit URL takes priority
    url = os.getenv("TELITE_DATABASE_URL", "").strip()
    if url:
        # SQLAlchemy needs postgresql+psycopg:// not postgresql://
        if url.startswith("postgresql://") or url.startswith("postgres://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
            url = url.replace("postgres://", "postgresql+psycopg://", 1)
        return url

    # SQLite fallback for local dev
    backend = os.getenv("TELITE_DB_BACKEND", "sqlite").lower()
    if backend == "sqlite":
        db_path = os.getenv("TELITE_DB_PATH", "data/telite_lms.db")
        return f"sqlite:///{db_path}"

    # Build PostgreSQL DSN from individual env vars
    host = os.getenv("TELITE_POSTGRES_HOST") or os.getenv("POSTGRES_HOST") or "localhost"
    port = os.getenv("TELITE_POSTGRES_PORT") or os.getenv("POSTGRES_PORT") or "5432"
    db   = os.getenv("TELITE_POSTGRES_DB")   or os.getenv("POSTGRES_DB")
    user = os.getenv("TELITE_POSTGRES_USER") or os.getenv("POSTGRES_USER")
    pw   = os.getenv("TELITE_POSTGRES_PASSWORD") or os.getenv("POSTGRES_PASSWORD")

    if not all([db, user, pw]):
        raise RuntimeError(
            "PostgreSQL credentials incomplete. "
            "Set TELITE_DATABASE_URL or TELITE_POSTGRES_* variables."
        )

    from urllib.parse import quote_plus
    return f"postgresql+psycopg://{quote_plus(user)}:{quote_plus(pw)}@{host}:{port}/{db}"


# ── Engine factory ────────────────────────────────────────────────────────────

def _create_engine():
    dsn = _build_dsn()
    is_sqlite = dsn.startswith("sqlite")

    kwargs: dict = {
        "echo": os.getenv("SQLALCHEMY_ECHO", "false").lower() == "true",
        "future": True,
    }

    if not is_sqlite:
        kwargs.update(
            {
                "pool_size": int(os.getenv("TELITE_POSTGRES_POOL_MIN_SIZE", "2")),
                "max_overflow": int(os.getenv("TELITE_POSTGRES_POOL_MAX_SIZE", "20")) - 2,
                "pool_timeout": int(os.getenv("TELITE_POSTGRES_POOL_TIMEOUT_SECONDS", "30")),
                "pool_pre_ping": True,  # detect stale connections
                "connect_args": {
                    "connect_timeout": int(
                        os.getenv("TELITE_POSTGRES_CONNECT_TIMEOUT_SECONDS", "10")
                    )
                },
            }
        )
    else:
        kwargs["connect_args"] = {"check_same_thread": False}

    engine = create_engine(dsn, **kwargs)

    # Enable WAL mode for SQLite (better concurrent reads)
    if is_sqlite:
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_conn, _):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    logger.info("SQLAlchemy engine created: %s", dsn.split("@")[-1] if "@" in dsn else dsn)
    return engine


# Singleton engine — created once at import time
_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = _create_engine()
    return _engine


def get_session_factory() -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _SessionLocal


# ── Session context managers ──────────────────────────────────────────────────

@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Provide a transactional database session.

    Usage:
        with get_db_session() as session:
            user = session.get(User, user_id)
    """
    factory = get_session_factory()
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def get_tenant_session(org_id: int) -> Generator[Session, None, None]:
    """
    Provide a session with PostgreSQL RLS context set.

    Sets app.current_org_id so RLS policies filter rows automatically.
    Falls back gracefully on SQLite (no RLS support).

    Usage:
        with get_tenant_session(org_id=3) as session:
            courses = session.execute(select(Course)).scalars().all()
            # Only courses for org_id=3 are returned (RLS enforced)
    """
    factory = get_session_factory()
    session: Session = factory()
    is_postgres = not _build_dsn().startswith("sqlite")

    try:
        if is_postgres:
            # Set RLS context for this transaction
            session.execute(
                text("SET LOCAL app.current_org_id = :org_id"),
                {"org_id": org_id},
            )
            session.execute(text("SET LOCAL app.bypass_rls = 'off'"))

        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def get_platform_session() -> Generator[Session, None, None]:
    """
    Provide a session that bypasses RLS (platform admin operations).

    Only use for platform-level operations that legitimately need
    cross-tenant access (e.g., listing all organisations).
    """
    factory = get_session_factory()
    session: Session = factory()
    is_postgres = not _build_dsn().startswith("sqlite")

    try:
        if is_postgres:
            session.execute(text("SET LOCAL app.bypass_rls = 'on'"))

        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ── FastAPI dependency ────────────────────────────────────────────────────────

def db_session():
    """
    FastAPI dependency that yields a database session.

    Usage:
        @router.get("/items")
        def list_items(db: Session = Depends(db_session)):
            ...
    """
    with get_db_session() as session:
        yield session


def dispose_engine() -> None:
    """Dispose the engine connection pool (called on app shutdown)."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
        _engine = None
        _SessionLocal = None
        logger.info("SQLAlchemy engine disposed.")
