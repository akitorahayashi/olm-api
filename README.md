# Private LLM API Server

## Overview

This project provides a robust, production-ready API server for interacting with local Large Language Models (LLMs) like those available through Ollama. It is built with FastAPI and designed for high performance, easy development, and scalable deployment using Docker.

The architecture emphasizes a clean separation of concerns, a containerized environment for consistency across development and production, and a comprehensive set of tools to ensure code quality and a smooth developer experience (DX).

## Tech Stack

- **Backend**: FastAPI
- **Database**: PostgreSQL
- **Containerization**: Docker, Docker Compose
- **Dependency Management**: Poetry
- **Database Migrations**: Alembic
- **CI/CD**: GitHub Actions
- **Code Quality**: Black (Formatter), Ruff (Linter)
- **Testing**: Pytest

## Local Development Environment Setup

Follow these steps to get the development environment up and running on your local machine.

### Prerequisites

- Docker and Docker Compose
- `make` command

### 1. Initial Project Setup

First, you need to create a `.env` file for local configuration. The `make setup` command will copy the example file for you. This only needs to be done once.

```sh
make setup
```

This creates a `.env` file with default settings. You can review and edit this file if needed. For example, you can change the `WEB_PORT` if the default `8000` is already in use on your machine.

### 2. Start the Services

Once the `.env` file is ready, start all the necessary services (API server, database) using Docker Compose:

```sh
make up
```

This command will build the Docker images and run the containers in the background. The API server will be available at `http://127.0.0.1:8000` (or the port you configured in `.env`). The source code is mounted as a volume, so changes you make to the code will trigger an automatic reload of the server.

### 3. Run Database Migrations

After the services are running, apply the database migrations to set up the required tables in your local PostgreSQL database:

```sh
make migrate
```

Your local development environment is now ready!

## Makefile Commands

This project uses a `Makefile` to provide a simple and consistent interface for common commands.

| Command         | Description                                                                                              |
| --------------- | -------------------------------------------------------------------------------------------------------- |
| `make help`     | ✨ Displays this help message with all available commands.                                                |
| `make setup`    | 🚀 Initializes the project by creating a `.env` file from the example.                                   |
| `make up`       | 🐳 Starts all development containers in detached mode.                                                    |
| `make down`     | 🛑 Stops and removes all development containers and networks.                                            |
| `make logs`     | 📜 Tails the logs of the API service in real-time.                                                        |
| `make shell`    | 💻 Opens an interactive shell (`/bin/sh`) inside the running API container.                                |
| `make migrate`  | 🗄️ Runs database migrations against the development database.                                             |
| `make format`   | 🎨 Formats the entire codebase using Black.                                                              |
| `make lint`     |  lint Checks the code for any style issues or errors using Ruff.                                          |
| `make test`     | 🧪 Runs the entire test suite in an isolated, containerized environment with its own database.             |


## Testing

To run the test suite, use the following command:

```sh
make test
```

This command spins up dedicated `test` and `db_test` containers. The test database runs in-memory (using `tmpfs`) to ensure tests are fast and completely isolated from your local development database.

## Code Quality

To maintain a high standard of code quality, this project uses **Ruff** for linting and **Black** for formatting.

- **To check for linting issues:**
  ```sh
  make lint
  ```
- **To automatically format the code:**
  ```sh
  make format
  ```

The CI pipeline will fail if there are any linting or formatting errors, so it's recommended to run these commands before committing changes.

## Deployment

This project is configured for continuous integration and deployment using GitHub Actions.

### CI Pipeline (`ci.yml`)

On every `push` or `pull_request` to the `main` branch, the CI pipeline automatically runs the following checks:
1.  **Linting**: Ensures the code adheres to the style guide.
2.  **Testing**: Runs the full `pytest` suite in a clean, containerized environment.

### Build and Push (`build-and-push.yml`)

When code is pushed to the `main` branch, a separate workflow automatically:
1.  Builds a production-optimized Docker image.
2.  Tags the image with the commit SHA and `latest`.
3.  Pushes the image to the GitHub Container Registry (GHCR).

### Manual Deployment (`deploy.yml`)

Deployment to a server (e.g., staging or production) is a manual process that can be triggered from the GitHub Actions UI. This workflow uses SSH to connect to the target server and runs a script to pull the latest image from GHCR and restart the services.
