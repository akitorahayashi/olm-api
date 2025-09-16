# Olm API Client v2

Python SDK supporting chat, vision, and tool calling.

## Basic Usage

```python
import asyncio
from olm_api_sdk.v2 import OlmApiClientV2

async def main():
    client = OlmApiClientV2("http://localhost:8000")

    messages = [{"role": "user", "content": "Hello!"}]
    response = await client.generate(messages=messages, model_name="llama3.2")

    print(response["choices"][0]["message"]["content"])

asyncio.run(main())
```

## Practical Examples

### Chatbot

```python
async def chatbot():
    client = OlmApiClientV2("http://localhost:8000")

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Teach me Python basics"}
    ]

    response = await client.generate(
        messages=messages,
        model_name="llama3.2",
        temperature=0.7
    )

    print(response["choices"][0]["message"]["content"])

asyncio.run(chatbot())
```

### Streaming Response

```python
async def streaming_chat():
    client = OlmApiClientV2("http://localhost:8000")

    messages = [{"role": "user", "content": "Write a long explanation"}]

    async for chunk in await client.generate(
        messages=messages,
        model_name="llama3.2",
        stream=True
    ):
        delta = chunk.get("choices", [{}])[0].get("delta", {})
        if "content" in delta:
            print(delta["content"], end="", flush=True)

asyncio.run(streaming_chat())
```

### Vision (Image Recognition)

```python
import base64

async def analyze_image():
    client = OlmApiClientV2("http://localhost:8000")

    # Encode image to base64
    with open("image.jpg", "rb") as f:
        image_data = base64.b64encode(f.read()).decode()

    messages = [{
        "role": "user",
        "content": "Describe this image",
        "images": [image_data]
    }]

    response = await client.generate(messages=messages, model_name="llama3.2")
    print(response["choices"][0]["message"]["content"])

asyncio.run(analyze_image())
```

### Tool Calling (Function Execution)

```python
async def weather_bot():
    client = OlmApiClientV2("http://localhost:8000")

    # Define available tools
    tools = [{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a city",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"]
            }
        }
    }]

    messages = [{"role": "user", "content": "What's the weather in Tokyo?"}]

    response = await client.generate(
        messages=messages,
        model_name="llama3.2",
        tools=tools
    )

    message = response["choices"][0]["message"]

    if message.get("tool_calls"):
        # Handle tool calls
        tool_call = message["tool_calls"][0]
        function_name = tool_call["function"]["name"]
        args = json.loads(tool_call["function"]["arguments"])

        print(f"Function call: {function_name}({args})")
        # Execute the actual function and return results
    else:
        print(message["content"])

asyncio.run(weather_bot())
```

## Client Types

### HTTP Client (Recommended)

```python
from olm_api_sdk.v2 import OlmApiClientV2
client = OlmApiClientV2("http://localhost:8000")
```

### Local Ollama Client

```python
from olm_api_sdk.v2 import OlmLocalClientV2
client = OlmLocalClientV2()  # Connect directly to local Ollama
```

## Mock Client for Testing

```python
from olm_api_sdk.v2.mock_client import MockOlmClientV2

# Test with fixed responses (cycling through list)
client = MockOlmClientV2(responses=["Hello!", "How are you?"])

messages = [{"role": "user", "content": "Greeting"}]
result = await client.generate(messages=messages, model_name="test")
print(result["choices"][0]["message"]["content"])  # "Hello!" or "How are you?"

# Test with mapped responses (dictionary)
# Key is matched against the last message's content
client = MockOlmClientV2(responses={
    "Hello": "Hi there!",
    "How are you?": "I'm doing well, thank you!",
    "Goodbye": "Farewell!"
})

result1 = await client.generate(
    messages=[{"role": "user", "content": "Hello"}],
    model_name="test"
)
print(result1["choices"][0]["message"]["content"])  # "Hi there!"

result2 = await client.generate(
    messages=[{"role": "user", "content": "How are you?"}],
    model_name="test"
)
print(result2["choices"][0]["message"]["content"])  # "I'm doing well, thank you!"
```

## API Specification

### `generate(messages, model_name, tools=None, stream=False, **kwargs)`
- `messages`: List of messages
- `model_name`: Model name
- `tools`: Tool definitions (optional)
- `stream`: True for streaming
- `**kwargs`: Additional parameters like temperature

**Returns:**
- `choices[0].message.content`: Generated text
- `choices[0].message.tool_calls`: Tool calls (if any)