# API v2 - Chat Completions Proxy

API v2 is a next-generation interface providing advanced features for Ollama. It supports conversation history, system prompts, Tool Calling, and more.

## Endpoints

### POST /api/v2/chat/completions

Chat Completions endpoint. Supports conversation based on message arrays, Tool Calling, and advanced generation parameters.

#### Request

```json
{
  "model": "llama3.2",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello, how are you?"}
  ],
  "stream": false,
  "temperature": 0.7,
  "top_p": 0.9,
  "max_tokens": 100
}
```

**Parameters:**
- `model` (string, required): Ollama model name to use
- `messages` (array, required): Array of messages
  - `role`: "system", "user", "assistant", "tool"
  - `content`: Message content
  - `name`: Sender name (optional)
  - `tool_calls`: Tool call information (for assistant messages)
  - `tool_call_id`: Tool call ID (for tool messages)
  - `images`: Array of base64-encoded images (for vision models, optional)
- `tools` (array, optional): Array of available tool definitions
- `tool_choice` (string/object, optional): Control tool selection
- `stream` (boolean, optional): Enable streaming response
- `temperature` (float, optional): Controls randomness (0.0-2.0)
- `top_p` (float, optional): Nucleus sampling (0.0-1.0)
- `top_k` (int, optional): Top-K sampling
- `max_tokens` (int, optional): Maximum number of tokens
- `stop` (string/array, optional): Stop sequence
- `options` (object, optional): Other Ollama-specific options

#### Vision Example (Image Input)

```json
{
  "model": "gemma3:270m",
  "messages": [
    {
      "role": "user",
      "content": "What do you see in this image?",
      "images": ["iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="]
    }
  ],
  "stream": false
}
```

**Note**: Images should be base64-encoded. Vision support depends on the model capabilities. Non-vision models will ignore the images field.

#### Tool Calling Example

```json
{
  "model": "llama3.2",
  "messages": [
    {"role": "user", "content": "What's the weather like today?"}
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Get current weather information",
        "parameters": {
          "type": "object",
          "properties": {
            "location": {"type": "string", "description": "City name"}
          },
          "required": ["location"]
        }
      }
    }
  ]
}
```

#### Response (Non-Streaming)

```json
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
        "content": "I'm doing well, thank you! How can I help you today?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 15,
    "completion_tokens": 12,
    "total_tokens": 27
  }
}
```

#### Tool Calling Response

```json
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
        "content": null,
        "tool_calls": [
          {
            "id": "call_abc123",
            "type": "function",
            "function": {
              "name": "get_weather",
              "arguments": "{\"location\": \"Tokyo\"}"
            }
          }
        ]
      },
      "finish_reason": "tool_calls"
    }
  ]
}
```

#### Response (Streaming)

Server-Sent Events (SSE) format:

```
Server-Sent Events (SSE) format:

```text
data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1699000000,"model":"llama3.2","choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1699000000,"model":"llama3.2","choices":[{"index":0,"delta":{"content":"I'm"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1699000000,"model":"llama3.2","choices":[{"index":0,"delta":{"content":" doing"},"finish_reason":null}]}
```

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1699000000,"model":"llama3.2","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

## Features

- **Conversation History Management**: Supports multi-turn conversations via the messages field
- **System Prompt**: Controls model behavior with the system role
- **Vision Support**: Process images with vision-capable models (base64-encoded)
- **Tool Calling**: Supports calling external functions and APIs
- **Advanced Parameters**: Fine control with temperature, top_p, top_k, etc.
- **Chat Completion API**: Standard chat completion interface

## Implementation Files

- **Router**: `router.py` - Endpoint definitions
- **Schemas**: `schemas/` directory - Pydantic models organized by domain
  - `message.py`: Message-related schemas
  - `tool.py`: Tool-related schemas
  - `request.py`: Request schemas
  - `response.py`: Response schemas
- **Service**: `../v1/services/ollama_service.py` - Shared business logic (v2 compatible)

## Migration Guide

Migration from v1 to v2:

```python
# v1 (old)
response = await client.gen_batch("Hello", "llama3.2")

# v2 (new)
response = await client.chat_completion(
    messages=[{"role": "user", "content": "Hello"}],
    model_name="llama3.2"
)
```

The v2 API is completely independent from v1 and does not affect existing v1 behavior.