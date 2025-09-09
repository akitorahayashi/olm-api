# Ollama API Client SDK

This SDK provides a standardized way to interact with the Ollama API. It includes a real client for production use and a mock client for testing. Both clients adhere to a common `OllamaClientProtocol`.

## Core Components

* **`OllamaClientProtocol`** : An interface defining the common methods (`gen_stream`, `gen_batch`). Use this for type hinting to easily switch between real and mock clients.
* **`OllamaApiClient`** : The primary client for making real HTTP requests to the Ollama API endpoint.
* **`MockOllamaApiClient`** : A high-fidelity mock client that simulates API behavior for testing without making network requests.

## `OllamaClientProtocol`

This is the abstract interface for all clients. It guarantees two methods. Code that depends on this protocol can seamlessly use either the real or mock client.

**Methods:**

* `gen_stream(prompt: str, model: str | None = None) -> AsyncGenerator[str, None]`:
  * Streams the response token by token.
* `gen_batch(prompt: str, model: str | None = None) -> str`:
  * Returns the complete response as a single string.

---

## `OllamaApiClient` (Real Client)

Use this client to connect to a running Ollama API service.

### Initialization

The client must be initialized with the API endpoint URL.

**Priority:**

1. **`api_url` parameter** : Explicitly provided URL.
2. **`OLM_API_ENDPOINT` environment variable** : URL from the environment.

A `ValueError` is raised if neither is provided.

```python
from sdk.olm_api_client import OllamaApiClient

# Recommended: Initialize with a URL
client = OllamaApiClient(api_url="http://localhost:8000")

# Alternatively, using an environment variable
# export OLM_API_ENDPOINT="http://localhost:8000"
# client = OllamaApiClient()
```

### Usage

Specify the model for each request. If `model` is `None`, it falls back to the `OLLAMA_MODEL` environment variable.

#### Streaming (`gen_stream`)

```python
import asyncio
from sdk.olm_api_client import OllamaApiClient

client = OllamaApiClient(api_url="http://localhost:8000")

async def stream_example():
    response_stream = client.gen_stream(
        prompt="Why is the sky blue?",
        model="qwen3:0.6b"
    )
    async for chunk in response_stream:
        print(chunk, end="", flush=True)

# asyncio.run(stream_example())
```

#### Non-Streaming (`gen_batch`)

```python
import asyncio
from sdk.olm_api_client import OllamaApiClient

client = OllamaApiClient(api_url="http://localhost:8000")

async def batch_example():
    response = await client.gen_batch(
        prompt="Why is the sky blue?",
        model="qwen3:0.6b"
    )
    print(response)

# asyncio.run(batch_example())
```

---

## `MockOllamaApiClient` (Mock Client)

Use this for testing. It simulates API responses locally and deterministically.

### Initialization

```python
from sdk.olm_api_client import MockOllamaApiClient

# Default responses with no delay
client = MockOllamaApiClient(token_delay=0)

# Custom responses
custom_responses = ["Response 1", "Response 2", "Response 3"]
client = MockOllamaApiClient(responses=custom_responses, token_delay=0)

# Realistic streaming delay
realistic_client = MockOllamaApiClient(token_delay=0.01)
```

### Parameters

* **`responses`** : Optional list of strings to use as responses. If not provided, uses default responses.
* **`token_delay`** : Delay between tokens during streaming (seconds). Use `0` for fast tests.
* **`api_url`** : Accepted for compatibility but not used.

### Behavior

* **Configurable Responses** : Cycles through provided responses array or defaults.
* **Simulated Thinking** : Responses include `<think>` tags unless `think=False` is specified.
* **No Network Required** : All operations are performed in-memory.

### Usage

The interface is identical to `OllamaApiClient`.

```python
import asyncio
from sdk.olm_api_client import MockOllamaApiClient

# Custom responses for testing
test_responses = ["Test answer 1", "Test answer 2"]
client = MockOllamaApiClient(responses=test_responses, token_delay=0)

async def mock_example():
    # First call returns "Test answer 1"
    response1 = await client.gen_batch("any prompt", think=False)
    print(response1)  # Output: Test answer 1
    
    # Second call returns "Test answer 2"
    response2 = await client.gen_batch("another prompt", think=False)
    print(response2)  # Output: Test answer 2

# asyncio.run(mock_example())
```

---

## Recommended Usage Pattern (Dependency Injection)

For building robust and testable applications, we recommend using a factory function to provide the appropriate API client. By type-hinting with `OllamaClientProtocol`, you can easily inject either the real client (`OllamaApiClient`) or a mock client (`MockOllamaApiClient`) depending on the environment.

This approach supports two main development and testing patterns, which can be selected using environment variables without any code changes.

### Pattern A: Local-Only Development (e.g., on a MacBook)

This pattern is ideal for feature development and rapid iteration.

-   **Setup**: Run `ollama serve` directly on your development machine.
-   **Configuration**: The client application initializes `OllamaApiClient` with the `api_url` pointing to your local Ollama server (e.g., `http://localhost:11434`).
-   **Benefits**:
    -   **No Dependencies**: Eliminates reliance on the shared `olm-api` server on the Mac mini.
    -   **High Speed**: Network latency is zero, providing extremely fast responses.
    -   **Clean Logging**: The central API server's database remains free of development-related logs.

### Pattern B: Integrated Testing (Connecting to Deployed API)

This pattern is used to test your application in a state that closely mirrors the production environment.

-   **Setup**: The client application connects to the `olm-api` service running on the Mac mini.
-   **Configuration**: `OllamaApiClient` is initialized with the `api_url` pointing to the `olm-api` endpoint (e.g., `http://<mac-mini-ip>:8000`).
-   **Use Case**: Essential for end-to-end testing before deployment to ensure the client interacts correctly with the deployed API server.

### Practical Factory Function Example

The following factory function, `get_olm_client`, demonstrates how to switch between the mock client, Pattern A, and Pattern B using environment variables.

```python
import os
from sdk.olm_api_client import (
    OllamaApiClient,
    MockOllamaApiClient,
    OllamaClientProtocol,
)

# Default URL for a local Ollama instance (Pattern A)
LOCAL_OLLAMA_URL = "http://localhost:11434"

def get_olm_client() -> OllamaClientProtocol:
    """
    Factory function to get the appropriate Ollama client based on the environment.

    - If `APP_ENV` is 'test', it returns a `MockOllamaApiClient` for unit testing.
    - If `OLM_API_ENDPOINT` is set, it connects to the specified API server (Pattern B).
    - Otherwise, it defaults to a local Ollama instance (Pattern A).
    """
    # Use mock client for unit tests
    if os.getenv("APP_ENV") == "test":
        print("INFO: Using MockOllamaApiClient for testing.")
        return MockOllamaApiClient(token_delay=0)

    # Use real client for development and production
    api_url = os.getenv("OLM_API_ENDPOINT")

    if api_url:
        # Pattern B: Connect to the remote olm-api server
        print(f"INFO: Connecting to remote olm-api server: {api_url}")
        return OllamaApiClient(api_url=api_url)
    else:
        # Pattern A: Connect to a local Ollama server by default
        print(f"INFO: Connecting to local Ollama server: {LOCAL_OLLAMA_URL}")
        return OllamaApiClient(api_url=LOCAL_OLLAMA_URL)

# --- How to Use ---

# In your application, call the factory to get the client
async def main():
    my_client: OllamaClientProtocol = get_olm_client()
    response = await my_client.gen_batch(prompt="Tell me a joke.")
    print(response)

# To run with Pattern A (Local Development):
# (No environment variables needed, connects to http://localhost:11434)
# > python your_app.py

# To run with Pattern B (Integrated Testing):
# > OLM_API_ENDPOINT="http://<mac-mini-ip>:8000" python your_app.py

# To run with Mock Client (Unit Testing):
# > APP_ENV="test" python your_app.py
```
