from __future__ import annotations

import argparse
import json

from app.services.store import get_db_backend, migrate_sqlite_to_postgres


def main() -> None:
    parser = argparse.ArgumentParser(description="Copy Telite backend data from SQLite into PostgreSQL.")
    parser.add_argument(
        "--sqlite-path",
        dest="sqlite_path",
        help="Path to the source SQLite database file. Defaults to TELITE_SQLITE_SOURCE_PATH or telite_lms.db.",
    )
    parser.add_argument(
        "--keep-existing",
        action="store_true",
        help="Do not clear existing PostgreSQL rows before copying SQLite data.",
    )
    args = parser.parse_args()

    if get_db_backend() != "postgres":
        raise SystemExit(
            "PostgreSQL backend is not active. Set TELITE_DB_BACKEND=postgres or TELITE_DATABASE_URL first."
        )

    result = migrate_sqlite_to_postgres(
        source_path=args.sqlite_path,
        truncate_existing=not args.keep_existing,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
