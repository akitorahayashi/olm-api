# Ollama API Client SDK

This SDK provides a unified interface for interacting with Ollama, supporting both local development and remote API communication.

## Core Idea: A Unified Interface

The SDK is built around the `OllamaClientProtocol`, which defines a common set of methods (`gen_stream`, `gen_batch`). This allows your application to remain completely unaware of whether it's communicating with a local `ollama serve` instance or a remote `olm-api` server.

## Client Implementations

1.  **`OllamaLocalClient`**:
    *   **Purpose**: For local development.
    *   **Mechanism**: Communicates directly with a local `ollama serve` instance using the official `ollama` Python library.
    *   **Benefit**: Fast, no network dependency, and ideal for rapid iteration on your own machine.

2.  **`OllamaApiClient`**:
    *   **Purpose**: For integrated testing or production use.
    *   **Mechanism**: Communicates with a remote `olm-api` server endpoint.
    *   **Benefit**: Allows you to test your application against the exact same API that will be used in production.

3.  **`MockOllamaApiClient`**:
    *   **Purpose**: For local unit testing.
    *   **Mechanism**: Simulates API responses in-memory without any network requests.
    *   **Benefit**: Fast, deterministic, and enables testing without a running backend.

    The `MockOllamaApiClient` is highly configurable for testing. You can specify responses in three ways:

    1.  **List of Strings (Default)**: Cycles through a list of predefined responses.
        ```python
        responses = ["Hello", "How are you?"]
        client = MockOllamaApiClient(responses=responses)
        ```

    2.  **Dictionary Mapping**: Maps specific prompts (or partial prompts) to responses. This is useful for testing specific conversational flows.
        Note: Matching tries exact match first, then the first substring match by insertion order. Matching is case-sensitive by default.
        ```python
        prompt_map = {
            "What is your name?": "I am a mock client.",
            "weather": "The weather is always sunny in mock-land."
        }
        client = MockOllamaApiClient(responses=prompt_map)

        # Exact match
        await client.gen_batch("What is your name?", "test-model")
        # -> "I am a mock client."

        # Partial match
        await client.gen_batch("How is the weather?", "test-model")
        # -> "The weather is always sunny in mock-land."
        ```

    3.  **Callable Function**: For the most complex scenarios, you can provide a function that generates a response dynamically based on the prompt and model name.
        ```python
        def my_response_generator(prompt: str, model_name: str) -> str:
            if "error" in prompt:
                return "An error occurred."
            return f"Response from {model_name} for '{prompt}'"

        client = MockOllamaApiClient(responses=my_response_generator)
        ```

---

## How to Use

### Direct Client Initialization

```python
from sdk.olm_api_client import OllamaApiClient, OllamaLocalClient, MockOllamaApiClient

# Remote API client
client = OllamaApiClient(api_url="http://<remote-ip>:8000")

# Local client
client = OllamaLocalClient(host="http://localhost:11434")  # host is optional

# Mock client for testing
client = MockOllamaApiClient()

# Use the client
import asyncio

async def main():
    response = await client.gen_batch(
        prompt="Why is the sky blue?",
        model_name="qwen3:0.6b"
    )
    print(response)

asyncio.run(main())
```

### Usage Examples

**A) Local Development**

```python
from sdk.olm_api_client import OllamaLocalClient

async def run_local():
    client = OllamaLocalClient()  # Defaults to http://localhost:11434
    
    response = await client.gen_batch(
        prompt="Explain Python asyncio",
        model_name="qwen3:0.6b"
    )
    print(response)
```

**B) Remote API**

```python
from sdk.olm_api_client import OllamaApiClient

async def run_remote():
    client = OllamaApiClient(api_url="http://your-server:8000")
    
    response = await client.gen_batch(
        prompt="What is machine learning?",
        model_name="qwen3:0.6b"
    )
    print(response)
```

**C) Mock Testing**

```python
from sdk.olm_api_client import MockOllamaApiClient

async def test_function():
    # Option A: Use specific responses
    client = MockOllamaApiClient(responses=["mock response"])
    response = await client.gen_batch(prompt="Test prompt", model_name="test-model")
    assert response == "mock response"

    # Option B: Test with default responses
    client = MockOllamaApiClient()
    response = await client.gen_batch(prompt="Test prompt", model_name="test-model")
    assert isinstance(response, str) and len(response) > 0
```
