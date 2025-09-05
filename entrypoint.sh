#!/bin/sh

# Exit immediately if a command exits with a non-zero status ('e')
# or if an unset variable is used ('u').
set -eu

# --- Wait for DB and run migrations ---
# This section is skipped if the command is not the default uvicorn server
# (e.g., if a user runs 'shell' or another command).
if [ "$#" -eq 0 ] || [ "$1" = "uvicorn" ]; then
    count=0
    echo "Waiting for database to be ready..."
    
    # Create database if it doesn't exist
    echo "Checking if database exists and creating if necessary..."
    while ! PGPASSWORD="${POSTGRES_PASSWORD}" psql -h db -U "${POSTGRES_USER}" -d postgres -c "SELECT 1 FROM pg_database WHERE datname='${POSTGRES_DB_NAME}'" | grep -q 1; do
        echo "Creating database ${POSTGRES_DB_NAME}..."
        PGPASSWORD="${POSTGRES_PASSWORD}" psql -h db -U "${POSTGRES_USER}" -d postgres -c "CREATE DATABASE \"${POSTGRES_DB_NAME}\";" || true
        sleep 1
    done
    echo "Database exists."
    
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
    WORKERS=${NUM_OF_UVICORN_WORKERS:-4}
    echo "Starting server on 0.0.0.0:8000 with ${WORKERS} worker(s)..."
    exec uvicorn src.main:app \
        --host "0.0.0.0" \
        --port "8000" \
        --workers "${WORKERS}" \
        --loop uvloop \
        --limit-concurrency 40
fi
