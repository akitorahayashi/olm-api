#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Activate the virtual environment
# The venv is copied into the runner stage at /app/.venv
. /app/.venv/bin/activate

# Run database migrations
# This command ensures the database is up-to-date before starting the app.
echo "Running database migrations..."
alembic upgrade head

# Start the Uvicorn server
# The server will listen on 0.0.0.0 to be accessible from outside the container.
# The port is set to 8000, as specified in the requirements.
echo "Starting Uvicorn server..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8000
