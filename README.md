# Private LLM API Server

## Overview

This project provides a robust, production-ready API server designed to serve local Large Language Models (LLMs). Built with FastAPI, it offers a clean, high-performance, and scalable solution for integrating local AI capabilities into your applications.

The architecture emphasizes a clean separation of concerns and a fully containerized environment using Docker. **A key feature of this architecture is the self-contained Ollama service, where the AI model is baked directly into the Docker image.** This creates an immutable, portable, and GPU-accelerated service, ensuring consistency and high performance from development to production.

## Tech Stack

The project leverages a modern Python technology stack:

- **Backend Framework**: FastAPI
- **Database**: PostgreSQL
- **Containerization**: Docker, Docker Compose
- **Dependency Management**: Poetry
- **Database Migrations**: Alembic
- **Code Quality**: Ruff (Linter), Black (Formatter)
- **Testing**: Pytest
- **LLM Integration**: Ollama (with GPU support)

## Setup and Execution

### Prerequisites

- Docker and Docker Compose
- `make` command
- NVIDIA GPU with drivers installed (for production-like performance)

### 1. Initialize Your Environment

Getting started is as simple as running one command. This only needs to be done once.

```sh
make setup
```

This command handles all the necessary first-time setup:
1.  **Creates Environment Files**: It copies `.env.example` to `.env.dev` (for local development) and `.env.prod` (for production).
2.  **Pulls Required Images**: It automatically pulls the `postgres:16-alpine` Docker image required for running the test suite, ensuring your environment is ready for testing from the start.

You only need to focus on `.env.dev` for your local development.

### 2. Start the Services

Start all services (API server, database, and Ollama) for development using a simple `make` command:

```sh
make up
```

This command builds the necessary Docker images, including the custom Ollama image with the model specified in your `.env` file baked in. **The Makefile automatically selects the correct `.env.dev` configuration by creating a symbolic link (`.env`) that Docker Compose uses by default.** This provides a seamless developer experience.

The API will be accessible at `http://127.0.0.1:8000` by default. If you set `HOST_BIND_IP=0.0.0.0`, access it via `http://<your-host-ip>:8000`. The source code is mounted as a volume, enabling hot-reloading on code changes.

### 3. Run Database Migrations (If Needed)

The application's entrypoint script automatically runs database migrations on startup, so you typically do not need to run this command manually. However, if you need to apply new migrations to an already running server without restarting it, you can use this command:

```sh
make migrate
```

## Environment Variables

This project follows the **DRY (Don't Repeat Yourself)** principle by defining a single, unified set of variable names in `.env.example`. The `Makefile` handles the complexity of environment switching by creating a symbolic link named `.env` that points to the correct configuration file (`.env.dev` or `.env.prod`).

Key variables include:
- **`HOST_BIND_IP`**: The IP address on the host machine to which the API server port will bind. Use `127.0.0.1` for local access only (recommended for development) and `0.0.0.0` to allow external access (for production).
- **`DATABASE_URL`**: The full connection string for the PostgreSQL database.
- **`BUILT_IN_OLLAMA_MODEL`**: The name of the Ollama model to be baked into the Docker image during the build process. This model will be active by default on server startup and cannot be deleted via the API.

## API Specification

### Endpoint: `POST /api/v1/generate`

This is the sole endpoint for generating text from the LLM.

### Request Body

The request body must be a JSON object with the following fields:

| Parameter | Type    | Default | Description                               |
|-----------|---------|---------|-------------------------------------------|
| `prompt`  | string  |         | **Required.** The input text for the LLM. |
| `stream`  | boolean | `false` | If `true`, the response will be streamed. |

**Note**: The model used for generation is the one currently active on the server. The default model is set via the `BUILT_IN_OLLAMA_MODEL` environment variable, and it can be changed dynamically using the `POST /api/v1/models/switch/{model_name}` endpoint.

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

The host depends on your `.env.dev` settings (`HOST_BIND_IP`). The port is fixed at `8000`. If `HOST_BIND_IP=0.0.0.0`, replace `127.0.0.1` with your host IP in the examples below.

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

## Development Workflow

### Recommended: Local Development with Poetry

For the fastest development cycle, we recommend running tools like linters, formatters, and tests directly on your local machine.

**1. Install Dependencies:**
First, ensure you have [Poetry](https://python-poetry.org/docs/#installation) installed. Then, from the project root, install all dependencies into a local virtual environment managed by Poetry:
```sh
poetry install
```

**2. Running Commands:**
Once the dependencies are installed, you can run tools directly using `poetry run`:

| Command                 | Description                                                  |
|-------------------------|--------------------------------------------------------------|
| `poetry run pytest`     | 🧪 Runs the test suite using `pytest-docker` to manage the DB. |
| `poetry run ruff .`     | 🔎 Lints the code for issues using Ruff.                     |
| `poetry run ruff . --fix` | 🩹 Lints the code with Ruff and applies fixes automatically. |
| `poetry run black .`    | 🎨 Formats the entire codebase using Black.                  |

### Alternative: Docker-Based Commands with `make`

If you prefer not to install Python/Poetry locally, you can use `make` to run commands inside Docker containers. This can be slower but requires only Docker and `make` to be installed.

| Command             | Description                                                              |
|---------------------|--------------------------------------------------------------------------|
| `make help`         | ✨ Shows a help message with all available commands.                     |
| `make setup`        | 🚀 Initializes `.env.dev` and `.env.prod` from the single `.env.example`. |
| `make up`           | 🐳 Starts all development containers in detached mode.                   |
| `make down`         | 🛑 Stops and removes all development containers.                         |
| `make logs`         | 📜 Tails the logs of the API service in real-time.                       |
| `make shell`        | 💻 Opens an interactive shell (`/bin/sh`) inside the API container.      |
| `make migrate`      | 🗄️ Runs database migrations against the development database.           |
| `make format`       | 🎨 Formats the entire codebase using Black (via Docker).                 |
| `make format-check` | 🎨 Checks if the code is formatted with Black (via Docker).            |
| `make lint`         | 🔎 Lints the code for issues using Ruff (via Docker).                    |
| `make lint-fix`     | 🩹 Lints and fixes code with Ruff (via Docker).                          |

## Deployment

This project is configured for continuous integration, which automatically builds and pushes a Docker image to the GitHub Container Registry (GHCR). The actual deployment to a server is a manual process.

### Automated Build Process

-   **CI Pipeline**: On every push to the `main` branch, the pipeline runs linters and tests.
-   **Build & Push**: On a successful push to `main`, a production-ready Docker image is built and pushed to GHCR. This image contains the application server and the self-contained Ollama service with the specified model.

### Manual Deployment Steps

The deployment process is now simpler and more consistent with the development workflow.

1.  **Prepare your server**: Ensure Docker, Docker Compose, `make`, and NVIDIA container toolkit/drivers are installed.
2.  **Create `.env.prod` file**: Manually create a `.env.prod` file on your server. Use `.env.example` as a reference. Populate it with your production-level configurations (e.g., database credentials, `HOST_BIND_IP=0.0.0.0`). The API port is fixed at `8000`.
3.  **Pull the image**: Pull the latest Docker image from GHCR.
4.  **Start services**: Use the `make up-prod` command. This command uses `docker-compose.yml` without any overrides and automatically selects your `.env.prod` file for configuration.

```sh
# (On your server)
make up-prod
```

This streamlined approach removes the need for a separate `docker-compose.prod.yml`, reducing complexity and making the deployment process more robust.