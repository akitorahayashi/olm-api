#!/bin/sh

# Exit immediately if a command exits with a non-zero status ('e')
# or if an unset variable is used ('u').
set -eu

# Activate the virtual environment.
. /app/.venv/bin/activate

# --- Wait for DB and run migrations ---
# This section is skipped if the command is not the default uvicorn server
# (e.g., if a user runs 'shell' or another command).
if [ "$#" -eq 0 ] || [ "$1" = "uvicorn" ]; then
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
fi

# --- Start Uvicorn server (or run another command) ---
# Allow overriding host, port, and worker count via environment variables.
API_LISTEN_IP=${API_LISTEN_IP:-0.0.0.0}
API_PORT=${API_PORT:-8000}
UVICORN_WORKERS=${UVICORN_WORKERS:-1}

echo "Starting server on ${API_LISTEN_IP}:${API_PORT} with ${UVICORN_WORKERS} worker(s)..."

# If arguments are passed to the script, execute them instead of the default server.
# This allows running commands like `make shell`.
if [ "$#" -gt 0 ]; then
    exec "$@"
else
    exec uvicorn src.main:app \
        --host "${API_LISTEN_IP}" \
        --port "${API_PORT}" \
        --workers "${UVICORN_WORKERS}"
fi
