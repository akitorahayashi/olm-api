# Olm API Client v1

Python SDK for simple text generation.

## Import Methods

```python
from olm_api_sdk.v1 import (
    OlmApiClientV1,
    OlmLocalClientV1,
    MockOlmClientV1,
    OlmClientV1Protocol
)
```

## Basic Usage

### Asynchronous Usage

```python
import asyncio
from olm_api_sdk.v1 import OlmApiClientV1

async def main():
    client = OlmApiClientV1("http://localhost:8000")

    # Basic text generation
    result = await client.generate(
        prompt="Hello, how are you?",
        model_name="llama3.2"
    )
    print(result["content"])

asyncio.run(main())
```

### Synchronous Usage

```python
from olm_api_sdk.v1 import OlmApiClientV1

client = OlmApiClientV1("http://localhost:8000")

# Basic text generation
result = client.generate(
    prompt="Hello, how are you?",
    model_name="llama3.2"
)
print(result["content"])
```

## Advanced Features

### Generation with Thinking Process

#### Asynchronous

```python
result = await client.generate(
    prompt="Solve this math problem",
    model_name="llama3.2",
    think=True  # Get thinking process
)
print("Answer:", result["content"])
print("Thinking:", result["think"])
```

#### Synchronous

```python
result = client.generate(
    prompt="Solve this math problem",
    model_name="llama3.2",
    think=True  # Get thinking process
)
print("Answer:", result["content"])
print("Thinking:", result["think"])
```

### Streaming Generation

#### Asynchronous

```python
async def stream_example():
    client = OlmApiClientV1("http://localhost:8000")

    async for chunk in await client.generate(
        prompt="Write a long story",
        model_name="llama3.2",
        stream=True
    ):
        print(chunk["content"], end="", flush=True)

asyncio.run(stream_example())
```

#### Synchronous

```python
client = OlmApiClientV1("http://localhost:8000")

for chunk in client.generate(
    prompt="Write a long story",
    model_name="llama3.2",
    stream=True
):
    print(chunk["content"], end="", flush=True)
```

## Mock Client for Testing

### Asynchronous Usage

```python
from olm_api_sdk.v1.mock_client import MockOlmClientV1

# Test with fixed responses (cycling through list)
client = MockOlmClientV1(responses=["Hello!", "I'm fine!"])

result = await client.generate(prompt="Greeting", model_name="test")
print(result["content"])  # "Hello!" or "I'm fine!"

# Test with mapped responses (dictionary)
client = MockOlmClientV1(responses={
    "Hello": "Hi there!",
    "How are you?": "I'm doing well, thank you!",
    "Goodbye": "Farewell!"
})

result1 = await client.generate(prompt="Hello", model_name="test")
print(result1["content"])  # "Hi there!"

result2 = await client.generate(prompt="How are you?", model_name="test")
print(result2["content"])  # "I'm doing well, thank you!"
```

### Synchronous Usage

```python
from olm_api_sdk.v1.mock_client import MockOlmClientV1

# Test with fixed responses (cycling through list)
client = MockOlmClientV1(responses=["Hello!", "I'm fine!"])

result = client.generate(prompt="Greeting", model_name="test")
print(result["content"])  # "Hello!" or "I'm fine!"

# Test with mapped responses (dictionary)
client = MockOlmClientV1(responses={
    "Hello": "Hi there!",
    "How are you?": "I'm doing well, thank you!",
    "Goodbye": "Farewell!"
})

result1 = client.generate(prompt="Hello", model_name="test")
print(result1["content"])  # "Hi there!"

result2 = client.generate(prompt="How are you?", model_name="test")
print(result2["content"])  # "I'm doing well, thank you!"
```

## API Specification

### `generate(prompt, model_name, stream=False, think=None)`
- `prompt`: Input text
- `model_name`: Model name to use
- `stream`: True for streaming generation
- `think`: True to include thinking process

**Returns:**
- `content`: Generated text
- `think`: Thinking process (when think=True)
- `full_response`: Raw response