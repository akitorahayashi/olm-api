# Private LLM API Server

## Overview

This project provides a robust, production-ready API server designed to serve local Large Language Models (LLMs) via Ollama. Built with FastAPI, it offers a clean, high-performance, and scalable solution for integrating local AI capabilities into your applications.

The architecture emphasizes a clean separation of concerns, a fully containerized environment using Docker for consistency across development and production, and a comprehensive set of development tools to ensure code quality and a smooth developer experience (DX).

## Tech Stack

The project leverages a modern Python technology stack:

- **Backend Framework**: FastAPI
- **Database**: PostgreSQL
- **Containerization**: Docker, Docker Compose
- **Dependency Management**: Poetry
- **Database Migrations**: Alembic
- **Code Quality**: Ruff (Linter), Black (Formatter)
- **Testing**: Pytest
- **LLM Integration**: Ollama

## Setup and Execution

### Prerequisites

- Docker and Docker Compose
- `make` command

### 1. Initialize Environment Files

The project uses a single template, `.env.example`, as the single source of truth for all required environment variables. The `make setup` command uses this template to create environment-specific files. This only needs to be done once.

```sh
make setup
```

This command creates two files:
- `.env.dev`: For local development. You can edit this file to match your local setup.
- `.env.prod`: For production deployments. This file is ignored by Git and should be managed securely.

For local development, you only need to focus on `.env.dev`.

### 2. Start the Services

Start all services (API server and database) for development using a simple `make` command:

```sh
make up
```

This command builds the necessary Docker images and starts the containers. **The Makefile automatically selects the correct `.env.dev` configuration by creating a symbolic link (`.env`) that Docker Compose uses by default.** This provides a seamless developer experience, as you don't need to manually specify environment files.

The API will be accessible at `http://127.0.0.1:8000` by default. The source code is mounted as a volume, enabling hot-reloading on code changes.

### 3. Run Database Migrations (If Needed)

The application's entrypoint script automatically runs database migrations on startup, so you typically do not need to run this command manually. However, if you need to apply new migrations to an already running server without restarting it, you can use this command:

```sh
make migrate
```

## Environment Variables

This project follows the **DRY (Don't Repeat Yourself)** principle by defining a single, unified set of variable names in `.env.example` (e.g., `API_PORT` instead of `DEV_API_PORT` and `PROD_API_PORT`).

The value for each variable is then set in the environment-specific files (`.env.dev`, `.env.prod`). For example, you can set `API_PORT=8000` in `.env.dev` and `API_PORT=50000` in `.env.prod`.

The `Makefile` handles the complexity of environment switching. When you run a command like `make up` or `make up-prod`, it automatically creates a symbolic link named `.env` that points to the correct configuration file (`.env.dev` or `.env.prod`). Docker Compose then reads this `.env` file by default. This makes the process seamless and robust.

Key variables include:
- **`API_PORT`**: The external port to expose for the API server.
- **`DATABASE_URL`**: The full connection string for the PostgreSQL database.
- **`OLLAMA_BASE_URL`**: The base URL for the Ollama server.

## API Specification

### Endpoint: `POST /api/v1/generate`

This is the sole endpoint for generating text from the LLM.

### Request Body

The request body must be a JSON object with the following fields:

| Parameter | Type    | Default | Description                               |
|-----------|---------|---------|-------------------------------------------|
| `prompt`  | string  |         | **Required.** The input text for the LLM. |
| `stream`  | boolean | `false` | If `true`, the response will be streamed. |

**Note**: The model used for the generation is determined by the `OLLAMA_MODEL` environment variable on the server, not by a parameter in the request body.

### Response Body

#### Standard Response (`stream: false`)

If `stream` is `false` (or omitted), the API returns a single JSON object after the full response has been generated.

**Example Response:**
```json
{
  "response": "This is the complete response from the language model."
}
```

#### Streaming Response (`stream: true`)

If `stream` is `true`, the API returns a stream of Server-Sent Events (SSE). Each event contains a chunk of the response data. This is useful for real-time applications where you want to display the response as it's being generated.

The response will have the `Content-Type: text/event-stream` header. Each message is formatted as `data: ...\n\n`.

**Example Stream:**
```
data: {"response": "This "}

data: {"response": "is a "}

data: {"response": "streamed "}

data: {"response": "response."}

data: {}
```

## Usage Examples

### Standard Request (curl)

```sh
curl -X POST "http://127.0.0.1:8000/api/v1/generate" \
-H "Content-Type: application/json" \
-d '{"prompt": "Why is the sky blue?"}'
```

### Streaming Request (curl)

The `-N` (or `--no-buffer`) flag is important for viewing the stream as it arrives.

```sh
curl -X POST "http://127.0.0.1:8000/api/v1/generate" \
-H "Content-Type: application/json" \
-d '{"prompt": "Write a short story about a robot.", "stream": true}' -N
```

## Development Commands

This project uses a `Makefile` to provide a simple interface for common development tasks.

| Command          | Description                                                              |
|------------------|--------------------------------------------------------------------------|
| `make help`      | ✨ Shows a help message with all available commands.                     |
| `make setup`     | 🚀 Initializes `.env.dev` and `.env.prod` from the single `.env.example`. |
| `make up`        | 🐳 Starts all development containers in detached mode.                   |
| `make down`      | 🛑 Stops and removes all development containers.               |
| `make logs`      | 📜 Tails the logs of the API service in real-time.             |
| `make shell`     | 💻 Opens an interactive shell (`/bin/sh`) inside the API container.|
| `make migrate`   | 🗄️ Runs database migrations against the development database. |
| `make format`    | 🎨 Formats the entire codebase using Black.                    |
| `make format-check`| 🎨 Checks if the code is formatted with Black.                 |
| `make lint`      | 🔎 Lints the code for issues using Ruff.                       |
| `make lint-fix`  | 🩹 Lints the code with Ruff and applies fixes automatically.   |
| `make test`      | 🧪 Runs the test suite in an isolated, containerized environment.|

## Deployment

This project is configured for continuous integration, which automatically builds and pushes a Docker image to the GitHub Container Registry (GHCR). The actual deployment to a server is a manual process.

### Automated Build Process

-   **CI Pipeline**: On every push to the `main` branch, the pipeline runs linters and tests.
-   **Build & Push**: On a successful push to `main`, a production-ready Docker image is built and pushed to GHCR.

### Manual Deployment Steps

The deployment process is now simpler and more consistent with the development workflow.

1.  **Prepare your server**: Ensure Docker, Docker Compose, and `make` are installed.
2.  **Create `.env.prod` file**: Manually create a `.env.prod` file on your server. You can use `.env.example` as a reference for the required variables. Populate it with your production-level configurations (e.g., database credentials, a non-default `API_PORT` if desired).
3.  **Pull the image**: Pull the latest Docker image from GHCR.
4.  **Start services**: Use the `make up-prod` command. This command uses `docker-compose.yml` without any overrides and automatically selects your `.env.prod` file for configuration.

```sh
# (On your server)
make up-prod
```

This streamlined approach removes the need for a separate `docker-compose.prod.yml`, reducing complexity and making the deployment process more robust.
