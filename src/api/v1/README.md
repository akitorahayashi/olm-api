# API v1 - Simple Proxy

API v1 is an endpoint for conventional simple prompt execution. It is maintained for backward compatibility and will not be changed in the future.

## Endpoints

### POST /api/v1/generate

Text generation endpoint. Receives a simple prompt string and returns a response from the Ollama model.

#### Request

```json
{
  "prompt": "Hello, how are you?",
  "model_name": "llama3.2",
  "stream": false
}
```

**Parameters:**
- `prompt` (string, required): Prompt string to send to the model
- `model_name` (string, required): Ollama model name to use
- `stream` (boolean, optional): Enable streaming response (default: false)

#### Response (Non-Streaming)

```json
{
  "response": "I'm doing well, thank you! How can I help you today?"
}
```

#### Response (Streaming)

Server-Sent Events (SSE) format:

```
data: {"response": "I'm"}
data: {"response": " doing"}
data: {"response": " well,"}
data: {"response": " thank you!"}
```

### POST /api/v1/logs

Log retrieval endpoint (see logs.py for details)

## Use Cases

- Maintaining compatibility with legacy systems
- Use cases that only require simple prompt execution
- Compatibility with existing client code

## Limitations

- Only supports a single prompt string
- No conversation history management
- Cannot specify system prompt
- Tool Calling not supported
- Limited advanced generation parameters

## Implementation Files

- **Router**: `routers/generate.py` - Endpoint definitions
- **Service**: `services/ollama_service.py` - Business logic
- **Models**: Pydantic model definitions inline

For more advanced features, use `/api/v2/chat/completions` in the v2 API.