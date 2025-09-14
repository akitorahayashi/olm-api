# Olm API Client v1

A Python client library for the Olm API v1, providing simple prompt-based text generation with streaming support.

## Features

- **Simple Prompt Interface**: Send a prompt string and get a text response
- **Streaming Support**: Real-time text generation with async generators
- **Type Safety**: Full typing support with protocols
- **Error Handling**: Comprehensive error handling with proper exception types
- **Legacy Compatible**: Designed for backward compatibility with existing systems

## Installation

```bash
pip install httpx  # Required dependency
```

## Quick Start

### Basic Usage

```python
import asyncio
from olm_api_client.v1 import OlmApiClientV1

async def main():
    client = OlmApiClientV1("http://localhost:8000")

    # Generate text without streaming
    response = await client.generate("Hello, how are you?", "llama3.2")
    print(response)

# Run the async function
asyncio.run(main())
```

### Streaming Generation

```python
import asyncio
from olm_api_client.v1 import OlmApiClientV1

async def main():
    client = OlmApiClientV1("http://localhost:8000")

    # Generate text with streaming
    async for chunk in await client.generate("Tell me a story", "llama3.2", stream=True):
        print(chunk, end="", flush=True)
    print()  # New line after streaming

asyncio.run(main())
```

## API Reference

### OlmApiClientV1

The main client class for interacting with the Olm API v1.

#### Constructor

```python
OlmApiClientV1(api_url: str)
```

**Parameters:**
- `api_url` (str): The base URL of the Olm API server

**Example:**
```python
client = OlmApiClientV1("http://localhost:8000")
```

#### Methods

##### generate

```python
async def generate(prompt: str, model_name: str, stream: bool = False) -> Union[str, AsyncGenerator[str, None]]
```

Generate text response with optional streaming support.

**Parameters:**
- `prompt` (str): The prompt to send to the model
- `model_name` (str): The name of the Olm model to use
- `stream` (bool): Whether to stream the response (default: False)

**Returns:**
- `str`: Complete generated text response (if stream=False)
- `AsyncGenerator[str, None]`: Async generator yielding text chunks (if stream=True)

**Examples:**

```python
# Generate without streaming
response = await client.generate("What is Python?", "llama3.2")
print(response)

# Generate with streaming
async for chunk in await client.generate("Count to 10", "llama3.2", stream=True):
    print(chunk, end="")
```

## Protocol Support

The client implements the `OlmClientV1Protocol` for type checking and testing.

```python
from olm_api_client.v1 import OlmClientV1Protocol

def process_with_client(client: OlmClientV1Protocol):
    # Your code here - works with any v1-compatible client
    pass
```

## Error Handling

The client raises standard `httpx` exceptions for network errors:

```python
import httpx
from olm_api_client.v1 import OlmApiClientV1

async def main():
    client = OlmApiClientV1("http://localhost:8000")

    try:
        response = await client.generate("Hello", "llama3.2")
        print(response)
    except httpx.RequestError as e:
        print(f"Network error: {e}")
    except httpx.HTTPStatusError as e:
        print(f"HTTP error: {e.response.status_code}")
```

## Use Cases

The v1 client is ideal for:

- **Legacy Systems**: Maintaining compatibility with existing prompt-based workflows
- **Simple Applications**: When you only need basic prompt-to-text functionality
- **Quick Prototyping**: Fast setup for simple text generation needs
- **Lightweight Integration**: Minimal dependencies and simple API

## Limitations

- **No Conversation History**: Each request is independent
- **No System Prompts**: Cannot set model behavior instructions
- **No Tool Calling**: Advanced function calling not supported
- **Limited Parameters**: Basic generation parameters only

## Migration to v2

For advanced features like conversation history, system prompts, and tool calling, consider migrating to the v2 client:

```python
# v1 (simple)
from olm_api_client.v1 import OlmApiClientV1
client = OlmApiClientV1("http://localhost:8000")
response = await client.generate("Hello", "llama3.2")

# v2 (advanced)
from olm_api_client.v2 import OlmApiClientV2
client = OlmApiClientV2("http://localhost:8000")
messages = [{"role": "user", "content": "Hello"}]
response = await client.generate(messages, "llama3.2")
content = response["choices"][0]["message"]["content"]
```

## Testing

The client is fully testable using the protocol:

```python
from olm_api_client.v1 import OlmClientV1Protocol

class MockClient:
    async def generate(self, prompt: str, model_name: str, stream: bool = False):
        if stream:
            async def mock_generator():
                yield "Mock "
                yield "response"
            return mock_generator()
        else:
            return "Mock response"

# Type checking will pass
mock_client: OlmClientV1Protocol = MockClient()
```