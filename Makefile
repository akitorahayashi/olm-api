# ==============================================================================
# Makefile for Project Automation
#
# Provides a unified interface for common development tasks, abstracting away
# the underlying Docker Compose commands for a better Developer Experience (DX).
#
# Inspired by the self-documenting Makefile pattern.
# See: https://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
# ==============================================================================

# Default target executed when 'make' is run without arguments
.DEFAULT_GOAL := help

# ==============================================================================
# Sudo Configuration
#
# Allows running Docker commands with sudo when needed (e.g., in CI environments).
# Usage: make up SUDO=true
# ==============================================================================
SUDO_PREFIX :=
ifeq ($(SUDO),true)
	SUDO_PREFIX := sudo
endif

DOCKER_CMD := $(SUDO_PREFIX) docker

# Define the project name based on the directory name for dynamic container naming
PROJECT_NAME := $(shell basename $(CURDIR))

# Define project names for different environments
DEV_PROJECT_NAME := $(PROJECT_NAME)-dev
PROD_PROJECT_NAME := $(PROJECT_NAME)-prod
TEST_PROJECT_NAME := $(PROJECT_NAME)-test

# ==============================================================================
# HELP
# ==============================================================================

.PHONY: help
help: ## Show this help message
	@echo "Usage: make [target] [VAR=value]"
	@echo "Options:"
	@echo "  \033[36m%-15s\033[0m %s" "SUDO=true" "Run docker commands with sudo (e.g., make up SUDO=true)"
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ==============================================================================
# Environment Setup
# ==============================================================================

.PHONY: setup
setup: ## Initialize project: install dependencies, create .env file and pull required Docker images.
	@echo "Installing python dependencies with Poetry..."
	@poetry install --no-root
	@echo "Creating environment file..."
	@if [ ! -f .env ]; then \
		echo "Creating .env from .env.example..." ; \
		cp .env.example .env; \
	else \
		echo ".env already exists. Skipping creation."; \
	fi
	@echo "✅ Environment file created (.env)"
	@echo "💡 You can customize .env for your specific needs:"
	@echo "   📝 Change OLLAMA_HOST to switch between container/host Ollama"
	@echo "   📝 Adjust other settings as needed"
	@echo ""
	@echo "Pulling PostgreSQL image for tests..."
	$(DOCKER_CMD) pull postgres:16-alpine

# ==============================================================================
# Development Environment Commands
# ==============================================================================

.PHONY: up
up: ## Start all development containers in detached mode
	@echo "Starting up development services..."
	$(DOCKER_CMD) compose -f docker-compose.yml -f docker-compose.dev.override.yml --project-name $(DEV_PROJECT_NAME) up -d

.PHONY: down
down: ## Stop and remove all development containers
	@echo "Shutting down development services..."
	$(DOCKER_CMD) compose -f docker-compose.yml -f docker-compose.dev.override.yml --project-name $(DEV_PROJECT_NAME) down --remove-orphans

.PHONY: rebuild
rebuild: ## Rebuild the api service without cache and restart it
	@echo "Rebuilding api service with --no-cache..."
	$(DOCKER_CMD) compose -f docker-compose.yml -f docker-compose.dev.override.yml --project-name $(DEV_PROJECT_NAME) build --no-cache api
	$(DOCKER_CMD) compose -f docker-compose.yml -f docker-compose.dev.override.yml --project-name $(DEV_PROJECT_NAME) up -d api

.PHONY: up-prod
up-prod: ## Start all production-like containers
	@echo "Starting up production-like services..."
	$(DOCKER_CMD) compose -f docker-compose.yml --project-name $(PROD_PROJECT_NAME) up -d --build --pull always --remove-orphans

.PHONY: down-prod
down-prod: ## Stop and remove all production-like containers
	@echo "Shutting down production-like services..."
	$(DOCKER_CMD) compose -f docker-compose.yml --project-name $(PROD_PROJECT_NAME) down --remove-orphans

.PHONY: logs
logs: ## View the logs for the development API service
	@echo "Following logs for the dev api service..."
	$(DOCKER_CMD) compose -f docker-compose.yml -f docker-compose.dev.override.yml --project-name $(DEV_PROJECT_NAME) logs -f api

.PHONY: shell
shell: ## Open a shell inside the running development API container
	@echo "Opening shell in dev api container..."
	@$(DOCKER_CMD) compose -f docker-compose.yml -f docker-compose.dev.override.yml --project-name $(DEV_PROJECT_NAME) exec api /bin/sh || \
		(echo "Failed to open shell. Is the container running? Try 'make up'" && exit 1)

.PHONY: migrate
migrate: ## Run database migrations against the development database
	@echo "Running database migrations for dev environment..."
	$(DOCKER_CMD) compose -f docker-compose.yml -f docker-compose.dev.override.yml --project-name $(DEV_PROJECT_NAME) exec api sh -c ". /app/.venv/bin/activate && alembic upgrade head"

# ==============================================================================
# CODE QUALITY 
# ==============================================================================

.PHONY: format
format: ## Format code with black and ruff --fix
	@echo "Formatting code with black and ruff..."
	poetry run black .
	poetry run ruff check . --fix

.PHONY: lint
lint: ## Lint code with black check and ruff
	@echo "Linting code with black check and ruff..."
	poetry run black --check .
	poetry run ruff check .

# ==============================================================================
# TESTING
# ==============================================================================

.PHONY: test
test: unit-test build-test db-test e2e-test## Run the full test suite

.PHONY: unit-test
unit-test: ## Run the fast, database-independent unit tests locally
	@echo "Running unit tests..."
	@poetry run python -m pytest tests/unit -s

.PHONY: db-test
db-test: ## Run the slower, database-dependent tests locally
	@echo "Running database tests..."
	@poetry run python -m pytest tests/db -s

.PHONY: e2e-test
e2e-test: ## Run end-to-end tests against a live application stack
	@echo "Running end-to-end tests..."
	@poetry run python -m pytest tests/e2e -s

.PHONY: perf-test
perf-test: ## Run performance tests with concurrent request measurements
	@echo "Running performance tests..."
	@poetry run python -m pytest tests/perf -s

.PHONY: build-test
build-test: ## Build Docker image for testing without leaving artifacts
	@echo "Building Docker image for testing (clean build)..."
	@TEMP_IMAGE_TAG=$$(date +%s)-build-test; \
	$(DOCKER_CMD) build --target runner --tag temp-build-test:$$TEMP_IMAGE_TAG . && \
	echo "Build successful. Cleaning up temporary image..." && \
	$(DOCKER_CMD) rmi temp-build-test:$$TEMP_IMAGE_TAG || true
