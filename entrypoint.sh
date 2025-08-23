#!/bin/sh

# Exit immediately if a command exits with a non-zero status ('e')
# or if an unset variable is used ('u').
set -eu

# Activate the virtual environment.
# This is sourced to make `alembic` and `uvicorn` available in the PATH.
. /app/.venv/bin/activate

# --- Wait for DB and run migrations ---
# Allow overriding retry count and sleep duration via environment variables.
RETRIES=${RETRIES:-30}
SLEEP_SECONDS=${SLEEP_SECONDS:-2}
count=0
echo "Waiting for database to be ready..."
while ! alembic upgrade head; do
    count=$((count + 1))
    if [ ${count} -ge ${RETRIES} ]; then
        echo "Failed to connect to database after ${RETRIES} attempts. Exiting."
        exit 1
    fi
    echo "Migration failed, retrying in ${SLEEP_SECONDS} seconds... (${count}/${RETRIES})"
    sleep ${SLEEP_SECONDS}
done
echo "Database migrations completed successfully."

# --- Start Uvicorn server ---
# Allow overriding host, port, and worker count via environment variables.
UVICORN_HOST=${UVICORN_HOST:-0.0.0.0}
UVICORN_PORT=${UVICORN_PORT:-8000}
UVICORN_WORKERS=${UVICORN_WORKERS:-1}

echo "Starting Uvicorn server on ${UVICORN_HOST}:${UVICORN_PORT} with ${UVICORN_WORKERS} worker(s)..."
exec uvicorn src.main:app \
    --host "${UVICORN_HOST}" \
    --port "${UVICORN_PORT}" \
    --workers "${UVICORN_WORKERS}"
