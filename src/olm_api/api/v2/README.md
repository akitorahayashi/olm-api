# API v2 - Chat Completions

Advanced chat completion API with conversation history, vision, and tool calling support.

## Endpoint: `POST /api/v2/chat`

### Request

```json
{
  "model": "llama3.2",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello, how are you?"}
  ],
  "stream": false,
  "temperature": 0.7
}
```

**Parameters:**
- `model` (string, **required**): Model name (also accepts `model_name`)
- `messages` (array, **required**): Array of message objects
- `stream` (boolean, optional, default: `false`): Enable streaming response
- `tools` (array, optional): List of available tools
- `tool_choice` (string | object, optional): Tool selection mode
- `temperature` (number, optional): Sampling temperature (0.0-1.0)
- `top_p` (number, optional): Nucleus sampling parameter
- `top_k` (number, optional): Top-k sampling parameter
- `max_tokens` (number, optional): Maximum tokens to generate
- `stop` (string | array, optional): Stop sequences
- `think` (boolean, optional): Enable thinking mode

### Message Format

```json
{
  "role": "system | user | assistant | tool",
  "content": "Message content",
  "images": ["base64_encoded_image"],
  "tool_calls": [{"id": "call_123", "type": "function", "function": {...}}],
  "tool_call_id": "call_123"
}
```

### Tool Definition

```json
{
  "type": "function",
  "function": {
    "name": "get_weather",
    "description": "Get weather information",
    "parameters": {
      "type": "object",
      "properties": {
        "location": {"type": "string", "description": "City name"}
      },
      "required": ["location"]
    }
  }
}
```

### Response (Non-Streaming)

```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "llama3.2",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "I'm doing well, thank you!",
      "think": "The user is asking how I am...",
      "full_response": "<think>...</think>I'm doing well, thank you!",
      "tool_calls": null
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 15,
    "completion_tokens": 12,
    "total_tokens": 27
  }
}
```

### Response (Streaming)

Returns Server-Sent Events with completion chunks:

```text
data: {"id":"chatcmpl-123","object":"chat.completion.chunk","choices":[{"delta":{"role":"assistant"}}]}
data: {"id":"chatcmpl-123","object":"chat.completion.chunk","choices":[{"delta":{"content":"I'm","think":"...","full_response":"..."}}]}
...
data: [DONE]
```

### Vision Support

Include base64-encoded images in user messages:

```json
{
  "model": "gemma3:270m",
  "messages": [{
    "role": "user",
    "content": "What's in this image?",
    "images": ["iVBORw0KGgoAAAANSUhEUgAA..."]
  }]
}
```

### Error Responses

- `400`: Invalid request format or parameters
- `502`: Ollama API error
- `503`: Unable to connect to Ollama
- `500`: Internal server error

### Example Usage

```bash
curl -X POST "http://localhost:8000/api/v2/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ],
    "temperature": 0.7
  }'
```

### Tool Calling Example

```bash
curl -X POST "http://localhost:8000/api/v2/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2",
    "messages": [
      {"role": "user", "content": "What'\''s the weather in Tokyo?"}
    ],
    "tools": [{
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Get weather information",
        "parameters": {
          "type": "object",
          "properties": {"location": {"type": "string"}},
          "required": ["location"]
        }
      }
    }]
  }'
```