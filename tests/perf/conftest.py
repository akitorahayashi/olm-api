import os
import subprocess
import time
from typing import Generator

import httpx
import pytest
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def load_prompt() -> str:
    """
    Load prompt from the shared prompt.txt file.
    """
    prompt_path = os.path.join(os.path.dirname(__file__), "prompt.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read().strip()


def get_model_name() -> str:
    """
    Get the model name. Configure the model name here manually.
    """
    # Manually configure the model name here
    model_name = "qwen3:0.6b"
    return model_name


# Set environment variables for Docker Compose
os.environ["HOST_BIND_IP"] = os.getenv("HOST_BIND_IP", "127.0.0.1")
os.environ["TEST_PORT"] = os.getenv("TEST_PORT", "8002")
os.environ["BUILT_IN_OLLAMA_MODEL"] = os.getenv("BUILT_IN_OLLAMA_MODEL", "qwen3:0.6b")


@pytest.fixture(scope="session", autouse=True)
def perf_setup() -> Generator[None, None, None]:
    """
    Manages the lifecycle of the application for performance testing.
    """
    # Determine if sudo should be used based on environment variable
    use_sudo = os.getenv("SUDO") == "true"
    docker_command = ["sudo", "-E", "docker"] if use_sudo else ["docker"]

    host_bind_ip = os.getenv("HOST_BIND_IP", "127.0.0.1")
    host_port = os.getenv("TEST_PORT", "8002")
    health_url = f"http://{host_bind_ip}:{host_port}/health"

    # Define compose commands (environment variables handled by docker-compose.test.override.yml)
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
                capture_output=True,
                text=True,
                env=os.environ,
            )  # 5 minutes timeout
        except subprocess.CalledProcessError as e:
            print("\n🛑 compose up failed; performing cleanup...")
            print(f"Exit code: {e.returncode}")
            print(f"STDOUT: {e.stdout}")
            print(f"STDERR: {e.stderr}")
            subprocess.run(compose_down_command, check=False)
            raise

        # Health Check
        start_time = time.time()
        timeout = 300  # 5 minutes for external Ollama connection
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
        subprocess.run(compose_down_command, check=False)
    finally:
        pass
