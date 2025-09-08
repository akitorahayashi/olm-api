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
