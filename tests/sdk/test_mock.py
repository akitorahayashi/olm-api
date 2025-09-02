import re

import pytest

from sdk.olm_api_client.mock import MockOllamaApiClient


@pytest.mark.asyncio
async def test_mock_client_generates_streaming_response():
    """MockOllamaApiClientがストリーミング応答を正しく生成することをテストする"""
    # Arrange
    client = MockOllamaApiClient()
    prompt = "hello"
    expected_start = "<think>"
    expected_end_text = (
        "Hello! How are you today? I'm here to help with anything you need!"
    )

    # Act
    response_chunks = [chunk async for chunk in client.generate(prompt)]
    full_response = "".join(response_chunks).strip()

    # Assert
    assert len(response_chunks) > 0, "ストリーミング応答が生成されませんでした"
    assert full_response.startswith(
        expected_start
    ), "応答が<think>タグで始まっていません"

    # Clean strings for robust comparison by removing all whitespace
    cleaned_response = re.sub(r"\s+", "", full_response)
    cleaned_expected = re.sub(r"\s+", "", expected_end_text)

    assert cleaned_expected in cleaned_response, "期待される応答内容が含まれていません"
    assert "<think>" in full_response
    assert "</think>" in full_response


@pytest.mark.asyncio
async def test_mock_client_uses_cycling_responses():
    """カスタム応答がない場合に、モッククライアントが応答リストを順に利用することをテストする"""
    # Arrange
    client = MockOllamaApiClient()
    first_prompt = "some random prompt"
    second_prompt = "another random prompt"
    expected_first_text = "Hello! How can I help you today?"
    expected_second_text = (
        "That's an interesting question. Could you tell me more about it?"
    )

    # Act
    first_response_chunks = [chunk async for chunk in client.generate(first_prompt)]
    second_response_chunks = [chunk async for chunk in client.generate(second_prompt)]

    first_full_response = "".join(first_response_chunks)
    second_full_response = "".join(second_response_chunks)

    # Assert
    cleaned_first_response = re.sub(r"\s+", "", first_full_response)
    cleaned_expected_first = re.sub(r"\s+", "", expected_first_text)
    assert (
        cleaned_expected_first in cleaned_first_response
    ), "最初のデフォルト応答が含まれていません"

    cleaned_second_response = re.sub(r"\s+", "", second_full_response)
    cleaned_expected_second = re.sub(r"\s+", "", expected_second_text)
    assert (
        cleaned_expected_second in cleaned_second_response
    ), "2番目のデフォルト応答が含まれていません"

    assert (
        cleaned_first_response != cleaned_second_response
    ), "異なるプロンプトに対して同じ応答が返されました"
