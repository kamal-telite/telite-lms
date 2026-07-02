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

import json
import logging
import os

from sqlalchemy import inspect, text

from app.core.runtime import is_development, is_production_like
from app.db.engine import get_db_session, get_engine, is_postgres_dsn
from app.models.base import Base

logger = logging.getLogger("telite.db.init")


def create_all_tables() -> None:
    """Create all ORM-mapped tables that don't exist yet."""
    engine = get_engine()
    Base.metadata.create_all(engine, checkfirst=True)
    logger.info("SQLAlchemy tables verified/created.")


# Legacy mixin columns only — domain columns belong in Alembic (see docs/adr/004-schema-authority.md).

def repair_shared_columns() -> None:
    """Add legacy shared mixin columns on SQLite dev bootstrap only."""
    if not _allow_legacy_schema_bootstrap():
        logger.info("Skipping repair_shared_columns; schema is Alembic-managed.")
        return

    engine = get_engine()
    inspector = inspect(engine)
    preparer = engine.dialect.identifier_preparer

    with engine.begin() as connection:
        for table in Base.metadata.sorted_tables:
            if not inspector.has_table(table.name):
                continue

            existing_columns = {column["name"] for column in inspector.get_columns(table.name)}
            quoted_table = preparer.quote(table.name)

            if "created_at" in table.c and "created_at" not in existing_columns:
                connection.execute(
                    text(f"ALTER TABLE {quoted_table} ADD COLUMN created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()")
                )
                logger.info("Added missing created_at column to %s.", table.name)
                existing_columns.add("created_at")
            elif "created_at" in table.c and engine.dialect.name == "postgresql":
                connection.execute(
                    text(f"ALTER TABLE {quoted_table} ALTER COLUMN created_at SET DEFAULT NOW()")
                )

            if "updated_at" in table.c and "updated_at" not in existing_columns:
                connection.execute(
                    text(f"ALTER TABLE {quoted_table} ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE NULL")
                )
                logger.info("Added missing updated_at column to %s.", table.name)
                existing_columns.add("updated_at")

            if "org_id" in table.c and "org_id" not in existing_columns:
                connection.execute(
                    text(f"ALTER TABLE {quoted_table} ADD COLUMN org_id INTEGER NOT NULL DEFAULT 1")
                )
                logger.info("Added missing org_id column to %s.", table.name)


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
            logger.warning("RLS policy setup failed (non-fatal): %s", exc)


def verify_connection() -> bool:
    """Verify database connectivity. Returns True if healthy."""
    try:
        with get_db_session() as session:
            session.execute(text("SELECT 1"))
        return True
    except Exception:
        logger.exception("Database connectivity check failed")
        return False


def backfill_course_modules_from_courses() -> None:
    """Populate native course_modules from legacy courses.modules_json when missing."""
    with get_db_session() as session:
        courses = session.execute(
            text(
                """
                SELECT id, org_id, modules_json
                FROM courses
                WHERE COALESCE(module_count, 0) > 0
                  AND NOT EXISTS (
                    SELECT 1 FROM course_modules WHERE course_modules.course_id = courses.id
                  )
                """
            )
        ).mappings().all()

        inserted = 0
        for course in courses:
            try:
                modules = json.loads(course["modules_json"] or "[]")
            except (TypeError, ValueError):
                modules = []

            for index, module in enumerate(modules):
                title = module.get("title") if isinstance(module, dict) else str(module)
                if not title:
                    continue

                session.execute(
                    text(
                        """
                        INSERT INTO course_modules (
                            course_id, org_id, section, section_id, status, title,
                            module_type, sort_order, content_url, created_at
                        )
                        VALUES (
                            :course_id, :org_id, 0, NULL, 'draft', :title,
                            'lesson', :sort_order, NULL, NOW()
                        )
                        """
                    ),
                    {
                        "course_id": course["id"],
                        "org_id": course["org_id"],
                        "title": title,
                        "sort_order": index,
                    },
                )
                inserted += 1

        if inserted:
            logger.info("Backfilled %d native course modules from courses.modules_json.", inserted)


def ensure_default_organization() -> None:
    """Ensure legacy seed rows pointing at org_id=1 have a parent organization."""
    with get_db_session() as session:
        exists = session.execute(text("SELECT 1 FROM organizations WHERE id = 1")).first()
        if exists:
            return

        session.execute(
            text(
                """
                INSERT INTO organizations (
                    id, name, type, domain, slug, status, plan, created_at
                )
                VALUES (
                    1, 'Telite Systems', 'company', 'telite.io', 'telite',
                    'active', 'free', CURRENT_TIMESTAMP
                )
                """
            )
        )
        logger.info("Created missing default organization with id=1.")


def _use_alembic_migrations() -> bool:
    if is_production_like():
        return True
    if is_postgres_dsn():
        return True
    return os.getenv("TELITE_USE_ALEMBIC", "").lower() in ("true", "1", "yes")


def _allow_legacy_schema_bootstrap() -> bool:
    """SQLite-only dev bootstrap. PostgreSQL and production-like envs use Alembic only."""
    if is_production_like():
        return False
    if not is_development():
        return False
    if _use_alembic_migrations():
        return False
    if is_postgres_dsn():
        return False
    return True


def run_phase3_init() -> None:
    """
    Full Phase 3 database initialisation sequence.
    Called from app lifespan alongside the existing store.init_db().
    """
    logger.info("Phase 3 DB init startingâ€¦")

    if _allow_legacy_schema_bootstrap():
        create_all_tables()
        repair_shared_columns()
        apply_rls_if_postgres()
        ensure_default_organization()
        backfill_course_modules_from_courses()
    elif _use_alembic_migrations():
        logger.info("Skipping schema repair and legacy backfills; schema managed by Alembic.")
    else:
        logger.info(
            "Skipping legacy schema bootstrap in %s; run Alembic migrations for schema changes.",
            os.getenv("ENVIRONMENT", "development"),
        )

    # 6. Verify connectivity
    if verify_connection():
        logger.info("Phase 3 DB init complete â€” database healthy.")
    else:
        logger.error("Phase 3 DB init â€” database connectivity FAILED.")
