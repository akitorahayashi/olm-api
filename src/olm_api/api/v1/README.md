# API v1 - Simple Text Generation

Simple prompt-based text generation endpoint for backward compatibility.

## Endpoint: `POST /api/v1/chat`

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
- `prompt` (string, **required**): Input text for generation
- `model_name` (string, **required**): Ollama model name
- `stream` (boolean, optional, default: `false`): Enable streaming response
- `think` (boolean, optional): Enable thinking mode for compatible models

### Response (Non-Streaming)

```json
{
  "think": "Let me consider this greeting...",
  "content": "I'm doing well, thank you!",
  "response": "<think>Let me consider this greeting...</think>I'm doing well, thank you!"
}
```

**Fields:**
- `think` (string | null): Model's reasoning process from `<think>` tags
- `content` (string): Final response content with `<think>` tags removed
- `response` (string): Raw response including all tags

### Response (Streaming)

Returns Server-Sent Events with JSON chunks:

```text
data: {"think": "...", "content": "I'm", "response": "..."}
data: {"think": "...", "content": "I'm doing", "response": "..."}
...
```

### Error Responses

- `400`: Invalid request parameters
- `502`: Ollama API error
- `500`: Internal server error

### Example Usage

```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain Python decorators",
    "model_name": "llama3.2",
    "think": true
  }'
```
