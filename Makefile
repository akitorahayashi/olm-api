# Makefile for abstracting Docker Compose commands for a better DX.

# Use .PHONY to ensure these targets run even if files with the same name exist.
.PHONY: build up down logs migrate test help

# Define SUDO variable, which will be empty if the user is already root.
SUDO := $(shell if [ $$(id -u) -ne 0 ]; then echo "sudo"; fi)

# Default target runs when 'make' is called without arguments.
default: up

build:
	@echo "Building Docker images..."
	$(SUDO) docker compose build

up:
	@echo "Starting services in detached mode..."
	$(SUDO) docker compose up -d

down:
	@echo "Stopping and removing containers, networks, and volumes..."
	$(SUDO) docker compose down

logs:
	@echo "Following logs for the 'api' service..."
	$(SUDO) docker compose logs -f api

migrate:
	@echo "Running database migrations..."
	$(SUDO) docker compose exec api alembic upgrade head

test:
	@echo "Running tests inside the 'api' container..."
	$(SUDO) docker compose exec api pytest tests/

help:
	@echo "Available commands:"
	@echo "  build    - Build the docker images for the services"
	@echo "  up       - Start the services in the background"
	@echo "  down     - Stop and remove the services"
	@echo "  logs     - Follow the logs of the api service"
	@echo "  migrate  - Run database migrations"
	@echo "  test     - Run the test suite"
