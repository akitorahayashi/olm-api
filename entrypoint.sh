#!/bin/sh

# Exit immediately if a command exits with a non-zero status ('e')
# or if an unset variable is used ('u').
set -eu

# --- Run migrations ---
# This section is skipped if the command is not the default uvicorn server
# (e.g., if a user runs 'shell' or another command).
if [ "$#" -eq 0 ] || [ "$1" = "uvicorn" ]; then
    count=0
    echo "Running database migrations..."

    while ! alembic upgrade head; do
        count=$((count + 1))
        if [ ${count} -ge 10 ]; then
            echo "Failed to run migrations after 10 attempts. Exiting."
            exit 1
        fi
        echo "Migration failed, retrying in 1 second... (${count}/10)"
        sleep 1
    done
    echo "Database migrations completed successfully."
fi

# --- Start Uvicorn server (or run another command) ---
# If arguments are passed to the script, execute them instead of the default server.
# This allows running commands like `make shell`.
if [ "$#" -gt 0 ]; then
    exec "$@"
else
    WORKERS=${NUM_OF_UVICORN_WORKERS:-4}
    echo "Starting server on 0.0.0.0:8000 with ${WORKERS} worker(s)..."
    exec uvicorn src.main:app \
        --host "0.0.0.0" \
        --port "8000" \
        --workers "${WORKERS}" \
        --loop uvloop \
        --limit-concurrency 40
fi
