# ==============================================================================
# Stage 1: Builder
# - Installs dependencies into a virtual environment.
# ==============================================================================
FROM python:3.12-slim as builder

# Argument for pinning the Poetry version
ARG POETRY_VERSION=1.8.2

# Set environment variables for Poetry
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app

# Install Poetry
RUN pip install "poetry==${POETRY_VERSION}"

# Copy dependency definition files
COPY pyproject.toml poetry.lock ./

# Install dependencies, excluding development ones and not installing the project itself
RUN poetry install --no-root --no-dev


# ==============================================================================
# Stage 2: Runner
# - Creates a non-root user.
# - Copies dependencies and source code.
# - Sets up the entrypoint and healthcheck.
# ==============================================================================
FROM python:3.12-slim

# Create a non-root user and group
RUN groupadd -r appgroup && useradd -r -g appgroup -d /home/appuser -m appuser

# Set the working directory
WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /app/.venv ./.venv

# Set the PATH to include the venv's bin directory
ENV PATH="/app/.venv/bin:${PATH}"

# Copy application code and necessary files
COPY --chown=appuser:appgroup src/ ./src
COPY --chown=appuser:appgroup alembic/ ./alembic
COPY --chown=appuser:appgroup alembic.ini .
COPY --chown=appuser:appgroup entrypoint.sh .

# Grant execute permissions to the entrypoint script
RUN chmod +x entrypoint.sh

# Switch to the non-root user
USER appuser

# Expose the port the app runs on
EXPOSE 8000

# Healthcheck to ensure the application is responsive
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD [ "wget", "--quiet", "--tries=1", "--spider", "http://localhost:8000/health" ]

# Set the entrypoint script to be executed when the container starts
ENTRYPOINT ["/app/entrypoint.sh"]
