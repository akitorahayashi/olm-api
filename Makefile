# ==============================================================================
# Makefile for Project Automation
#
# Provides a unified interface for common development tasks, abstracting away
# the underlying Docker Compose commands for a better Developer Experience (DX).
#
# Inspired by the self-documenting Makefile pattern.
# See: https://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
# ==============================================================================

# Ensure that the targets are always run
.PHONY: help setup up down logs shell format format-check lint lint-check test migrate clean rebuild

# Default target executed when 'make' is run without arguments
.DEFAULT_GOAL := help

# Define the project name based on the directory name for dynamic container naming
PROJECT_NAME := $(shell basename $(CURDIR))

# Define project names for different environments
DEV_PROJECT_NAME := $(PROJECT_NAME)-dev
PROD_PROJECT_NAME := $(PROJECT_NAME)-prod
TEST_PROJECT_NAME := $(PROJECT_NAME)-test

# ==============================================================================
# HELP
# ==============================================================================

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ==============================================================================
# PROJECT SETUP & ENVIRONMENT
# ==============================================================================

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
	docker pull postgres:16-alpine

up: ## Start all development containers in detached mode
	@echo "Starting up development services..."
	@ln -sf .env.dev .env
	docker compose -f docker-compose.yml -f docker-compose.override.yml --project-name $(DEV_PROJECT_NAME) up -d

down: ## Stop and remove all development containers
	@echo "Shutting down development services..."
	@ln -sf .env.dev .env
	docker compose -f docker-compose.yml -f docker-compose.override.yml --project-name $(DEV_PROJECT_NAME) down --remove-orphans

clean: ## Stop and remove all dev containers, networks, and volumes (use with CONFIRM=1)
	@if [ "$(CONFIRM)" != "1" ]; then echo "This is a destructive operation. Please run 'make clean CONFIRM=1' to confirm."; exit 1; fi
	@echo "Cleaning up all development Docker resources (including volumes)..."
	@ln -sf .env.dev .env
	docker compose -f docker-compose.yml -f docker-compose.override.yml --project-name $(DEV_PROJECT_NAME) down --volumes --remove-orphans

rebuild: ## Rebuild the api service without cache and restart it
	@echo "Rebuilding api service with --no-cache..."
	@ln -sf .env.dev .env
	docker compose -f docker-compose.yml -f docker-compose.override.yml --project-name $(DEV_PROJECT_NAME) build --no-cache api
	docker compose -f docker-compose.yml -f docker-compose.override.yml --project-name $(DEV_PROJECT_NAME) up -d api

up-prod: ## Start all production-like containers
	@echo "Starting up production-like services..."
	@ln -sf .env.prod .env
	docker compose -f docker-compose.yml --project-name $(PROD_PROJECT_NAME) up -d --build --pull always --remove-orphans

down-prod: ## Stop and remove all production-like containers
	@echo "Shutting down production-like services..."
	@ln -sf .env.prod .env
	docker compose -f docker-compose.yml --project-name $(PROD_PROJECT_NAME) down --remove-orphans

logs: ## View the logs for the development API service
	@echo "Following logs for the dev api service..."
	@ln -sf .env.dev .env
	docker compose -f docker-compose.yml -f docker-compose.override.yml --project-name $(DEV_PROJECT_NAME) logs -f api

shell: ## Open a shell inside the running development API container
	@echo "Opening shell in dev api container..."
	@ln -sf .env.dev .env
	@docker compose -f docker-compose.yml -f docker-compose.override.yml --project-name $(DEV_PROJECT_NAME) exec api /bin/sh || \
		(echo "Failed to open shell. Is the container running? Try 'make up'" && exit 1)

migrate: ## Run database migrations against the development database
	@echo "Running database migrations for dev environment..."
	@ln -sf .env.dev .env
	docker compose -f docker-compose.yml -f docker-compose.override.yml --project-name $(DEV_PROJECT_NAME) exec api sh -c ". /app/.venv/bin/activate && alembic upgrade head"

# ==============================================================================
# CODE QUALITY & TESTING
# ==============================================================================

format: ## Format the code using Black
	@echo "Formatting code with Black..."
	poetry run black src/ tests/

format-check: ## Check if the code is formatted with Black
	@echo "Checking code format with Black..."
	poetry run black --check src/ tests/

lint: ## Lint and fix the code with Ruff automatically
	@echo "Linting and fixing code with Ruff..."
	poetry run ruff check src/ tests/ --fix

lint-check: ## Check the code for issues with Ruff
	@echo "Checking code with Ruff..."
	poetry run ruff check src/ tests/

unit-test: ## Run the fast, database-independent unit tests locally
	@echo "Running unit tests..."
	@poetry run pytest tests/unit

db-test: ## Run the slower, database-dependent tests locally
	@echo "Running database tests..."
	@poetry run pytest --db tests/db

test: ## Run the full test suite within a Docker container (slow)
	@echo "Running test suite..."
	@ln -sf .env.test .env
	@cleanup() { \
		echo "Shutting down test services..."; \
		docker compose -f docker-compose.yml -f docker-compose.override.yml --project-name $(TEST_PROJECT_NAME) down --remove-orphans; \
	}; \
	trap cleanup EXIT; \
	echo "Starting up test services..."; \
	docker compose -f docker-compose.yml -f docker-compose.override.yml --project-name $(TEST_PROJECT_NAME) up -d; \
	echo "Running pytest..."; \
	docker compose -f docker-compose.yml -f docker-compose.override.yml --project-name $(TEST_PROJECT_NAME) exec api pytest -p no:xdist

e2e-test: ## Run end-to-end tests in a self-contained environment
	@echo "Running end-to-end tests..."
	@ln -sf .env.test .env
	@set -a; source .env.test; set +a; \
	cleanup() { \
		echo "Shutting down E2E test services..."; \
		docker compose -f docker-compose.yml -f docker-compose.override.yml --project-name $(TEST_PROJECT_NAME) down --remove-orphans; \
	}; \
	trap cleanup EXIT; \
	echo "Starting up E2E test services..."; \
	docker compose -f docker-compose.yml -f docker-compose.override.yml --project-name $(TEST_PROJECT_NAME) up -d --build; \
	echo "Waiting for API service to be healthy..."; \
	timeout 60s bash -c 'while [[ $$(curl -s -o /dev/null -w ''%{http_code}'' http://localhost:$$HOST_PORT/health) != "200" ]]; do echo "Waiting for API..."; sleep 2; done'; \
	echo "API is healthy. Running E2E tests..."; \
	(curl -f -s -X POST http://localhost:$$HOST_PORT/api/v1/generate \
		-H "Content-Type: application/json" \
		-d "{\"model\": \"$$BUILT_IN_OLLAMA_MODEL\",\"prompt\": \"Why is the sky blue?\",\"stream\": false}" | grep "choices" > /dev/null && echo "✅ Generate test PASSED") || (echo "❌ Generate test FAILED" && exit 1)