import asyncio
import os
import time
from typing import List

import httpx
import pytest

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


async def make_api_request(client: httpx.AsyncClient, url: str, payload: dict, request_number: int) -> dict:
    """
    Make a single API request and return the response data.
    Raises exception if the request fails.
    """
    try:
        response = await client.post(url, json=payload)
        if response.status_code != 200:
            raise Exception(f"Request {request_number} failed with status {response.status_code}: {response.text}")
        
        response_data = response.json()
        if "response" not in response_data:
            raise Exception(f"Request {request_number} returned invalid response format: {response_data}")
        
        return response_data
    except Exception as e:
        raise Exception(f"Request {request_number} failed: {str(e)}")


async def run_concurrent_requests(num_requests: int) -> float:
    """
    Run concurrent requests and return the elapsed time.
    Raises exception if any request fails, including the request number.
    """
    host_port = os.getenv("HOST_PORT", "8000")
    model_name = os.getenv("BUILT_IN_OLLAMA_MODEL")
    assert model_name, "BUILT_IN_OLLAMA_MODEL environment variable must be set"

    generate_url = f"http://localhost:{host_port}/api/v1/generate"
    request_payload = {
        "prompt": "What is 2+2?",
        "stream": False,
    }

    start_time = time.time()
    
    async with httpx.AsyncClient(timeout=120) as client:
        # Create tasks for concurrent requests
        tasks = [
            make_api_request(client, generate_url, request_payload, i+1)
            for i in range(num_requests)
        ]
        
        # Wait for all requests to complete
        results = await asyncio.gather(*tasks)
    
    elapsed_time = time.time() - start_time
    
    # Validate all responses
    for i, result in enumerate(results):
        if not isinstance(result.get("response"), str) or len(result.get("response", "")) == 0:
            raise Exception(f"Request {i+1} returned invalid response content: {result}")
    
    return elapsed_time


@pytest.mark.asyncio
async def test_concurrency_performance():
    """Test concurrent requests with 1 and 5 requests sequentially"""
    test_cases = [1, 5]  # 10, 50  # テスト実装段階のため最初は少数に限定
    
    print("\n🚀 パフォーマンステスト開始")
    print("=" * 50)
    
    for i, num_requests in enumerate(test_cases):
        test_name = f"test_concurrent_requests_{num_requests}"
        print(f"\n🧪 テスト {i+1}/{len(test_cases)}: {num_requests}回の同時リクエスト")
        
        try:
            elapsed = await run_concurrent_requests(num_requests)
            print(f"✅ {num_requests}回の同時リクエスト: {elapsed:.2f}秒")
        except Exception as e:
            print(f"❌ テスト関数 '{test_name}' で失敗しました")
            print(f"❌ 例外の詳細: {str(e)}")
            pytest.fail(f"テスト関数 '{test_name}' で失敗: {str(e)}")
    
    print("\n🎉 すべてのパフォーマンステストが成功しました！")
    print("=" * 50)