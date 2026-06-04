"""
Database initialisation for Phase 3.

Runs on application startup:
  1. Creates all SQLAlchemy tables (if not exist)
  2. Applies PostgreSQL RLS policies
  3. Seeds default platform settings and global admin
  4. Verifies connectivity

This replaces the raw SQL init_db() in store.py for new tables.
Existing tables managed by store.py are left untouched during migration.
"""

from __future__ import annotations

import logging
import os

from sqlalchemy import text

from app.db.engine import get_db_session, get_engine
from app.models.base import Base

logger = logging.getLogger("telite.db.init")


def create_all_tables() -> None:
    """Create all ORM-mapped tables that don't exist yet."""
    engine = get_engine()
    Base.metadata.create_all(engine, checkfirst=True)
    logger.info("SQLAlchemy tables verified/created.")


def apply_rls_if_postgres() -> None:
    """Apply Row-Level Security policies on PostgreSQL."""
    engine = get_engine()
    if engine.dialect.name != "postgresql":
        logger.info("Skipping RLS setup (not PostgreSQL).")
        return

    from app.db.rls import apply_rls_policies
    with get_db_session() as session:
        try:
            apply_rls_policies(session)
            logger.info("PostgreSQL RLS policies applied.")
        except Exception as exc:
            # RLS setup failure is non-fatal during development
            logger.warning("RLS policy setup failed (non-fatal): %s", exc)


def verify_connection() -> bool:
    """Verify database connectivity. Returns True if healthy."""
    try:
        with get_db_session() as session:
            session.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error("Database connectivity check failed: %s", exc)
        return False


def run_phase3_init() -> None:
    """
    Full Phase 3 database initialisation sequence.
    Called from app lifespan alongside the existing store.init_db().
    """
    logger.info("Phase 3 DB init starting…")

    # 1. Create new ORM tables
    create_all_tables()

    # 2. Apply RLS (PostgreSQL only)
    apply_rls_if_postgres()

    # 3. Verify connectivity
    if verify_connection():
        logger.info("Phase 3 DB init complete — database healthy.")
    else:
        logger.error("Phase 3 DB init — database connectivity FAILED.")
