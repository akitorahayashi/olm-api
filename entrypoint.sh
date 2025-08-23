#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
# 'e' for exit, 'u' for unset variables, 'o pipefail' for pipe errors.
set -Eeuo pipefail

# Activate the virtual environment
# The venv is copied into the runner stage at /app/.venv
. /app/.venv/bin/activate

# --- Wait for DB and run migrations ---
max_retries=30
retry_count=0
echo "Waiting for database to be ready..."
while ! alembic upgrade head; do
    retry_count=$((retry_count + 1))
    if [ ${retry_count} -ge ${max_retries} ]; then
        echo "Failed to connect to database after ${max_retries} attempts. Exiting."
        exit 1
    fi
    echo "Migration failed, retrying in 2 seconds... (${retry_count}/${max_retries})"
    sleep 2
done
echo "Database migrations completed successfully."

# --- Start Uvicorn server ---
# Use environment variables for host and port, with sensible defaults.
UVICORN_HOST=${UVICORN_HOST:-0.0.0.0}
UVICORN_PORT=${UVICORN_PORT:-8000}

echo "Starting Uvicorn server on ${UVICORN_HOST}:${UVICORN_PORT}..."
exec uvicorn src.main:app --host "${UVICORN_HOST}" --port "${UVICORN_PORT}"
