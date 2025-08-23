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

### 1. Create `.env` file

The project requires an `.env` file for configuration. The `make setup` command simplifies this process by copying the `.env.example` template. This only needs to be done once.

```sh
make setup
```

This command creates a `.env` file in the project root. You can edit this file to match your local setup.

### 2. Start the Services

With the `.env` file configured, start all services (API server and database) using Docker Compose:

```sh
make up
```

This command builds the necessary Docker images and starts the containers. The API will be accessible at `http://127.0.0.1:8000` by default. The source code is mounted as a volume, enabling hot-reloading on code changes.

### 3. Run Database Migrations

After the containers are running, apply the database migrations to set up the required tables:

```sh
make migrate
```

Your local development environment is now fully configured and ready to use.

## Environment Variables

The application is configured via environment variables defined in the `.env` file. The most important ones are:

- **`DATABASE_URL`**: The full connection string for the PostgreSQL database. This is used by the `api` container to connect to the `db` container.
- **`OLLAMA_BASE_URL`**: The base URL for the Ollama server. When running this project in Docker and Ollama on the host machine, you may need to set this to `http://host.docker.internal:11434`.
- **`OLLAMA_MODEL`**: The specific Ollama model to be used for generating responses (e.g., `qwen3:8b`). This is configured on the server-side and is not part of the API request.

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

| Command          | Description                                                    |
|------------------|----------------------------------------------------------------|
| `make help`      | ✨ Shows a help message with all available commands.           |
| `make setup`     | 🚀 Initializes the project by creating a `.env` file.          |
| `make up`        | 🐳 Starts all development containers in detached mode.         |
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

To deploy the application, you need to pull the latest image from the container registry and run it on your local server.

1.  **Prepare your server**: Ensure Docker and Docker Compose are installed on your machine.
2.  **Create `.env` file**: Create a production `.env` file on your server with the necessary configurations.
3.  **Pull the image**: Pull the latest Docker image from the registry where it was pushed by the GitHub Actions workflow.
4.  **Start services**: Use `docker-compose.yml` to start the application.

```sh
# (On your server)
docker compose pull
docker compose up -d
```
