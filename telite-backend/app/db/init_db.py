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
import json
import os

from sqlalchemy import Boolean, Float, Integer, inspect, text
from sqlalchemy.sql.sqltypes import BigInteger, Numeric, String, Text

from app.db.engine import get_db_session, get_engine
from app.models.base import Base

logger = logging.getLogger("telite.db.init")


def create_all_tables() -> None:
    """Create all ORM-mapped tables that don't exist yet."""
    engine = get_engine()
    Base.metadata.create_all(engine, checkfirst=True)
    logger.info("SQLAlchemy tables verified/created.")


def repair_shared_columns() -> None:
    """Add shared ORM mixin columns that may be missing on older tables."""
    engine = get_engine()
    inspector = inspect(engine)
    preparer = engine.dialect.identifier_preparer

    def default_for_column(column) -> str:
        if column.nullable:
            return ""
        if isinstance(column.type, (Integer, BigInteger, Float, Numeric)):
            return " DEFAULT 0"
        if isinstance(column.type, Boolean):
            return " DEFAULT FALSE"
        if isinstance(column.type, (String, Text)):
            return " DEFAULT ''"
        return ""

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
                existing_columns.add("org_id")

            for column in table.c:
                if column.name in existing_columns:
                    continue
                if column.primary_key:
                    continue
                column_type = column.type.compile(dialect=engine.dialect)
                nullable = "" if column.nullable else " NOT NULL"
                default = default_for_column(column)
                connection.execute(
                    text(f"ALTER TABLE {quoted_table} ADD COLUMN {preparer.quote(column.name)} {column_type}{nullable}{default}")
                )
                logger.info("Added missing %s column to %s.", column.name, table.name)


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
    except Exception as exc:
        logger.error("Database connectivity check failed: %s", exc)
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
                    'active', 'free', NOW()
                )
                """
            )
        )
        logger.info("Created missing default organization with id=1.")


def run_phase3_init() -> None:
    """
    Full Phase 3 database initialisation sequence.
    Called from app lifespan alongside the existing store.init_db().
    """
    logger.info("Phase 3 DB init starting…")

    # 1. Create new ORM tables
    create_all_tables()

    # 2. Repair older tables that predate shared ORM mixins
    repair_shared_columns()

    # 3. Apply RLS (PostgreSQL only)
    apply_rls_if_postgres()

    # 4. Ensure legacy seed rows have their parent organization
    ensure_default_organization()

    # 5. Backfill native course modules for existing seed databases
    backfill_course_modules_from_courses()

    # 6. Verify connectivity
    if verify_connection():
        logger.info("Phase 3 DB init complete — database healthy.")
    else:
        logger.error("Phase 3 DB init — database connectivity FAILED.")
