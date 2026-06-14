"""Create/grant the non-owner runtime database role used by the API."""

from __future__ import annotations

import os
import re

from sqlalchemy import create_engine, text


def _normalize_url(url: str) -> str:
    if url.startswith("postgresql://") or url.startswith("postgres://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


def _quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def main() -> int:
    runtime_user = os.getenv("TELITE_RUNTIME_POSTGRES_USER", "").strip()
    runtime_password = os.getenv("TELITE_RUNTIME_POSTGRES_PASSWORD", "").strip()
    migration_url = os.getenv("TELITE_MIGRATION_DATABASE_URL", "").strip()

    if not runtime_user or not runtime_password:
        print("Runtime DB role not configured; skipping role bootstrap")
        return 0
    if not migration_url:
        print("TELITE_MIGRATION_DATABASE_URL not configured; skipping role bootstrap")
        return 0
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", runtime_user):
        raise ValueError("TELITE_RUNTIME_POSTGRES_USER must be a simple PostgreSQL identifier")

    engine = create_engine(_normalize_url(migration_url), future=True)
    with engine.begin() as conn:
        role_exists = conn.execute(
            text("SELECT 1 FROM pg_roles WHERE rolname = :runtime_user"),
            {"runtime_user": runtime_user},
        ).scalar()
        quoted_role = conn.dialect.identifier_preparer.quote(runtime_user)
        quoted_db = conn.dialect.identifier_preparer.quote(conn.engine.url.database)
        quoted_password = _quote_literal(runtime_password)

        if role_exists:
            conn.execute(text(f"ALTER ROLE {quoted_role} WITH LOGIN PASSWORD {quoted_password}"))
        else:
            conn.execute(text(f"CREATE ROLE {quoted_role} LOGIN PASSWORD {quoted_password}"))
        conn.execute(text(f"ALTER ROLE {quoted_role} NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS"))
        conn.execute(text(f"GRANT CONNECT ON DATABASE {quoted_db} TO {quoted_role}"))
        conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {quoted_role}"))
        conn.execute(text(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {quoted_role}"))
        conn.execute(text(f"GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO {quoted_role}"))
        conn.execute(text(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {quoted_role}"))
        conn.execute(text(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO {quoted_role}"))

    print(f"Runtime DB role ready: {runtime_user}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
