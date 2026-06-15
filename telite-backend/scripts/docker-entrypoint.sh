#!/bin/bash
set -euo pipefail

mkdir -p /app/uploads
if [ "$(id -u)" -eq 0 ]; then
    chown -R telite:telite /app/uploads
    exec gosu telite "$0" "$@"
fi

if [[ "${1:-}" == "uvicorn" || "${*:-}" == *"uvicorn app.main:app"* ]]; then
    echo "Preparing runtime database role..."
    python -m scripts.ensure_runtime_db_role
    echo "Preparing database schema..."
    python -m scripts.run_migrations
fi

exec "$@"
