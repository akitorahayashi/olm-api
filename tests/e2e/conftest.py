import os
import subprocess
import time
from typing import Generator

import httpx
import pytest
from dotenv import load_dotenv


@pytest.fixture(scope="session", autouse=True)
def e2e_setup() -> Generator[None, None, None]:
    """
    Manages the lifecycle of the application for end-to-end testing.

    This session-scoped fixture automatically performs the following steps:
    1.  **Loads Environment**: Reads configuration from the `.env.test` file.
    2.  **Starts Services**: Executes `docker-compose up` to build and start all
        required services (API, database, Ollama).
    3.  **Health Check**: Polls the API's `/health` endpoint, waiting until the
        server is responsive before allowing tests to proceed.
    4.  **Yields Control**: Pauses and allows the E2E tests to run against the
        live application stack.
    5.  **Stops Services**: Executes `docker-compose down` to stop and remove
        all services and networks, ensuring a clean state after the test
        session concludes.
    """
    # 1. Load environment variables from .env.test
    load_dotenv(".env.test")
    host_port = os.getenv("HOST_PORT", "8000")
    health_url = f"http://localhost:{host_port}/health"

    # 2. Start services using docker-compose
    print("\n🚀 Starting E2E services...")
    compose_up_command = [
        "docker",
        "compose",
        "-f",
        "docker-compose.yml",
        "-f",
        "docker-compose.override.yml",
        "up",
        "-d",
        "--build",
    ]
    subprocess.run(compose_up_command, check=True)

    # 3. Health Check
    start_time = time.time()
    timeout = 120  # 2 minutes timeout
    is_healthy = False
    while time.time() - start_time < timeout:
        try:
            response = httpx.get(health_url, timeout=5)
            if response.status_code == 200:
                print("✅ API is healthy!")
                is_healthy = True
                break
        except httpx.RequestError:
            print("⏳ API not yet healthy, retrying...")
            time.sleep(5)

    if not is_healthy:
        subprocess.run(["docker", "compose", "logs", "api"])
        pytest.fail(f"API did not become healthy within {timeout} seconds.")

    # 4. Yield control to the tests
    yield

    # 5. Stop services
    print("\n🛑 Stopping E2E services...")
    compose_down_command = ["docker", "compose", "down", "--remove-orphans"]
    subprocess.run(compose_down_command, check=True)
