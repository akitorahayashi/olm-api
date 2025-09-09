import os
from typing import get_type_hints
from unittest.mock import AsyncMock, patch

import pytest

from sdk.olm_api_client.client import OllamaApiClient
from sdk.olm_api_client.mock import MockOllamaApiClient
from sdk.olm_api_client.protocol import OllamaClientProtocol


class TestOllamaClientProtocol:
    """Test cases for OllamaClientProtocol"""

    def test_protocol_has_gen_stream_method(self):
        """Test that the protocol defines gen_stream method"""
        assert hasattr(OllamaClientProtocol, "gen_stream")

    def test_protocol_has_gen_batch_method(self):
        """Test that the protocol defines gen_batch method"""
        assert hasattr(OllamaClientProtocol, "gen_batch")

    def test_gen_stream_method_signature(self):
        """Test that gen_stream method has correct signature"""
        # Get type hints from the protocol
        hints = get_type_hints(OllamaClientProtocol.gen_stream)

        # Check return type
        assert "return" in hints
        # The return type should be AsyncGenerator[str, None]
        return_type = hints["return"]
        assert hasattr(return_type, "__origin__")  # AsyncGenerator type

    def test_gen_batch_method_signature(self):
        """Test that gen_batch method has correct signature"""
        # Get type hints from the protocol
        hints = get_type_hints(OllamaClientProtocol.gen_batch)

        # Check return type
        assert "return" in hints
        # The return type should be str
        return_type = hints["return"]
        assert return_type is str

    def test_real_client_implements_protocol(self):
        """Test that OllamaApiClient implements the protocol"""
        client = OllamaApiClient(api_url="http://localhost:11434")
        assert isinstance(client, OllamaClientProtocol)

    def test_mock_client_implements_protocol(self):
        """Test that MockOllamaApiClient implements the protocol"""
        client = MockOllamaApiClient()
        assert isinstance(client, OllamaClientProtocol)

    def test_protocol_compatibility_with_streaming(self):
        """Test protocol compatibility with streaming calls"""

        # Create a mock that follows the protocol
        class ProtocolCompliantMock:
            def gen_stream(self, prompt: str, model_name: str):
                return self._async_gen()

            async def gen_batch(self, prompt: str, model_name: str):
                return "batch response"

            async def _async_gen(self):
                yield "chunk1"
                yield "chunk2"

        mock = ProtocolCompliantMock()
        assert isinstance(mock, OllamaClientProtocol)

    def test_protocol_compatibility_with_non_streaming(self):
        """Test protocol compatibility with non-streaming calls"""

        class ProtocolCompliantMock:
            def gen_stream(self, prompt: str, model_name: str):
                return self._async_gen()

            async def gen_batch(self, prompt: str, model_name: str):
                return "complete response"

            async def _async_gen(self):
                yield "chunk"

        mock = ProtocolCompliantMock()
        assert isinstance(mock, OllamaClientProtocol)


class TestProtocolUsage:
    """Test using the protocol in practice"""

    @pytest.mark.asyncio
    async def test_can_use_protocol_for_type_checking(self):
        """Test that protocol can be used for type checking"""

        def process_client(client: OllamaClientProtocol) -> bool:
            return hasattr(client, "gen_stream") and hasattr(client, "gen_batch")

        real_client = OllamaApiClient(api_url="http://localhost:11434")
        mock_client = MockOllamaApiClient()

        assert process_client(real_client) is True
        assert process_client(mock_client) is True

    @pytest.mark.asyncio
    async def test_protocol_allows_polymorphic_usage(self):
        """Test polymorphic usage of different client implementations"""
        clients = [
            OllamaApiClient(api_url="http://localhost:11434"),
            MockOllamaApiClient(token_delay=0),
        ]

        for client in clients:
            assert isinstance(client, OllamaClientProtocol)

            # Test that both support the same interface
            assert callable(client.gen_stream)
            assert callable(client.gen_batch)

            # Both should support streaming and non-streaming
            # (We can't easily test actual calls without mocking, but interface is consistent)

    def test_protocol_enforces_method_existence(self):
        """Test that protocol enforces required methods"""

        class IncompleteClient:
            pass

        incomplete = IncompleteClient()
        assert not isinstance(incomplete, OllamaClientProtocol)

        class PartiallyCompleteClient:
            def gen_stream(self, prompt: str, model_name: str):
                pass

            # Missing gen_batch

        partial = PartiallyCompleteClient()
        assert not isinstance(partial, OllamaClientProtocol)

    def test_protocol_allows_additional_methods(self):
        """Test that implementations can have additional methods"""

        class ExtendedClient:
            def gen_stream(self, prompt: str, model_name: str):
                return AsyncMock()

            async def gen_batch(self, prompt: str, model_name: str):
                return "batch response"

            def additional_method(self):
                return "extra functionality"

        extended = ExtendedClient()
        assert isinstance(extended, OllamaClientProtocol)
        assert hasattr(extended, "additional_method")

    @pytest.mark.asyncio
    async def test_protocol_method_signature_compatibility(self):
        """Test that protocol method signatures are compatible across implementations"""
        real_client = OllamaApiClient(api_url="http://localhost:11434")
        mock_client = MockOllamaApiClient(token_delay=0)

        # Both should accept the same parameters for gen_stream
        test_params = {"prompt": "test prompt", "model_name": "test-model"}

        # Should not raise TypeError for parameter mismatch
        try:
            real_result = real_client.gen_stream(**test_params)
            mock_result = mock_client.gen_stream(**test_params)

            # Both should return async generator
            assert hasattr(real_result, "__aiter__")
            assert hasattr(mock_result, "__aiter__")

        except TypeError as e:
            pytest.fail(f"Parameter signature mismatch: {e}")

    @pytest.mark.asyncio
    async def test_protocol_return_type_compatibility(self):
        """Test return type compatibility between implementations"""
        mock_client = MockOllamaApiClient(token_delay=0)

        # Test streaming mode
        stream_result = mock_client.gen_stream("test", "test-model")
        assert hasattr(stream_result, "__aiter__")  # Should be async generator

        # Test batch mode
        batch_result = await mock_client.gen_batch("test", "test-model")
        assert isinstance(batch_result, str)  # Should be string
