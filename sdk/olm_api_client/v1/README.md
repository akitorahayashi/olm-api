# Olm API Client v1

A Python client for the Olm API v1, for simple prompt-based text generation.

## Installation

```bash
pip install httpx
```

## Usage

Initialize the client with the API server's URL.

```python
import asyncio
from olm_api_client.v1 import OlmApiClientV1

client = OlmApiClientV1("http://localhost:8000")
```

### Standard Generation

```python
async def generate_text():
    result = await client.generate(
        prompt="Hello, how are you?", 
        model_name="llama3.2",
        think=True # Optional: to get the model's reasoning
    )
    print("Content:", result.content)
    print("Thinking:", result.think) # Contains reasoning if think=True

asyncio.run(generate_text())
```

### Streaming Generation

Set `stream=True` to get an async generator.

```python
async def stream_text():
    async for chunk in await client.generate(
        prompt="Tell me a story", 
        model_name="llama3.2", 
        stream=True
    ):
        print(chunk.content, end="", flush=True)

asyncio.run(stream_text())
```

## API Reference

### `OlmApiClientV1`

#### `__init__(api_url: str)`
- `api_url`: Base URL of the Olm API server.

#### `async def generate(prompt: str, model_name: str, stream: bool = False, think: Optional[bool] = None)`
- **Returns**: 
    - If `stream=False`: A `GenerateResponse` object with `content`, `think`, and `response` attributes.
    - If `stream=True`: An `AsyncGenerator` that yields `GenerateResponse` chunks.
