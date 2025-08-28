import os
import subprocess
import time
from typing import Generator

import httpx
import pytest


@pytest.fixture(scope="session", autouse=True)
def perf_setup() -> Generator[None, None, None]:
    """
    Manages the lifecycle of the application for performance testing.
    """
    # Environment variables are now controlled by the docker-compose.test.override.yml
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
        "docker-compose.test.override.yml",
        "--project-name",
        "olm-api-test",
        "up",
        "-d",
        "--build",
    ]
    compose_down_command = docker_command + [
        "compose",
        "-f",
        "docker-compose.yml",
        "-f",
        "docker-compose.test.override.yml",
        "--project-name",
        "olm-api-test",
        "down",
        "--remove-orphans",
    ]

    try:
        # Start services, ensuring cleanup on failure
        print("\n🚀 Starting Performance Test services...")
        print(f"Health check URL: {health_url}")
        try:
            subprocess.run(
                compose_up_command,
                check=True,
                timeout=300,
            )  # 5 minutes timeout
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
                else:
                    print(
                        f"⏳ API is up (status {response.status_code}), but not healthy yet. Retrying..."
                    )
            except httpx.RequestError as e:
                print(f"⏳ API not yet healthy, retrying... Error: {e}")
            # Sleep at the end of the loop to prevent busy-waiting
            time.sleep(5)

        if not is_healthy:
            subprocess.run(
                docker_command
                + [
                    "compose",
                    "-f",
                    "docker-compose.yml",
                    "-f",
                    "docker-compose.test.override.yml",
                    "--project-name",
                    "olm-api-test",
                    "logs",
                    "api",
                ]
            )
            # Ensure teardown on health check failure
            print(
                "\n🛑 Stopping Performance Test services due to health check failure..."
            )
            subprocess.run(compose_down_command, check=False)
            pytest.fail(f"API did not become healthy within {timeout} seconds.")

        yield

        # Stop services
        print("\n🛑 Stopping Performance Test services...")
        subprocess.run(compose_down_command, check=True)
    finally:
        pass
