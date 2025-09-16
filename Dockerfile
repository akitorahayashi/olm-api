# syntax=docker/dockerfile:1.7-labs
# ==============================================================================
# Stage 1: Base
# - Base stage with uv setup and dependency files
# ==============================================================================
FROM python:3.12-slim as base

WORKDIR /app

# Install uv
RUN --mount=type=cache,target=/root/.cache \
  pip install uv

# Copy dependency definition files  
COPY pyproject.toml uv.lock README.md ./


# ==============================================================================
# Stage 2: Dev Dependencies
# - Installs ALL dependencies (including development) to create a cached layer
#   that can be leveraged by CI/CD for linting, testing, etc.
# ==============================================================================
FROM base as dev-deps

# Install system dependencies required for the application
# - curl: used for debugging in the development container
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install all dependencies, including development ones
RUN --mount=type=cache,target=/root/.cache \
  uv sync


# ==============================================================================
# Stage 3: Production Dependencies
# - Creates a lean virtual environment with only production dependencies.
# ==============================================================================
FROM base as prod-deps

# Install only production dependencies
RUN --mount=type=cache,target=/root/.cache \
  uv sync --no-dev



# ==============================================================================
# Stage 4: Development
# - Development environment with all dependencies and debugging tools
# - Includes curl and other development utilities
# ==============================================================================
FROM python:3.12-slim AS development

# Install PostgreSQL client and development tools
RUN apt-get update && apt-get install -y postgresql-client curl && rm -rf /var/lib/apt/lists/*

# Create a non-root user for development
RUN groupadd -r appgroup && useradd -r -g appgroup -d /home/appuser -m appuser

WORKDIR /app
RUN chown appuser:appgroup /app

# Copy the development virtual environment from dev-deps stage
COPY --from=dev-deps /app/.venv ./.venv

# Set the PATH to include the venv's bin directory
ENV PATH="/app/.venv/bin:${PATH}"

# Copy application code
COPY --chown=appuser:appgroup src/ ./src
COPY --chown=appuser:appgroup sdk/ ./sdk
COPY --chown=appuser:appgroup alembic/ ./alembic
COPY --chown=appuser:appgroup pyproject.toml .
COPY --chown=appuser:appgroup entrypoint.sh .

RUN chmod +x entrypoint.sh

# Switch to non-root user
USER appuser

EXPOSE 8000

# Development healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import sys, urllib.request; sys.exit(0) if urllib.request.urlopen('http://localhost:8000/health').getcode() == 200 else sys.exit(1)"

ENTRYPOINT ["/app/entrypoint.sh"]



# ==============================================================================
# Stage 5: Production
# - Creates the final, lightweight production image.
# - Copies the lean venv and only necessary application files.
# ==============================================================================
FROM python:3.12-slim AS production

# Install PostgreSQL client for database operations
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*



# Create a non-root user and group for security
RUN groupadd -r appgroup && useradd -r -g appgroup -d /home/appuser -m appuser

# Set the working directory
WORKDIR /app

# Grant ownership of the working directory to the non-root user
RUN chown appuser:appgroup /app

# Copy the lean virtual environment from the prod-deps stage
COPY --from=prod-deps /app/.venv ./.venv

# Set the PATH to include the venv's bin directory for simpler command execution
ENV PATH="/app/.venv/bin:${PATH}"

# Copy only the necessary application code and configuration, excluding tests
COPY --chown=appuser:appgroup src/ ./src
COPY --chown=appuser:appgroup sdk/ ./sdk
COPY --chown=appuser:appgroup alembic/ ./alembic
COPY --chown=appuser:appgroup pyproject.toml .
COPY --chown=appuser:appgroup entrypoint.sh .

# Grant execute permissions to the entrypoint script
RUN chmod +x entrypoint.sh

# Switch to the non-root user
USER appuser

# Expose the port the app runs on (will be mapped by Docker Compose)
EXPOSE 8000

# Healthcheck using only Python's standard library to avoid extra dependencies
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import sys, urllib.request; sys.exit(0) if urllib.request.urlopen('http://localhost:8000/health').getcode() == 200 else sys.exit(1)"

# Set the entrypoint script to be executed when the container starts
ENTRYPOINT ["/app/entrypoint.sh"]
