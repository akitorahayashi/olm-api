# Ollama API Client SDK

This SDK provides a unified interface for interacting with Ollama, supporting both local development and remote API communication.

## Core Idea: A Unified Interface

The SDK is built around the `OllamaClientProtocol`, which defines a common set of methods (`gen_stream`, `gen_batch`). This allows your application to remain completely unaware of whether it's communicating with a local `ollama serve` instance or a remote `olm-api` server.

A central factory function, `create_client()`, handles the logic of providing the correct client based on a single environment variable.

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

---

## How to Use: The `create_client` Factory

The **recommended** way to use this SDK is through the `create_client()` factory. This function reads the `OLM_CLIENT_MODE` environment variable to determine which client to return.

### Step 1: Using the Factory in Your Application

```python
# In your application's main logic
from sdk.olm_api_client import create_client, OllamaClientProtocol

async def run_my_app():
    # The factory provides the correct client instance automatically.
    client: OllamaClientProtocol = create_client()

    # Your code always uses the same interface, regardless of the client.
    response = await client.gen_batch(
        prompt="Why is the sky blue?",
        model_name="qwen3:0.6b"
    )
    print(response)
```

### Step 2: Configuring the Client Mode

You can switch between modes by setting environment variables before running your application.

**A) Local Development Mode**

Connects to a local `ollama serve` instance.

```sh
# No extra variables needed if ollama serve is at http://localhost:11434
export OLM_CLIENT_MODE=local
python your_app.py
```

**B) Remote API Mode**

Connects to the deployed `olm-api` server.

```sh
export OLM_CLIENT_MODE=remote
export OLM_API_ENDPOINT="http://<your-mac-mini-ip>:8000"
python your_app.py
```
*Note: `remote` is the default mode if `OLM_CLIENT_MODE` is not set.*

**C) Mock Mode (for Unit Tests)**

Uses the in-memory mock client.

```sh
export OLM_CLIENT_MODE=mock
python -m pytest
```

---

## Direct Initialization (Advanced)

While the `create_client` factory is recommended, you can also initialize clients directly if you need more control.

```python
from sdk.olm_api_client import OllamaApiClient, OllamaLocalClient

# Explicitly create a remote client
remote_client = OllamaApiClient(api_url="http://<remote-ip>:8000")

# Explicitly create a local client
local_client = OllamaLocalClient(host="http://localhost:11434")
```
