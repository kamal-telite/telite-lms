from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

load_dotenv(REPO_ROOT / ".env")
load_dotenv(BACKEND_ROOT / ".env", override=True)

from app.db.engine import get_platform_session  # noqa: E402


REQUIRED = {
    "media.upload",
    "media.view",
    "media.edit",
    "media.replace",
    "block.edit",
    "h5p.upload",
    "h5p.edit",
    "h5p.delete",
    "h5p.view",
}
ROLES = ("category_admin", "org_admin", "author")


def _redact(value: str | None) -> str:
    if not value:
        return "None"
    if "://" in value and "@" in value:
        prefix, rest = value.split("://", 1)
        credentials, host = rest.split("@", 1)
        user = credentials.split(":", 1)[0]
        return f"{prefix}://{user}:****@{host}"
    return value


def print_environment() -> None:
    print("Environment seen by audit_permissions.py:")
    for key in (
        "TELITE_DATABASE_URL",
        "TELITE_POSTGRES_HOST",
        "TELITE_POSTGRES_PORT",
        "TELITE_POSTGRES_DB",
        "TELITE_POSTGRES_USER",
        "POSTGRES_USER",
    ):
        print(f"  {key}={_redact(os.getenv(key))}")


def main() -> int:
    print_environment()
    try:
        with get_platform_session() as db:
            rows = db.execute(
                text(
                    """
                    SELECT role, permission_key, enabled
                    FROM role_permissions
                    WHERE role = ANY(:roles)
                    ORDER BY role, permission_key
                    """
                ),
                {"roles": list(ROLES)},
            ).fetchall()
    except SQLAlchemyError as exc:
        print("\nPermission audit could not connect to the configured database.")
        print(f"Database error: {exc.__class__.__name__}: {exc}")
        return 2

    by_role = {role: set() for role in ROLES}
    print(f"\nTotal role_permissions found: {len(rows)}")
    for row in rows:
        status = "enabled" if row.enabled else "disabled"
        print(f"{row.role} | {row.permission_key} | {status}")
        if row.enabled:
            by_role.setdefault(row.role, set()).add(row.permission_key)

    missing = {
        role: sorted(REQUIRED - permissions)
        for role, permissions in by_role.items()
        if REQUIRED - permissions
    }
    if missing:
        print("\nMissing required capabilities:")
        for role, capabilities in missing.items():
            print(f"  {role}: {', '.join(capabilities)}")
        return 1

    print("\nPASS: Required media/block/H5P capabilities are present for category_admin, org_admin, and author.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
