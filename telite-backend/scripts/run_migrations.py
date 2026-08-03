"""
Container startup migration runner.

Handles:
- Fresh databases (alembic upgrade head)
- Legacy create_all databases (repair orphans, then stamp head)
- Incremental upgrades (repair orphans, then alembic upgrade head)

IMPORTANT: Migration failures MUST prevent application startup.
This is a safety requirement for production deployments.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time

from sqlalchemy import inspect, text

from app.db.engine import dispose_engine, get_engine

# Configure logging for migration process
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("telite.migrations")


def _use_migration_database_url() -> None:
    """Use migration database URL if provided."""
    migration_url = os.getenv("TELITE_MIGRATION_DATABASE_URL", "").strip()
    if not migration_url:
        return
    os.environ["TELITE_DATABASE_URL"] = migration_url
    dispose_engine()


def _repair_orphan_references() -> None:
    """Repair orphan references in existing data."""
    engine = get_engine()
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    if "categories" not in tables or "organizations" not in tables:
        return

    with engine.begin() as conn:
        result = conn.execute(
            text(
                """
                UPDATE categories
                SET organization_id = NULL
                WHERE organization_id IS NOT NULL
                  AND organization_id NOT IN (SELECT id FROM organizations)
                """
            )
        )
        repaired = result.rowcount or 0
        if repaired:
            logger.info(f"Repaired {repaired} orphan categories.organization_id value(s)")


def _verify_database_connection(max_retries: int = 5, retry_delay: int = 5) -> bool:
    """Verify database connection before running migrations."""
    for attempt in range(max_retries):
        try:
            engine = get_engine()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connection verified")
            return True
        except Exception as exc:
            if attempt < max_retries - 1:
                logger.warning(f"Database connection attempt {attempt + 1}/{max_retries} failed: {exc}. Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                logger.error(f"Database connection failed after {max_retries} attempts: {exc}")
                return False
    return False


def main() -> int:
    """Main migration runner with safety checks."""
    logger.info("Starting database migration process")
    
    # Verify database connection first
    if not _verify_database_connection():
        logger.error("CRITICAL: Database connection failed. Migration process aborted.")
        logger.error("Application will NOT start to prevent partial schema state.")
        return 1
    
    _use_migration_database_url()
    
    # Log database connection info (without sensitive data)
    db_host = os.getenv('TELITE_POSTGRES_HOST', 'NOT SET')
    db_port = os.getenv('TELITE_POSTGRES_PORT', 'NOT SET')
    db_name = os.getenv('TELITE_POSTGRES_DB', 'NOT SET')
    logger.info(f"Database: {db_host}:{db_port}/{db_name}")
    
    try:
        engine = get_engine()
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        
        logger.info(f"Current tables: {len(tables)}")

        _repair_orphan_references()

        if "alembic_version" not in tables:
            legacy_tables = {"users", "organizations", "courses"}
            if legacy_tables.issubset(tables):
                logger.warning("Legacy schema detected without Alembic history — stamping head")
                subprocess.run(["alembic", "stamp", "head"], check=True)
                logger.info("Legacy schema stamped successfully")
                return 0

            logger.info("Fresh database — running Alembic upgrade")
            subprocess.run(["alembic", "upgrade", "head"], check=True)
            logger.info("Fresh database migration completed successfully")
            return 0

        logger.info("Applying pending Alembic migrations")
        subprocess.run(["alembic", "upgrade", "head"], check=True)
        logger.info("Database migrations completed successfully")
        return 0
        
    except subprocess.CalledProcessError as exc:
        logger.error(f"CRITICAL: Migration command failed with exit code {exc.returncode}")
        logger.error("Application will NOT start to prevent partial schema state.")
        logger.error("Manual intervention required. Check migration logs and resolve issues.")
        return 1
    except Exception as exc:
        logger.error(f"CRITICAL: Unexpected error during migration: {exc}")
        logger.error("Application will NOT start to prevent partial schema state.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        if exit_code != 0:
            logger.error("Migration process failed. Deployment aborted.")
            sys.exit(exit_code)
        else:
            logger.info("Migration process completed successfully. Application can start.")
            sys.exit(0)
    except KeyboardInterrupt:
        logger.error("Migration process interrupted by user")
        sys.exit(130)
    except Exception as exc:
        logger.error(f"Fatal error in migration process: {exc}")
        sys.exit(1)
