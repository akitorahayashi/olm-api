from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient
from starlette import status

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


async def test_chat_completions_basic(
    unit_test_client: AsyncClient, mock_ollama_service_v2: MagicMock
):
    """
    Test that the /chat/completions endpoint works with basic messages.
    """
    # Arrange
    messages = [{"role": "user", "content": "Hello!"}]
    model = "qwen3:0.6b"

    mock_response = {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1640995200,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Hello! How can I help you today?",
                    "tool_calls": None,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    }

    mock_ollama_service_v2.chat_completion.return_value = mock_response

    # Act
    response = await unit_test_client.post(
        "/api/v2/chat/completions",
        json={"model": model, "messages": messages, "stream": False},
    )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert (
        response_data["choices"][0]["message"]["content"]
        == "Hello! How can I help you today?"
    )
    mock_ollama_service_v2.chat_completion.assert_called_once()


async def test_chat_completions_with_tools(
    unit_test_client: AsyncClient, mock_ollama_service_v2: MagicMock
):
    """
    Test that the /chat/completions endpoint works with tool calling.
    """
    # Arrange
    messages = [{"role": "user", "content": "Think about this problem"}]
    model = "qwen3:0.6b"
    tools = [
        {
            "type": "function",
            "function": {
                "name": "save_thought",
                "description": "Save a thought for later reference",
                "parameters": {
                    "type": "object",
                    "properties": {"thought_content": {"type": "string"}},
                },
            },
        }
    ]

    mock_response = {
        "id": "chatcmpl-456",
        "object": "chat.completion",
        "created": 1640995200,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_123",
                            "type": "function",
                            "function": {
                                "name": "save_thought",
                                "arguments": '{"thought_content": "I need to analyze this carefully..."}',
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 15, "completion_tokens": 10, "total_tokens": 25},
    }

    mock_ollama_service_v2.chat_completion.return_value = mock_response

    # Act
    response = await unit_test_client.post(
        "/api/v2/chat/completions",
        json={"model": model, "messages": messages, "tools": tools, "stream": False},
    )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["choices"][0]["message"]["tool_calls"] is not None
    assert (
        response_data["choices"][0]["message"]["tool_calls"][0]["function"]["name"]
        == "save_thought"
    )
    mock_ollama_service_v2.chat_completion.assert_called_once()


async def test_chat_completions_missing_model(
    unit_test_client: AsyncClient,
    mock_ollama_service_v2: MagicMock,
):
    """
    Test that a 422 error is returned if model is not provided.
    """
    # Act
    response = await unit_test_client.post(
        "/api/v2/chat/completions",
        json={"messages": [{"role": "user", "content": "test"}]},
    )

    # Assert
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    mock_ollama_service_v2.chat_completion.assert_not_called()


async def test_chat_completions_empty_messages(
    unit_test_client: AsyncClient,
    mock_ollama_service_v2: MagicMock,
):
    """
    Test that a 422 error is returned if messages are empty.
    """
    # Act
    response = await unit_test_client.post(
        "/api/v2/chat/completions", json={"model": "qwen3:0.6b", "messages": []}
    )

    # Assert
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    mock_ollama_service_v2.chat_completion.assert_not_called()
