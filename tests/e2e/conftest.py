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
    """
    load_dotenv(".env.test")
    host_port = os.getenv("HOST_PORT", "8000")
    health_url = f"http://localhost:{host_port}/health"

    # Determine if sudo should be used based on environment variable
    use_sudo = os.getenv("SUDO") == "true"
    docker_command = ["sudo", "docker"] if use_sudo else ["docker"]

    # Define compose commands
    compose_up_command = docker_command + [
        "compose",
        "-f",
        "docker-compose.yml",
        "-f",
        "docker-compose.override.yml",
        "up",
        "-d",
        "--build",
    ]
    compose_down_command = docker_command + ["compose", "down", "--remove-orphans"]

    # Start services, ensuring cleanup on failure
    print("\n🚀 Starting E2E services...")
    try:
        subprocess.run(compose_up_command, check=True)
    except subprocess.CalledProcessError:
        print("\n🛑 compose up failed; performing cleanup...")
        subprocess.run(compose_down_command, check=False)
        raise

    # Health Check
    start_time = time.time()
    timeout = 120
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
        subprocess.run(docker_command + ["compose", "logs", "api"])
        # Ensure teardown on health check failure
        print("\n🛑 Stopping E2E services due to health check failure...")
        subprocess.run(compose_down_command, check=False)
        pytest.fail(f"API did not become healthy within {timeout} seconds.")

    yield

    # Stop services
    print("\n🛑 Stopping E2E services...")
    subprocess.run(compose_down_command, check=True)