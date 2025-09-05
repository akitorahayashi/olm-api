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
Optionally, you can pass `think=True` (or `False`) to control thinking mode when supported by the server.

#### Streaming (`gen_stream`)

```python
import asyncio
from sdk.olm_api_client import OllamaApiClient

client = OllamaApiClient(api_url="http://localhost:8000")

async def stream_example():
    response_stream = client.gen_stream(
        prompt="Why is the sky blue?",
        model="qwen3:0.6b",
        think=True,
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
        model="qwen3:0.6b",
        think=False,
    )
    print(response)

# asyncio.run(batch_example())
```

---

## `MockOllamaApiClient` (Mock Client)

Use this for testing. It simulates API responses locally and deterministically.

### Initialization

The `token_delay` parameter controls the simulated streaming speed. A delay of `0` is useful for fast-running tests.

```python
from sdk.olm_api_client import MockOllamaApiClient

# For fast tests, no delay
fast_client = MockOllamaApiClient(token_delay=0)

# For realistic streaming simulation
realistic_client = MockOllamaApiClient(token_delay=0.01)
```

### Behavior

* **Deterministic Responses** : The mock client returns consistent, predefined answers for common prompts (e.g., "hello", "test"). For other prompts, it cycles through a list of generic responses.
* **Simulated Thinking** : Responses include `<think>` tags to mimic the behavior of a real model's thought process.
* **No Network Required** : All operations are performed in-memory.

### Usage

The interface is identical to `OllamaApiClient`.

```python
import asyncio
from sdk.olm_api_client import MockOllamaApiClient

# Use the fast client for a quick test
client = MockOllamaApiClient(token_delay=0)

async def mock_example():
    # Batch response is instant
    response = await client.gen_batch(prompt="hello there")
    print(response)
    # Example Output: <think>...</think> Hello! 😊 How are you today?...

    # Stream response is also instant with token_delay=0
    async for chunk in client.gen_stream(prompt="some other prompt"):
        print(chunk, end="")

# asyncio.run(mock_example())
```

---

## Recommended Usage Pattern (Dependency Injection)

For robust and testable code, use the `OllamaClientProtocol` for type hinting. This allows you to inject either the real or mock client depending on the environment.

```python
from sdk.olm_api_client import OllamaApiClient, MockOllamaApiClient, OllamaClientProtocol
import os

def get_client() -> OllamaClientProtocol:
    """Factory function to get the appropriate client."""
    if os.getenv("DEBUG") == "true":
        return MockOllamaApiClient(token_delay=0)
    else:
        api_url = os.getenv("OLM_API_ENDPOINT")
        if not api_url:
            raise ValueError("OLM_API_ENDPOINT is not set for production")
        return OllamaApiClient(api_url=api_url)

# In your application, use the factory
async def main():
    my_client: OllamaClientProtocol = get_client()
    response = await my_client.gen_batch(prompt="Tell me a joke.")
    print(response)

# To run in debug/test mode:
# DEBUG=true python your_app.py

# To run in production:
# OLM_API_ENDPOINT="http://real-api-server" python your_app.py
```
