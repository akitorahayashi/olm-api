# Olm API Client v2

A Python client for the Olm API v2, supporting chat, vision, and tool calling.

## Usage

Initialize the client with the API server's URL. The client will connect to the `/api/v2/chat` endpoint.

```python
import asyncio
from olm_api_client.v2 import OlmApiClientV2

client = OlmApiClientV2("http://localhost:8000")
```

### Chat

```python
async def chat():
    messages = [
        {"role": "system", "content": "You are a helpful Python tutor."},
        {"role": "user", "content": "What are Python decorators?"}
    ]

    response = await client.generate(
        messages=messages, 
        model_name="llama3.2",
        temperature=0.7
    )
    print(response["choices"][0]["message"]["content"])

asyncio.run(chat())
```

### Streaming Chat

Set `stream=True` to get an async generator that yields response chunks.

```python
async def stream_chat():
    messages = [{"role": "user", "content": "Write a short poem."}]
    async for chunk in await client.generate(
        messages=messages, 
        model_name="llama3.2", 
        stream=True
    ):
        delta = chunk.get("choices", [{}])[0].get("delta", {})
        if "content" in delta:
            print(delta["content"], end="", flush=True)

asyncio.run(stream_chat())
```

### Vision (Image Input)

Provide a base64-encoded image in the `images` field of a user message.

```python
import base64

async def analyze_image():
    with open("image.png", "rb") as f:
        image_data = base64.b64encode(f.read()).decode()

    messages = [{
        "role": "user",
        "content": "What do you see in this image?",
        "images": [image_data]
    }]

    response = await client.generate(messages, "gemma3:270m")
    print(response["choices"][0]["message"]["content"])

asyncio.run(analyze_image())
```

### Tool Calling

1.  Define tools and pass them to the `generate` method.
2.  Check the response for `tool_calls`.

```python
import json

async def use_tools():
    tools = [{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a city",
            "parameters": {
                "type": "object",
                "properties": {"location": {"type": "string"}},
                "required": ["location"]
            }
        }
    }]
    messages = [{"role": "user", "content": "What's the weather in Tokyo?"}]

    response = await client.generate(messages, "llama3.2", tools=tools)
    message = response["choices"][0]["message"]

    if message.get("tool_calls"):
        tool_call = message["tool_calls"][0]
        function_name = tool_call["function"]["name"]
        arguments = json.loads(tool_call["function"]["arguments"])
        print(f"Function call: {function_name}({arguments})")
        # Here you would execute the function and send back the result
    else:
        print(message["content"])

asyncio.run(use_tools())
```

## API Reference

### `OlmApiClientV2`

#### `__init__(api_url: str)`
- `api_url`: Base URL of the Olm API server.

#### `async def generate(messages, model_name, tools=None, stream=False, **kwargs)`
- `messages`: List of message dictionaries.
- `model_name`: Name of the model.
- `tools`: Optional list of tool definitions.
- `stream`: Set to `True` for a streaming response.
- `**kwargs`: Additional parameters like `temperature`, `think`, etc.
- **Returns**:
    - If `stream=False`: A dictionary representing the chat object.
    - If `stream=True`: An `AsyncGenerator` yielding response chunk dictionaries.