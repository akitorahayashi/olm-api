import os
import subprocess
import time
from typing import Generator

import httpx
import pytest


@pytest.fixture(scope="session", autouse=True)
def e2e_setup() -> Generator[None, None, None]:
    """
    Manages the lifecycle of the application for end-to-end testing.
    """
    # Determine if sudo should be used based on environment variable
    use_sudo = os.getenv("SUDO") == "true"
    docker_command = ["sudo", "docker"] if use_sudo else ["docker"]

    host_bind_ip = os.getenv("HOST_BIND_IP", "127.0.0.1")
    host_port = os.getenv("HOST_PORT", "8001")
    health_url = f"http://{host_bind_ip}:{host_port}/health"

    # Define compose commands (environment variables handled by docker-compose.test.override.yml)
    # Use --env-file /dev/null to prevent reading .env file
    compose_up_command = docker_command + [
        "compose",
        "--env-file",
        "/dev/null",
        "-f",
        "docker-compose.yml",
        "-f",
        "docker-compose.test.override.yml",
        "--project-name",
        "olm-api-test",
        "up",
        "-d",
    ]
    compose_down_command = docker_command + [
        "compose",
        "--env-file",
        "/dev/null",
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
        subprocess.run(
            compose_up_command, check=True, timeout=600
        )  # 10 minutes timeout
    except subprocess.CalledProcessError:
        print("\n🛑 compose up failed; performing cleanup...")
        subprocess.run(compose_down_command, check=False)
        raise

    # Health Check
    start_time = time.time()
    timeout = 600  # 10 minutes for qwen3:0.6b model download
    is_healthy = False
    while time.time() - start_time < timeout:
        try:
            subprocess.run(
                compose_up_command,
                check=True,
                timeout=120,
                capture_output=True,
                text=True,
            )  # Reduced to 2 minutes since images are pre-pulled
        except subprocess.CalledProcessError as e:
            print("\n🛑 compose up failed; performing cleanup...")
            print(f"Exit code: {e.returncode}")
            print(f"STDOUT: {e.stdout}")
            print(f"STDERR: {e.stderr}")
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
                    "/dev/null",
                    "-f",
                    "docker-compose.yml",
                    "-f",
                    "docker-compose.test.override.yml",
                    "--project-name",
                    "olm-api-test",
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
        pass
