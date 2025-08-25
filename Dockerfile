# syntax=docker/dockerfile:1.7-labs
# ==============================================================================
# Stage 1: Builder
# - Installs ALL dependencies (including development) to create a cached layer
#   that can be leveraged by CI/CD for linting, testing, etc.
# ==============================================================================
FROM python:3.12-slim as builder

# Argument for pinning the Poetry version
ARG POETRY_VERSION=2.1.4

# Set environment variables for Poetry
ENV POETRY_NO_INTERACTION=1 \
  POETRY_VIRTUALENVS_IN_PROJECT=true \
  POETRY_CACHE_DIR=/tmp/poetry_cache \
  PATH="/root/.local/bin:${PATH}"

WORKDIR /app

# Install system dependencies required for the application
# - curl: used for debugging in the development container
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*



# Install Poetry
RUN --mount=type=cache,target=/root/.cache \
  pip install pipx && \
  pipx ensurepath && \
  pipx install "poetry==${POETRY_VERSION}"

# Copy dependency definition files
COPY pyproject.toml poetry.lock ./ 

# Install all dependencies, including development ones
RUN --mount=type=cache,target=/tmp/poetry_cache \
  poetry config virtualenvs.in-project true && \
  poetry install --no-root



# ==============================================================================
# Stage 2: Prod-Builder
# - Creates a lean virtual environment with only production dependencies.
# ==============================================================================
FROM python:3.12-slim as prod-builder

# Argument for pinning the Poetry version
ARG POETRY_VERSION=2.1.4

# Set environment variables for Poetry
ENV POETRY_NO_INTERACTION=1 \
  POETRY_VIRTUALENVS_IN_PROJECT=true \
  POETRY_CACHE_DIR=/tmp/poetry_cache \
  PATH="/root/.local/bin:${PATH}"

WORKDIR /app

# Install Poetry
RUN --mount=type=cache,target=/root/.cache \
  pip install pipx && \
  pipx ensurepath && \
  pipx install "poetry==${POETRY_VERSION}"

# Copy dependency definition files
COPY pyproject.toml poetry.lock ./

# Install only production dependencies
RUN --mount=type=cache,target=/tmp/poetry_cache \
  poetry config virtualenvs.in-project true && \
  poetry install --no-root --only main



# ==============================================================================
# Stage 3: Runner
# - Creates the final, lightweight production image.
# - Copies the lean venv and only necessary application files.
# ==============================================================================
FROM python:3.12-slim AS runner



# Create a non-root user and group for security
RUN groupadd -r appgroup && useradd -r -g appgroup -d /home/appuser -m appuser

# Set the working directory
WORKDIR /app

# Grant ownership of the working directory to the non-root user
RUN chown appuser:appgroup /app

# Copy the lean virtual environment from the prod-builder stage
COPY --from=prod-builder /app/.venv ./.venv

# Set the PATH to include the venv's bin directory for simpler command execution
ENV PATH="/app/.venv/bin:${PATH}"

# Copy only the necessary application code and configuration, excluding tests
COPY --chown=appuser:appgroup src/ ./src
COPY --chown=appuser:appgroup alembic/ ./alembic
COPY --chown=appuser:appgroup pyproject.toml .
COPY --chown=appuser:appgroup entrypoint.sh .

# Grant execute permissions to the entrypoint script
RUN chmod +x entrypoint.sh

# Switch to the non-root user
USER appuser

# Expose the port the app runs on (will be mapped by Docker Compose)
EXPOSE 8000

# Default healthcheck path
ENV HEALTHCHECK_PATH=/health

# Healthcheck using only Python's standard library to avoid extra dependencies
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import sys, os, urllib.request; sys.exit(0) if urllib.request.urlopen(f'http://localhost:8000{os.environ.get(\"HEALTHCHECK_PATH\")}').getcode() == 200 else sys.exit(1)"

# Set the entrypoint script to be executed when the container starts
ENTRYPOINT ["/app/entrypoint.sh"]
