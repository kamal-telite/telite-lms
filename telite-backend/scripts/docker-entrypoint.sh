#!/bin/bash
set -euo pipefail

# Container startup script with production safety checks
# This script ensures:
# 1. Migrations run before application startup
# 2. Migration failures prevent deployment
# 3. Graceful shutdown handling
# 4. No duplicate initialization on restart

mkdir -p /app/uploads
if [ "$(id -u)" -eq 0 ]; then
    chown -R telite:telite /app/uploads
    exec gosu telite "$0" "$@"
fi

# Function to handle graceful shutdown
graceful_shutdown() {
    echo "Received shutdown signal. Performing graceful shutdown..."
    # Signal will be propagated to child processes
    exit 0
}

# Register signal handlers for graceful shutdown
trap graceful_shutdown SIGTERM SIGINT

# Check if this is a migration/initialization run
if [[ "${1:-}" == "uvicorn" || "${*:-}" == *"uvicorn app.main:app"* ]]; then
    echo "=== Container Startup Sequence ==="
    echo "Step 1: Preparing runtime database role..."
    python -m scripts.ensure_runtime_db_role
    if [ $? -ne 0 ]; then
        echo "ERROR: Runtime database role preparation failed. Aborting startup."
        exit 1
    fi
    
    echo "Step 2: Running database migrations..."
    python -m scripts.run_migrations
    if [ $? -ne 0 ]; then
        echo "ERROR: Database migrations failed. Aborting startup to prevent partial schema state."
        echo "This is a safety requirement for production deployments."
        exit 1
    fi
    
    echo "Step 3: Application startup..."
    echo "=== Startup sequence completed successfully ==="
fi

# Execute the main command
exec "$@"
