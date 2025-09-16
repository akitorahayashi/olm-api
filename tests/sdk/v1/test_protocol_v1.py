from typing import get_type_hints
from unittest.mock import AsyncMock

import pytest
from olm_api_sdk.v1.client import OlmApiClientV1
from olm_api_sdk.v1.mock_client import MockOlmClientV1
from olm_api_sdk.v1.protocol import OlmClientV1Protocol


class TestOlmClientV1Protocol:
    """Test cases for OlmClientV1Protocol"""

    def test_protocol_has_generate_method(self):
        """Test that the protocol defines generate method"""
        assert hasattr(OlmClientV1Protocol, "generate")

    def test_generate_method_signature(self):
        """Test that generate method has correct signature"""
        # Get type hints from the protocol
        hints = get_type_hints(OlmClientV1Protocol.generate)

        # Check return type
        assert "return" in hints
        # The return type should be Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]

    def test_real_client_implements_protocol(self):
        """Test that OlmApiClientV1 implements the protocol"""
        client = OlmApiClientV1(api_url="http://localhost:11434")
        assert isinstance(client, OlmClientV1Protocol)

    def test_mock_client_implements_protocol(self):
        """Test that MockOlmClientV1 implements the protocol"""
        client = MockOlmClientV1()
        assert isinstance(client, OlmClientV1Protocol)

    def test_protocol_compatibility_with_streaming(self):
        """Test protocol compatibility with streaming calls"""

        # Create a mock that follows the protocol
        class ProtocolCompliantMock:
            async def generate(
                self, prompt: str, model_name: str, stream: bool = False, think=None
            ):
                if stream:
                    return self._async_gen()
                else:
                    return {
                        "think": "",
                        "content": "batch response",
                        "response": "batch response",
                    }

            async def _async_gen(self):
                yield {"think": "", "content": "chunk1", "response": "chunk1"}
                yield {"think": "", "content": "chunk2", "response": "chunk1chunk2"}

        mock = ProtocolCompliantMock()
        assert isinstance(mock, OlmClientV1Protocol)

    def test_protocol_compatibility_with_non_streaming(self):
        """Test protocol compatibility with non-streaming calls"""

        class ProtocolCompliantMock:
            async def generate(
                self, prompt: str, model_name: str, stream: bool = False, think=None
            ):
                if stream:
                    return self._async_gen()
                else:
                    return {
                        "think": "",
                        "content": "complete response",
                        "response": "complete response",
                    }

            async def _async_gen(self):
                yield {"think": "", "content": "chunk", "response": "chunk"}

        mock = ProtocolCompliantMock()
        assert isinstance(mock, OlmClientV1Protocol)


class TestProtocolUsage:
    """Test using the protocol in practice"""

    @pytest.mark.asyncio
    async def test_can_use_protocol_for_type_checking(self):
        """Test that protocol can be used for type checking"""

        def process_client(client: OlmClientV1Protocol) -> bool:
            return hasattr(client, "generate")

        real_client = OlmApiClientV1(api_url="http://localhost:11434")
        mock_client = MockOlmClientV1()

        assert process_client(real_client) is True
        assert process_client(mock_client) is True

    @pytest.mark.asyncio
    async def test_protocol_allows_polymorphic_usage(self):
        """Test polymorphic usage of different client implementations"""
        clients = [
            OlmApiClientV1(api_url="http://localhost:11434"),
            MockOlmClientV1(token_delay=0),
        ]

        for client in clients:
            assert isinstance(client, OlmClientV1Protocol)

            # Test that both support the same interface
            assert callable(client.generate)

            # Both should support streaming and non-streaming
            # (We can't easily test actual calls without mocking, but interface is consistent)

    def test_protocol_enforces_method_existence(self):
        """Test that protocol enforces required methods"""

        class IncompleteClient:
            pass

        incomplete = IncompleteClient()
        assert not isinstance(incomplete, OlmClientV1Protocol)

        class PartiallyCompleteClient:
            def some_other_method(self):
                pass

            # Missing generate

        partial = PartiallyCompleteClient()
        assert not isinstance(partial, OlmClientV1Protocol)

    def test_protocol_allows_additional_methods(self):
        """Test that implementations can have additional methods"""

        class ExtendedClient:
            async def generate(
                self, prompt: str, model_name: str, stream: bool = False, think=None
            ):
                if stream:
                    return AsyncMock()
                return {
                    "think": "",
                    "content": "batch response",
                    "response": "batch response",
                }

            def additional_method(self):
                return "extra functionality"

        extended = ExtendedClient()
        assert isinstance(extended, OlmClientV1Protocol)
        assert hasattr(extended, "additional_method")

    @pytest.mark.asyncio
    async def test_protocol_method_signature_compatibility(self):
        """Test that protocol method signatures are compatible across implementations"""
        real_client = OlmApiClientV1(api_url="http://localhost:11434")
        mock_client = MockOlmClientV1(token_delay=0)

        # Both should accept the same parameters for generate
        test_params = {
            "prompt": "test prompt",
            "model_name": "test-model",
            "stream": True,
        }

        # Should not raise TypeError for parameter mismatch
        try:
            real_result = await real_client.generate(**test_params)
            mock_result = await mock_client.generate(**test_params)

            # Both should return async generator when stream=True
            assert hasattr(real_result, "__aiter__")
            assert hasattr(mock_result, "__aiter__")

        except TypeError as e:
            pytest.fail(f"Parameter signature mismatch: {e}")

    @pytest.mark.asyncio
    async def test_protocol_return_type_compatibility(self):
        """Test return type compatibility between implementations"""
        mock_client = MockOlmClientV1(token_delay=0)

        # Test streaming mode
        stream_result = await mock_client.generate("test", "test-model", stream=True)
        assert hasattr(stream_result, "__aiter__")  # Should be async generator

        # Test batch mode
        batch_result = await mock_client.generate("test", "test-model", stream=False)
        assert isinstance(batch_result, dict)  # Should be dict
        assert "think" in batch_result
        assert "content" in batch_result
        assert "response" in batch_result
