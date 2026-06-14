"""
Container startup migration runner.

Handles:
- Fresh databases (alembic upgrade head)
- Legacy create_all databases (repair orphans, then stamp head)
- Incremental upgrades (repair orphans, then alembic upgrade head)
"""

from __future__ import annotations

import os
import subprocess
import sys

from sqlalchemy import inspect, text

from app.db.engine import dispose_engine, get_engine


def _use_migration_database_url() -> None:
    migration_url = os.getenv("TELITE_MIGRATION_DATABASE_URL", "").strip()
    if not migration_url:
        return
    os.environ["TELITE_DATABASE_URL"] = migration_url
    dispose_engine()


def _repair_orphan_references() -> None:
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
            print(f"Repaired {repaired} orphan categories.organization_id value(s)")


def main() -> int:
    _use_migration_database_url()
    engine = get_engine()
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    _repair_orphan_references()

    if "alembic_version" not in tables:
        legacy_tables = {"users", "organizations", "courses"}
        if legacy_tables.issubset(tables):
            print("Legacy schema detected without Alembic history — stamping head")
            subprocess.run(["alembic", "stamp", "head"], check=True)
            return 0

        print("Fresh database — running Alembic upgrade")
        subprocess.run(["alembic", "upgrade", "head"], check=True)
        return 0

    print("Applying pending Alembic migrations")
    subprocess.run(["alembic", "upgrade", "head"], check=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"Migration command failed with exit code {exc.returncode}", file=sys.stderr)
        raise
