# Stage 1: Builder - Install dependencies with Poetry
FROM python:3.12-slim as builder

# Set environment variables to prevent Poetry from creating a virtual env in the project directory
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app

# Install Poetry
RUN pip install poetry

# Copy dependency definition files
COPY pyproject.toml poetry.lock ./

# Install dependencies, excluding development ones.
# --no-root is used because we will copy the source code in the next stage.
RUN poetry install --no-root --no-dev


# Stage 2: Runner - The final, lean image
FROM python:3.12-slim

WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /app/.venv ./.venv

# Copy the application source code
COPY src/ ./src
COPY alembic/ ./alembic
COPY alembic.ini .
COPY entrypoint.sh .

# Expose the port the app runs on
EXPOSE 8000

# Set the entrypoint script to be executed when the container starts
ENTRYPOINT ["./entrypoint.sh"]
