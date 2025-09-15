# Olm API Client v2

A Python client library for the Olm API v2, providing chat completion functionality with advanced features including conversation history, tool calling, and fine-grained generation control.

## Features

- **Chat Completion API**: Standard chat completion interface
- **Conversation History**: Multi-turn conversations with message arrays
- **System Prompts**: Control model behavior with system instructions
- **Vision Support**: Process images with vision-capable models
- **Tool Calling**: Function calling and external API integration
- **Advanced Parameters**: Fine control over generation (temperature, top_p, etc.)
- **Streaming Support**: Real-time text generation with Server-Sent Events
- **Type Safety**: Full typing support with protocols
- **Error Handling**: Comprehensive error handling with proper exception types

## Quick Start

### Basic Chat Completion

```python
import asyncio
from olm_api_client.v2 import OlmApiClientV2

async def main():
    client = OlmApiClientV2("http://localhost:8000")

    messages = [
        {"role": "user", "content": "Hello, how are you?"}
    ]

    response = await client.generate(messages, "llama3.2")
    content = response["choices"][0]["message"]["content"]
    print(content)

asyncio.run(main())
```

### Conversation with System Prompt

```python
import asyncio
from olm_api_client.v2 import OlmApiClientV2

async def main():
    client = OlmApiClientV2("http://localhost:8000")

    messages = [
        {"role": "system", "content": "You are a helpful Python tutor."},
        {"role": "user", "content": "What are Python decorators?"}
    ]

    response = await client.generate(
        messages,
        "llama3.2",
        temperature=0.7,
        max_tokens=200
    )

    print(response["choices"][0]["message"]["content"])

asyncio.run(main())
```

### Multi-turn Conversation

```python
import asyncio
from olm_api_client.v2 import OlmApiClientV2

async def main():
    client = OlmApiClientV2("http://localhost:8000")

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is machine learning?"},
        {"role": "assistant", "content": "Machine learning is a subset of AI..."},
        {"role": "user", "content": "Can you give me a simple example?"}
    ]

    response = await client.generate(messages, "llama3.2")
    print(response["choices"][0]["message"]["content"])

asyncio.run(main())
```

### Streaming Chat

```python
import asyncio
from olm_api_client.v2 import OlmApiClientV2

async def main():
    client = OlmApiClientV2("http://localhost:8000")

    messages = [
        {"role": "user", "content": "Write a short poem about Python programming"}
    ]

    async for chunk in await client.generate(
        messages, "llama3.2", stream=True
    ):
        if "choices" in chunk and chunk["choices"]:
            delta = chunk["choices"][0].get("delta", {})
            if "content" in delta:
                print(delta["content"], end="", flush=True)
    print()

asyncio.run(main())
```

### Vision (Image Processing)

```python
import asyncio
import base64
from olm_api_client.v2 import OlmApiClientV2

async def main():
    client = OlmApiClientV2("http://localhost:8000")

    # Load and encode image
    with open("image.png", "rb") as f:
        image_data = base64.b64encode(f.read()).decode()

    messages = [
        {
            "role": "user",
            "content": "What do you see in this image?",
            "images": [image_data]
        }
    ]

    response = await client.generate(messages, "gemma3:270m")
    print(response["choices"][0]["message"]["content"])

asyncio.run(main())
```

**Note**: Vision support requires vision-capable models like `gemma3`. Non-vision models will ignore the images field.

### Tool Calling

```python
import asyncio
import json
from olm_api_client.v2 import OlmApiClientV2

async def main():
    client = OlmApiClientV2("http://localhost:8000")

    # Define available tools
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get current weather information for a city",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city name"
                        },
                        "unit": {
                            "type": "string",
                            "enum": ["celsius", "fahrenheit"],
                            "description": "Temperature unit"
                        }
                    },
                    "required": ["location"]
                }
            }
        }
    ]

    messages = [
        {"role": "user", "content": "What's the weather like in Tokyo?"}
    ]

    response = await client.generate(
        messages, "llama3.2", tools=tools
    )

    choice = response["choices"][0]
    if choice["message"].get("tool_calls"):
        # Model wants to call a function
        tool_call = choice["message"]["tool_calls"][0]
        function_name = tool_call["function"]["name"]
        arguments = json.loads(tool_call["function"]["arguments"])
        print(f"Model wants to call {function_name} with {arguments}")
    else:
        # Regular text response
        print(choice["message"]["content"])

asyncio.run(main())
```

## API Reference

### OlmApiClientV2

The main client class for interacting with the Ollama API v2.

#### Constructor

```python
OlmApiClientV2(api_url: str)
```

**Parameters:**
- `api_url` (str): The base URL of the Olm API server

#### Methods

##### generate

```python
async def generate(
    messages: List[Dict[str, Any]],
    model_name: str,
    tools: Optional[List[Dict[str, Any]]] = None,
    stream: bool = False,
    **kwargs
) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]
```

Generate chat completion with standard format.

**Parameters:**
- `messages` (List[Dict]): Array of message objects
- `model_name` (str): Name of the Olm model to use
- `tools` (Optional[List[Dict]]): Array of available tool definitions
- `stream` (bool): Whether to stream the response
- `**kwargs`: Additional parameters (temperature, top_p, max_tokens, etc.)

**Message Format:**
```python
{
    "role": "user|assistant|system|tool",
    "content": "Message content",
    "name": "Optional sender name",
    "tool_calls": "Optional tool calls (for assistant messages)",
    "tool_call_id": "Optional tool call ID (for tool messages)",
    "images": ["base64_encoded_image1", "base64_encoded_image2"]  # Optional for vision
}
```

**Tool Format:**
```python
{
    "type": "function",
    "function": {
        "name": "function_name",
        "description": "Function description",
        "parameters": {
            "type": "object",
            "properties": {
                "param_name": {
                    "type": "string|number|boolean|array|object",
                    "description": "Parameter description"
                }
            },
            "required": ["param1", "param2"]
        }
    }
}
```

**Generation Parameters:**
- `temperature` (float): Controls randomness (0.0-2.0)
- `top_p` (float): Nucleus sampling (0.0-1.0)
- `top_k` (int): Top-K sampling
- `max_tokens` (int): Maximum tokens to generate
- `stop` (str|List[str]): Stop sequences
- `tool_choice` (str|Dict): Control tool selection

**Returns:**
- Non-streaming: `Dict[str, Any]` - Chat completion response object
- Streaming: `AsyncGenerator[Dict[str, Any], None]` - Async generator yielding JSON objects (dictionaries).

## Response Format

### Non-Streaming Response

```python
{
    "id": "chatcmpl-123456789",
    "object": "chat.completion",
    "created": 1699000000,
    "model": "llama3.2",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "Generated response text",
                "tool_calls": []  # If function calling was used
            },
            "finish_reason": "stop|length|tool_calls"
        }
    ],
    "usage": {
        "prompt_tokens": 15,
        "completion_tokens": 25,
        "total_tokens": 40
    }
}
```

### Streaming Response

Returns an async generator that yields JSON objects (dictionaries) as they are generated.

## Protocol Support

```python
from olm_api_client.v2 import OlmClientV2Protocol

def process_with_client(client: OlmClientV2Protocol):
    # Your code here - works with any v2-compatible client
    pass
```

## Error Handling

```python
import httpx
from olm_api_client.v2 import OlmApiClientV2

async def main():
    client = OlmApiClientV2("http://localhost:8000")

    try:
        messages = [{"role": "user", "content": "Hello"}]
        response = await client.generate(messages, "llama3.2")
        print(response["choices"][0]["message"]["content"])
    except httpx.RequestError as e:
        print(f"Network error: {e}")
    except httpx.HTTPStatusError as e:
        print(f"HTTP error: {e.response.status_code}")
```

## Chat Completion Format

The v2 client uses a standard chat completion format:

```python
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
]

response = await client.generate(
    messages,
    "llama3.2",
    temperature=0.7,
    max_tokens=100
)

content = response["choices"][0]["message"]["content"]
```

## Use Cases

The v2 client is ideal for:

- **Modern Applications**: Full-featured chat applications
- **Conversational AI**: Multi-turn conversations with context
- **Vision Applications**: Image analysis and multimodal interactions
- **Agent Systems**: Tool calling and function execution
- **API Integration**: Standard chat completion interface
- **Advanced Control**: Fine-grained generation parameter control

## Testing

```python
from olm_api_client.v2 import OlmClientV2Protocol

class MockClient:
    async def generate(self, messages, model_name, **kwargs):
        return {
            "choices": [{"message": {"role": "assistant", "content": "Mock"}}]
        }

# Type checking will pass
mock_client: OlmClientV2Protocol = MockClient()
```

## Migration from v1

```python
# v1 (old)
from olm_api_client.v1 import OlmApiClientV1
client = OlmApiClientV1("http://localhost:8000")
response = await client.generate("Hello", "llama3.2")

# v2 (new)
from olm_api_client.v2 import OlmApiClientV2
client = OlmApiClientV2("http://localhost:8000")
messages = [{"role": "user", "content": "Hello"}]
response = await client.generate(messages, "llama3.2")
content = response["choices"][0]["message"]["content"]
```