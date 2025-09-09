import os

from .client import OllamaApiClient
from .local_client import OllamaLocalClient
from .mock import MockOllamaApiClient
from .protocol import OllamaClientProtocol


def create_client() -> OllamaClientProtocol:
    """
    Factory function to create the appropriate Ollama client based on the
    `OLM_CLIENT_MODE` environment variable.

    - If `OLM_CLIENT_MODE` is "local", it returns an `OllamaLocalClient`
      that connects to a local `ollama serve` instance.
    - If `OLM_CLIENT_MODE` is "remote" (or not set), it returns an
      `OllamaApiClient` that connects to the remote API server, configured
      via the `OLM_API_ENDPOINT` environment variable.
    - If `OLM_CLIENT_MODE` is "mock", it returns a `MockOllamaApiClient`.

    Returns:
        An instance of a class that implements the `OllamaClientProtocol`.

    Raises:
        ValueError: If the client mode is invalid or if required environment
                    variables for a specific mode are not set.
    """
    mode = os.getenv("OLM_CLIENT_MODE", "remote").lower()

    if mode == "local":
        return OllamaLocalClient()
    elif mode == "remote":
        api_url = os.getenv("OLM_API_ENDPOINT")
        if not api_url:
            raise ValueError("OLM_API_ENDPOINT must be set for 'remote' client mode.")
        return OllamaApiClient(api_url=api_url)
    elif mode == "mock":
        return MockOllamaApiClient()
    else:
        raise ValueError(
            f"Invalid OLM_CLIENT_MODE: '{mode}'. "
            "Valid modes are 'local', 'remote', or 'mock'."
        )


__all__ = [
    "create_client",
    "OllamaApiClient",
    "OllamaLocalClient",
    "MockOllamaApiClient",
    "OllamaClientProtocol",
]
