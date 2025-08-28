import os
import shutil
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
    # Load the E2E test environment, overriding any existing env vars
    # to prevent contamination from other test fixtures (e.g., db_setup).
    load_dotenv(".env.test", override=True)
    host_port = os.getenv("HOST_PORT", "8000")
    health_url = f"http://localhost:{host_port}/health"

    # Determine if sudo should be used based on environment variable
    use_sudo = os.getenv("SUDO") == "true"
    docker_command = ["sudo", "docker"] if use_sudo else ["docker"]

    # Define compose commands
    compose_up_command = docker_command + [
        "compose",
        "--env-file",
        ".env.test",
        "-f",
        "docker-compose.yml",
        "-f",
        "docker-compose.override.yml",
        "up",
        "-d",
        "--build",
    ]
    compose_down_command = docker_command + [
        "compose",
        "--env-file",
        ".env.test",
        "-f",
        "docker-compose.yml",
        "-f",
        "docker-compose.override.yml",
        "down",
        "--remove-orphans",
    ]

    # Create a temporary .env file for docker-compose to use
    shutil.copy(".env.test", ".env")

    try:
        # Start services, ensuring cleanup on failure
        print("\n🚀 Starting E2E services...")
        print(f"Health check URL: {health_url}")
        try:
            result = subprocess.run(
                compose_up_command,
                check=True,
                timeout=300,
                capture_output=True,
                text=True,
            )  # 5 minutes timeout
            print("Docker compose up output:", result.stdout)
            if result.stderr:
                print("Docker compose up stderr:", result.stderr)
        except subprocess.CalledProcessError:
            print("\n🛑 compose up failed; performing cleanup...")
            subprocess.run(compose_down_command, check=False)
            raise

        # Health Check
        start_time = time.time()
        timeout = 300  # 5 minutes for qwen3:0.6b model download
        is_healthy = False
        while time.time() - start_time < timeout:
            try:
                response = httpx.get(health_url, timeout=5)
                if response.status_code == 200:
                    print("✅ API is healthy!")
                    is_healthy = True
                    break
            except httpx.RequestError as e:
                print(f"⏳ API not yet healthy, retrying... Error: {e}")
                time.sleep(5)

        if not is_healthy:
            subprocess.run(
                docker_command
                + [
                    "compose",
                    "--env-file",
                    ".env.test",
                    "-f",
                    "docker-compose.yml",
                    "-f",
                    "docker-compose.override.yml",
                    "logs",
                    "api",
                    "ollama",
                ]
            )
            # Ensure teardown on health check failure
            print("\n🛑 Stopping E2E services due to health check failure...")
            subprocess.run(compose_down_command, check=False)
            pytest.fail(f"API did not become healthy within {timeout} seconds.")

        yield

        # Stop services
        print("\n🛑 Stopping E2E services...")
        subprocess.run(compose_down_command, check=True)
    finally:
        # Clean up the temporary .env file
        if os.path.exists(".env"):
            os.remove(".env")
