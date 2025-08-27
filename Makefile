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
setup: ## Initialize project: install dependencies, create .env files and pull required Docker images.
	@echo "Installing python dependencies with Poetry..."
	@poetry install --no-root
	@echo "Creating environment files..."
	@if [ ! -f .env.example ]; then echo ".env.example not found!"; exit 1; fi
	@POSTGRES_DB_NAME=$$(grep POSTGRES_DB_NAME .env.example | cut -d '=' -f2); \
	for env in dev prod test; do \
		if [ ! -f .env.$${env} ]; then \
			echo "Creating .env.$${env}..." ; \
			cp .env.example .env.$${env}; \
			echo "\n# --- Dynamic settings ---" >> .env.$${env}; \
			echo "POSTGRES_DB=$${POSTGRES_DB_NAME}-$${env}" >> .env.$${env}; \
		else \
			echo ".env.$${env} already exists. Skipping creation."; \
		fi; \
	done
	@echo "Pulling PostgreSQL image for tests..."
	$(DOCKER_CMD) pull postgres:16-alpine

# ==============================================================================
# Development Environment Commands
# ==============================================================================

.PHONY: up
up: ## Start all development containers in detached mode
	@echo "Starting up development services..."
	@ln -sf .env.dev .env
	$(DOCKER_CMD) compose -f docker-compose.yml -f docker-compose.override.yml --project-name $(DEV_PROJECT_NAME) up -d

.PHONY: down
down: ## Stop and remove all development containers
	@echo "Shutting down development services..."
	@ln -sf .env.dev .env
	$(DOCKER_CMD) compose -f docker-compose.yml -f docker-compose.override.yml --project-name $(DEV_PROJECT_NAME) down --remove-orphans

.PHONY: clean
clean: ## Stop and remove all dev containers, networks, and volumes (use with CONFIRM=1)
	@if [ "$(CONFIRM)" != "1" ]; then echo "This is a destructive operation. Please run 'make clean CONFIRM=1' to confirm."; exit 1; fi
	@echo "Cleaning up all development Docker resources (including volumes)..."
	@ln -sf .env.dev .env
	$(DOCKER_CMD) compose -f docker-compose.yml -f docker-compose.override.yml --project-name $(DEV_PROJECT_NAME) down --volumes --remove-orphans

.PHONY: rebuild
rebuild: ## Rebuild the api service without cache and restart it
	@echo "Rebuilding api service with --no-cache..."
	@ln -sf .env.dev .env
	$(DOCKER_CMD) compose -f docker-compose.yml -f docker-compose.override.yml --project-name $(DEV_PROJECT_NAME) build --no-cache api
	$(DOCKER_CMD) compose -f docker-compose.yml -f docker-compose.override.yml --project-name $(DEV_PROJECT_NAME) up -d api

.PHONY: up-prod
up-prod: ## Start all production-like containers
	@echo "Starting up production-like services..."
	@ln -sf .env.prod .env
	$(DOCKER_CMD) compose -f docker-compose.yml --project-name $(PROD_PROJECT_NAME) up -d --build --pull always --remove-orphans

.PHONY: down-prod
down-prod: ## Stop and remove all production-like containers
	@echo "Shutting down production-like services..."
	@ln -sf .env.prod .env
	$(DOCKER_CMD) compose -f docker-compose.yml --project-name $(PROD_PROJECT_NAME) down --remove-orphans

.PHONY: logs
logs: ## View the logs for the development API service
	@echo "Following logs for the dev api service..."
	@ln -sf .env.dev .env
	$(DOCKER_CMD) compose -f docker-compose.yml -f docker-compose.override.yml --project-name $(DEV_PROJECT_NAME) logs -f api

.PHONY: shell
shell: ## Open a shell inside the running development API container
	@echo "Opening shell in dev api container..."
	@ln -sf .env.dev .env
	@$(DOCKER_CMD) compose -f docker-compose.yml -f docker-compose.override.yml --project-name $(DEV_PROJECT_NAME) exec api /bin/sh || \
		(echo "Failed to open shell. Is the container running? Try 'make up'" && exit 1)

.PHONY: migrate
migrate: ## Run database migrations against the development database
	@echo "Running database migrations for dev environment..."
	@ln -sf .env.dev .env
	$(DOCKER_CMD) compose -f docker-compose.yml -f docker-compose.override.yml --project-name $(DEV_PROJECT_NAME) exec api sh -c ". /app/.venv/bin/activate && alembic upgrade head"

# ==============================================================================
# CODE QUALITY & TESTING
# ==============================================================================

.PHONY: format
format: ## Format the code using Black
	@echo "Formatting code with Black..."
	poetry run black src/ tests/

.PHONY: format-check
format-check: ## Check if the code is formatted with Black
	@echo "Checking code format with Black..."
	poetry run black --check src/ tests/

.PHONY: lint
lint: ## Lint and fix the code with Ruff automatically
	@echo "Linting and fixing code with Ruff..."
	poetry run ruff check src/ tests/ --fix

.PHONY: lint-check
lint-check: ## Check the code for issues with Ruff
	@echo "Checking code with Ruff..."
	poetry run ruff check src/ tests/

.PHONY: unit-test
unit-test: ## Run the fast, database-independent unit tests locally
	@echo "Running unit tests..."
	@poetry run python -m pytest tests/unit

.PHONY: db-test
db-test: ## Run the slower, database-dependent tests locally
	@echo "Running database tests..."
	@poetry run python -m pytest tests/db

.PHONY: e2e-test
e2e-test: ## Run end-to-end tests against a live application stack
	@echo "Running end-to-end tests..."
	@ln -sf .env.test .env
	@poetry run python -m pytest tests/e2e

.PHONY: test
test: unit-test db-test e2e-test ## Run the full test suite