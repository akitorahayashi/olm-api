# API v2 - Chat Proxy

This document specifies the v2 API, which provides advanced chat features including conversation history, vision capabilities, and tool calling.

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
  "temperature": 0.7,
  "max_tokens": 100
}
```

**Key Parameters:**
- `model` (string, **required**): The model name.
- `messages` (array, **required**): An array of message objects representing the conversation history.
- `stream` (boolean, optional, default: `false`): Enable streaming response.
- `think` (boolean, optional): Enable thinking mode.
- `tools` (array, optional): A list of available tools the model can call.
- `tool_choice` (string | object, optional): Controls how the model uses tools.
- Other parameters like `temperature`, `top_p`, `max_tokens`, `stop` are also available.

### Message Object

```json
{
  "role": "system | user | assistant | tool",
  "content": "Message text",
  "images": ["base64_encoded_image"], 
  "tool_calls": [{}],             
  "tool_call_id": "call_abc123"   
}
```
- `images` (array of strings, optional): For vision models, a list of base64-encoded images.
- `tool_calls` (array, optional): For assistant messages, a list of tool calls requested by the model.
- `tool_call_id` (string, optional): For tool messages, the ID of the tool call this message is a result for.

### Vision (Image Input)

To use vision capabilities, include the `images` field in a `user` message.

```json
{
  "model": "gemma3:270m",
  "messages": [
    {
      "role": "user",
      "content": "What do you see in this image?",
      "images": ["iVBORw0KGgoAAAAN...RU5ErkJggg=="]
    }
  ]
}
```

### Tool Calling

1.  **Define tools** in the `tools` array of the request.
2.  The model may respond with a `tool_calls` object in the assistant's message.

**Tool Definition (`tools` array):**
```json
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
```

### Response (Non-Streaming)

Returns a standard chat completion object.

```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "model": "llama3.2",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "I'm doing well, thank you!",
        "think": "The user is asking how I am...",
        "response": "<think>...</think>I'm doing well, thank you!",
        "tool_calls": null
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {"prompt_tokens": 15, "completion_tokens": 12, "total_tokens": 27}
}
```

- If the model decides to call a tool, `finish_reason` will be `tool_calls` and `message.tool_calls` will contain the details.

### Response (Streaming)

If `stream: true`, the server returns a stream of `chat.completion.chunk` objects in SSE format. The stream is terminated by `[DONE]`.

```text
data: {"id":"...","choices":[{"delta":{"role":"assistant"}}]}
data: {"id":"...","choices":[{"delta":{"content":"I'm"}}]}
...
data: [DONE]
```