# ==============================================================================
# justfile for OLM API Project Automation
# ==============================================================================

PROJECT_NAME := env("PROJECT_NAME", "olm-api")
POSTGRES_IMAGE := env("POSTGRES_IMAGE", "postgres:16-alpine")

DEV_PROJECT_NAME := PROJECT_NAME + "-dev"
PROD_PROJECT_NAME := PROJECT_NAME + "-prod"
TEST_PROJECT_NAME := PROJECT_NAME + "-test"

DEV_COMPOSE  := "docker compose -f docker-compose.yml -f docker-compose.dev.override.yml --project-name " + DEV_PROJECT_NAME
PROD_COMPOSE := "docker compose -f docker-compose.yml --project-name " + PROD_PROJECT_NAME
TEST_COMPOSE := "docker compose -f docker-compose.yml -f docker-compose.test.override.yml --project-name " + TEST_PROJECT_NAME

# Show available recipes
help:
    @echo "Usage: just [recipe]"
    @echo "Available recipes:"
    @just --list | tail -n +2 | awk '{printf "  \033[36m%-20s\033[0m %s\n", $1, substr($0, index($0, $2))}'

default: help

# ==============================================================================
# Environment Setup
# ==============================================================================

# Initialize project: install dependencies, create .env file and pull required Docker images
setup:
    @echo "Installing python dependencies with uv..."
    @uv sync
    @echo "Creating environment file..."
    @if [ ! -f .env ] && [ -f .env.example ]; then \
        echo "Creating .env from .env.example..."; \
        cp .env.example .env; \
        echo "✅ Environment file created (.env)"; \
    else \
        echo ".env already exists. Skipping creation."; \
    fi
    @echo "💡 You can customize .env for your specific needs:"
    @echo "   📝 Change OLLAMA_HOST to switch between container/host Ollama"
    @echo "   📝 Adjust other settings as needed"
    @echo ""
    @echo "Pulling PostgreSQL image for tests..."
    docker pull {{POSTGRES_IMAGE}}
    @echo "✅ Setup complete. Dependencies are installed and .env file is ready."

# ==============================================================================
# Development Environment Commands
# ==============================================================================

# Start all development containers in detached mode
up:
    @echo "Starting up development services..."
    @{{DEV_COMPOSE}} up -d

# Stop and remove all development containers
down:
    @echo "Shutting down development services..."
    @{{DEV_COMPOSE}} down --remove-orphans

# Start all production-like containers
up-prod:
    @echo "Starting up production-like services..."
    @{{PROD_COMPOSE}} up -d --build --pull always --remove-orphans

# Stop and remove all production-like containers
down-prod:
    @echo "Shutting down production-like services..."
    @{{PROD_COMPOSE}} down --remove-orphans

# Rebuild and restart API container only
rebuild:
    @echo "Rebuilding and restarting API service..."
    @{{DEV_COMPOSE}} down --remove-orphans
    @{{DEV_COMPOSE}} build --no-cache api
    @{{DEV_COMPOSE}} up -d

# ==============================================================================
# CODE QUALITY
# ==============================================================================

# Format code with black and ruff --fix
format:
    @echo "Formatting code with black and ruff..."
    @uv run black .
    @uv run ruff check . --fix

# Lint code with black check and ruff
lint:
    @echo "Linting code with black check and ruff..."
    @uv run black --check .
    @uv run ruff check .

# ==============================================================================
# TESTING
# ==============================================================================

# Run the full test suite
test: unit-test sdk-test build-test db-test e2e-test

# Run the unit tests locally
unit-test:
    @echo "Running unit tests..."
    @uv run pytest tests/unit -s

# Run SDK tests locally
sdk-test:
    @echo "Running SDK tests..."
    @uv run pytest tests/sdk -s

# Run database tests locally
db-test:
    @echo "Running database tests..."
    @uv run pytest tests/db -s

# Run end-to-end tests against a live application stack
e2e-test:
    @echo "Running end-to-end tests..."
    @uv run pytest tests/e2e -s

# Run all performance tests (both parallel and sequential)
perf-test:
    @echo "Running all performance tests..."
    @uv run pytest tests/perf -s

# Run only the batch parallel performance test
perf-test-parallel:
    @echo "Running batch parallel performance test..."
    @uv run pytest tests/perf/test_batch_parallel.py -s

# Run only the batch sequential performance test
perf-test-sequential:
    @echo "Running batch sequential performance test..."
    @uv run pytest tests/perf/test_batch_sequential.py -s

# Build Docker image for testing without leaving artifacts
build-test:
    @echo "Building Docker image for testing (clean build)..."
    @TEMP_IMAGE_TAG=$(date +%s)-build-test; \
    docker build --target production --tag temp-build-test:$TEMP_IMAGE_TAG . && \
    echo "Build successful. Cleaning up temporary image..." && \
    docker rmi temp-build-test:$TEMP_IMAGE_TAG || true

# ==============================================================================
# CLEANUP
# ==============================================================================

# Remove __pycache__ and .venv to make project lightweight
clean:
    @echo "🧹 Cleaning up project..."
    @find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    @rm -rf .venv
    @rm -rf .pytest_cache
    @rm -rf .ruff_cache
    @echo "✅ Cleanup completed"