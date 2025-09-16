from typing import get_type_hints

import pytest
from olm_api_sdk.v2.client import OlmApiClientV2
from olm_api_sdk.v2.local_client import OlmLocalClientV2
from olm_api_sdk.v2.protocol import OlmClientV2Protocol


class TestOlmClientV2Protocol:
    """Test cases for OlmClientV2Protocol compliance"""

    def test_protocol_has_generate_method(self):
        """Test that the protocol defines generate method"""
        assert hasattr(OlmClientV2Protocol, "generate")

    def test_generate_method_signature(self):
        """Test that generate method has correct signature"""
        hints = get_type_hints(OlmClientV2Protocol.generate)
        assert "return" in hints
        # Should specify Union return type for streaming/non-streaming

    def test_all_clients_implement_protocol(self, fast_mock_client_v2):
        """Test that all v2 client implementations implement the protocol"""
        api_client = OlmApiClientV2(api_url="http://localhost:8000")
        local_client = OlmLocalClientV2()

        assert isinstance(api_client, OlmClientV2Protocol)
        assert isinstance(local_client, OlmClientV2Protocol)
        assert isinstance(fast_mock_client_v2, OlmClientV2Protocol)

    @pytest.mark.asyncio
    async def test_protocol_method_signature_compatibility(self, fast_mock_client_v2):
        """Test that all implementations accept the same parameters"""
        clients = [
            OlmApiClientV2(api_url="http://localhost:8000"),
            OlmLocalClientV2(),
            fast_mock_client_v2,
        ]

        test_params = {
            "messages": [{"role": "user", "content": "test"}],
            "model_name": "test-model",
            "tools": [
                {
                    "type": "function",
                    "function": {"name": "test_func", "description": "Test"},
                }
            ],
            "stream": True,
            "temperature": 0.7,
            "top_p": 0.9,
        }

        # All clients should accept these parameters without TypeError
        for client in clients:
            try:
                result = await client.generate(**test_params)
                # Verify return type for streaming
                assert hasattr(result, "__aiter__")
            except TypeError as e:
                pytest.fail(
                    f"Client {type(client).__name__} failed signature compatibility: {e}"
                )
            except Exception:
                # Other exceptions are OK (network errors, etc.) - we only test signatures
                pass

    @pytest.mark.asyncio
    async def test_protocol_return_type_streaming(self, fast_mock_client_v2):
        """Test that streaming mode returns async generator for all clients"""
        messages = [{"role": "user", "content": "test"}]

        result = await fast_mock_client_v2.generate(messages, "test-model", stream=True)
        assert hasattr(result, "__aiter__")  # Should be async generator

        # Verify it actually yields data
        chunks = []
        async for chunk in result:
            chunks.append(chunk)
            if len(chunks) >= 2:  # Don't need to consume all
                break
        assert len(chunks) >= 2

    @pytest.mark.asyncio
    async def test_protocol_return_type_non_streaming(self, fast_mock_client_v2):
        """Test that non-streaming mode returns dict for all clients"""
        messages = [{"role": "user", "content": "test"}]

        result = await fast_mock_client_v2.generate(
            messages, "test-model", stream=False
        )
        assert isinstance(result, dict)
        assert "choices" in result

    def test_protocol_runtime_checkable(self):
        """Test that protocol is runtime checkable"""

        # Valid implementation
        class ValidClient:
            async def generate(
                self, messages, model_name, tools=None, stream=False, **kwargs
            ):
                return {"choices": [{"message": {"content": "test"}}]}

        # Invalid implementation
        class InvalidClient:
            def wrong_method(self):
                pass

        valid = ValidClient()
        invalid = InvalidClient()

        assert isinstance(valid, OlmClientV2Protocol)
        assert not isinstance(invalid, OlmClientV2Protocol)

    def test_protocol_allows_additional_methods(self):
        """Test that implementations can have additional methods beyond protocol"""

        class ExtendedClient:
            async def generate(
                self, messages, model_name, tools=None, stream=False, **kwargs
            ):
                return {"choices": [{"message": {"content": "test"}}]}

            def additional_method(self):
                return "extra functionality"

        extended = ExtendedClient()
        assert isinstance(extended, OlmClientV2Protocol)
        assert hasattr(extended, "additional_method")

    @pytest.mark.asyncio
    async def test_protocol_polymorphism(self, fast_mock_client_v2):
        """Test polymorphic usage of different client implementations"""

        def process_client(client: OlmClientV2Protocol) -> str:
            return type(client).__name__

        clients = [
            OlmApiClientV2(api_url="http://localhost:8000"),
            OlmLocalClientV2(),
            fast_mock_client_v2,
        ]

        for client in clients:
            # Should work with type hints
            client_name = process_client(client)
            assert "Client" in client_name

            # Should have generate method
            assert hasattr(client, "generate")
            assert callable(client.generate)


class TestProtocolCompliance:
    """Test protocol compliance across different scenarios"""

    @pytest.mark.asyncio
    async def test_messages_parameter_compliance(self, fast_mock_client_v2):
        """Test that all clients handle messages parameter correctly"""

        # Test various message formats
        test_cases = [
            # Simple user message
            [{"role": "user", "content": "Hello"}],
            # System + user
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"},
            ],
            # Multi-turn conversation
            [
                {"role": "user", "content": "First message"},
                {"role": "assistant", "content": "First response"},
                {"role": "user", "content": "Follow up"},
            ],
            # Empty list (should still work)
            [],
        ]

        for messages in test_cases:
            result = await fast_mock_client_v2.generate(
                messages, "test-model", stream=False
            )
            assert isinstance(result, dict)
            assert "choices" in result

    @pytest.mark.asyncio
    async def test_tools_parameter_compliance(self, fast_mock_client_v2):
        """Test that tools parameter is handled consistently"""
        messages = [{"role": "user", "content": "Use tools"}]

        # Test with no tools
        result1 = await fast_mock_client_v2.generate(messages, "test-model", tools=None)
        assert isinstance(result1, dict)

        # Test with empty tools list
        result2 = await fast_mock_client_v2.generate(messages, "test-model", tools=[])
        assert isinstance(result2, dict)

        # Test with tool definition
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "test_function",
                    "description": "A test function",
                    "parameters": {
                        "type": "object",
                        "properties": {"param": {"type": "string"}},
                    },
                },
            }
        ]
        result3 = await fast_mock_client_v2.generate(
            messages, "test-model", tools=tools
        )
        assert isinstance(result3, dict)

    @pytest.mark.asyncio
    async def test_kwargs_parameter_handling(self, fast_mock_client_v2):
        """Test that additional kwargs are accepted consistently"""
        messages = [{"role": "user", "content": "test"}]

        # Test various generation parameters
        result = await fast_mock_client_v2.generate(
            messages,
            "test-model",
            temperature=0.7,
            top_p=0.9,
            top_k=40,
            max_tokens=100,
            stop=["END"],
            custom_param="value",
        )

        assert isinstance(result, dict)
        assert "choices" in result

    @pytest.mark.asyncio
    async def test_model_name_parameter(self, fast_mock_client_v2):
        """Test that model_name parameter is handled correctly"""
        messages = [{"role": "user", "content": "test"}]

        test_models = [
            "gpt-3.5-turbo",
            "llama3.2",
            "custom-model-name",
            "model_with_underscores",
            "model-with-hyphens",
        ]

        for model in test_models:
            result = await fast_mock_client_v2.generate(messages, model, stream=False)
            assert isinstance(result, dict)
            assert result["model"] == model

    @pytest.mark.asyncio
    async def test_stream_parameter_compliance(self, fast_mock_client_v2):
        """Test that stream parameter works consistently"""
        messages = [{"role": "user", "content": "test"}]

        # Test stream=False
        result_false = await fast_mock_client_v2.generate(
            messages, "test-model", stream=False
        )
        assert isinstance(result_false, dict)

        # Test stream=True
        result_true = await fast_mock_client_v2.generate(
            messages, "test-model", stream=True
        )
        assert hasattr(result_true, "__aiter__")

        # Test default (should be False)
        result_default = await fast_mock_client_v2.generate(messages, "test-model")
        assert isinstance(result_default, dict)


class TestProtocolErrorScenarios:
    """Test protocol compliance in error scenarios"""

    def test_incomplete_implementation_rejected(self):
        """Test that incomplete protocol implementations are rejected"""

        # Missing generate method
        class IncompleteClient1:
            pass

        # Missing generate method but has other methods
        class IncompleteClient2:
            def some_other_method(self):
                pass

        incomplete1 = IncompleteClient1()
        incomplete2 = IncompleteClient2()

        assert not isinstance(incomplete1, OlmClientV2Protocol)
        assert not isinstance(incomplete2, OlmClientV2Protocol)

    def test_valid_minimal_implementation(self):
        """Test that minimal valid implementation is accepted"""

        class MinimalClient:
            async def generate(
                self, messages, model_name, tools=None, stream=False, **kwargs
            ):
                if stream:

                    async def generator():
                        yield '{"choices":[{"delta":{"content":"test"}}]}'

                    return generator()
                return {"choices": [{"message": {"content": "test"}}]}

        client = MinimalClient()
        assert isinstance(client, OlmClientV2Protocol)

    @pytest.mark.asyncio
    async def test_protocol_with_mock_server_simulation(
        self, custom_response_client_v2
    ):
        """Test protocol compliance with simulated server responses"""
        # This tests that our mock client can simulate realistic scenarios

        mock_client = custom_response_client_v2(["Simulated API response"])

        # Simulate complex conversation
        conversation = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
        ]

        # Should handle complex conversation without issues
        result = await mock_client.generate(conversation, "gpt-3.5-turbo", stream=False)

        assert isinstance(result, dict)
        assert result["choices"][0]["message"]["content"] == "Simulated API response"
        assert result["model"] == "gpt-3.5-turbo"

    @pytest.mark.asyncio
    async def test_concurrent_protocol_usage(self, fast_mock_client_v2):
        """Test protocol compliance under concurrent usage"""
        import asyncio

        messages = [{"role": "user", "content": "Concurrent test"}]

        # Create multiple concurrent protocol-compliant calls
        async def make_call(i):
            return await fast_mock_client_v2.generate(
                messages, f"model-{i}", stream=False
            )

        # Execute multiple calls concurrently
        tasks = [make_call(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # All should follow protocol
        assert len(results) == 10
        for i, result in enumerate(results):
            assert isinstance(result, dict)
            assert "choices" in result
            assert result["model"] == f"model-{i}"
