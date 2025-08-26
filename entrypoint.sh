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
    count=0
    echo "Waiting for database to be ready..."
    while ! alembic upgrade head; do
        count=$((count + 1))
        if [ ${count} -ge 30 ]; then
            echo "Failed to connect to database after 30 attempts. Exiting."
            exit 1
        fi
        echo "Migration failed, retrying in 2 seconds... (${count}/30)"
        sleep 2
    done
    echo "Database migrations completed successfully."
fi

# --- Start Uvicorn server (or run another command) ---
# If arguments are passed to the script, execute them instead of the default server.
# This allows running commands like `make shell`.
if [ "$#" -gt 0 ]; then
    exec "$@"
else
    echo "Starting server on 0.0.0.0:8000 with 1 worker(s)..."
    exec uvicorn src.main:app \
        --host "0.0.0.0" \
        --port "8000" \
        --workers "1"
fi
