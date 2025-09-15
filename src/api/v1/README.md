# API v1 - Simple Proxy

This document specifies the v1 API, a simple endpoint for prompt-based text generation. It is maintained for backward compatibility.

## Endpoint: `POST /api/v1/generate`

### Request

```json
{
  "prompt": "Hello, how are you?",
  "model_name": "llama3.2",
  "stream": false,
  "think": false
}
```

**Parameters:**
- `prompt` (string, **required**): The input text for the model.
- `model_name` (string, **required**): The name of the Ollama model to use.
- `stream` (boolean, optional, default: `false`): If `true`, the response will be a stream of Server-Sent Events (SSE).
- `think` (boolean, optional, default: `false`): If `true`, enables thinking mode for compatible models, which may include a reasoning process in the response.

### Response (Non-Streaming)

The response is a single JSON object.

```json
{
  "think": "Let me consider this greeting...",
  "content": "I'm doing well, thank you!",
  "response": "<think>Let me consider this greeting...</think>I'm doing well, thank you!"
}
```

**Fields:**
- `think` (string | null): The model's reasoning process, extracted from `<think>` tags. `null` if not present.
- `content` (string): The final response content, with `<think>` tags removed.
- `response` (string): The raw response from the model, including any tags.

### Response (Streaming)

If `stream: true`, the server returns a stream of JSON objects in SSE format. Each object represents a token or a small part of the response.

```text
data: {"think": "...", "content": "I'm", "response": "..."}
data: {"think": "...", "content": "I'm doing", "response": "..."}
...
```
