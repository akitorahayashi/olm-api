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
.PHONY: help setup up down logs shell format format-check lint lint-fix test migrate

# Default target executed when 'make' is run without arguments
.DEFAULT_GOAL := help

# Define the project name based on the directory name for dynamic container naming
PROJECT_NAME := $(shell basename $(CURDIR))

# Use sudo if the user is not root, to handle Docker permissions
SUDO := $(shell if [ $$(id -u) -ne 0 ]; then echo "sudo"; fi)

# ==============================================================================
# HELP
# ==============================================================================

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ==============================================================================
# PROJECT SETUP & ENVIRONMENT
# ==============================================================================

setup: ## Initialize the project by creating a .env file
	@if [ ! -f .env ]; then \
		echo "Creating .env file from .env.example..."; \
		cp .env.example .env; \
	else \
		echo ".env file already exists. Skipping creation."; \
	fi

up: ## Start all development containers in detached mode
	@echo "Starting up services..."
	$(SUDO) docker compose --project-name $(PROJECT_NAME) up -d

down: ## Stop and remove all development containers
	@echo "Shutting down services..."
	$(SUDO) docker compose --project-name $(PROJECT_NAME) down --remove-orphans

up-prod: ## Start all containers using only docker-compose.yml (ignoring override)
    @echo "Starting up production-like services (ignoring override)..."
    $(SUDO) docker compose -f docker-compose.yml --project-name $(PROJECT_NAME)-prod up -d

down-prod: ## Stop and remove all containers started by up-prod
    @echo "Shutting down production-like services..."
    $(SUDO) docker compose -f docker-compose.yml --project-name $(PROJECT_NAME)-prod down --remove-orphans

logs: ## View the logs for the API service
	@echo "Following logs for the api service..."
	$(SUDO) docker compose --project-name $(PROJECT_NAME) logs -f api

shell: ## Open a shell inside the running API container
	@echo "Opening shell in api container..."
	@$(SUDO) docker compose --project-name $(PROJECT_NAME) exec api /bin/sh || \
		(echo "Failed to open shell. Is the container running? Try 'make up'" && exit 1)

migrate: ## Run database migrations against the development database
	@echo "Running database migrations..."
	$(SUDO) docker compose --project-name $(PROJECT_NAME) exec api sh -c ". /app/.venv/bin/activate && alembic upgrade head"

# ==============================================================================
# CODE QUALITY & TESTING
# ==============================================================================

format: ## Format the code using Black
	@echo "Formatting code with Black..."
	$(SUDO) docker compose --project-name $(PROJECT_NAME) exec api sh -c ". /app/.venv/bin/activate && black src/ tests/"

format-check: ## Check if the code is formatted with Black
	@echo "Checking code format with Black..."
	$(SUDO) docker compose --project-name $(PROJECT_NAME) exec api sh -c ". /app/.venv/bin/activate && black --check src/ tests/"

lint: ## Lint Check the code for issues with Ruff
	@echo "Linting code with Ruff..."
	$(SUDO) docker compose --project-name $(PROJECT_NAME) exec api sh -c ". /app/.venv/bin/activate && ruff check src/ tests/"

lint-fix: ## Check the code with Ruff and apply fixes automatically
	@echo "Linting and fixing code with Ruff..."
	$(SUDO) docker compose --project-name $(PROJECT_NAME) exec api sh -c ". /app/.venv/bin/activate && ruff check src/ tests/ --fix"

test: ## Run the test suite in an isolated environment
	@echo "Running test suite..."
	$(SUDO) docker compose --project-name $(PROJECT_NAME) run --rm --build test