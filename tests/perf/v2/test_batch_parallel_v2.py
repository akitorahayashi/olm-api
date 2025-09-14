import asyncio
import json
import os
import time

import httpx
import pytest

from tests.conftest import get_model_name, load_prompt

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


async def make_api_request(
    client: httpx.AsyncClient, url: str, payload: dict, request_number: int
) -> tuple[dict, float]:
    """
    Make a single API request and return the response data and elapsed time.
    Raises exception if the request fails.
    """
    start_time = time.time()
    try:
        response = await client.post(url, json=payload)
        elapsed = time.time() - start_time

        if response.status_code != 200:
            raise Exception(
                f"Request {request_number} failed with status {response.status_code}: {response.text}"
            )

        response_data = response.json()

        # Log the JSON response
        print(
            f"\nRequest {request_number}: {elapsed:.2f}s - Response JSON: {json.dumps(response_data, ensure_ascii=False)}"
        )

        if "choices" not in response_data or not response_data["choices"]:
            raise Exception(
                f"Request {request_number} returned invalid response format: {response_data}"
            )

        return response_data, elapsed
    except Exception as e:
        elapsed = time.time() - start_time
        raise Exception(
            f"Request {request_number} failed after {elapsed:.2f}s: {str(e)}"
        )


async def run_parallel_requests_with_timing(
    num_requests: int,
) -> tuple[float, list[float]]:
    """
    Run parallel requests and return total elapsed time and individual request times.
    """
    host_port = os.getenv("TEST_PORT", "8002")
    model_name = get_model_name()

    chat_url = f"http://localhost:{host_port}/api/v2/chat/completions"
    request_payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": load_prompt()}],
        "stream": False,
    }

    start_time = time.time()
    request_times = []

    async def request_with_timing(request_num):
        try:
            async with httpx.AsyncClient(timeout=600) as client:
                result, individual_time = await make_api_request(
                    client, chat_url, request_payload, request_num
                )

            request_times.append(individual_time)

            # Validate response
            if (
                not result.get("choices")
                or not isinstance(
                    result["choices"][0].get("message", {}).get("content"), str
                )
                or len(result["choices"][0]["message"]["content"]) == 0
            ):
                raise Exception(
                    f"Request {request_num} returned invalid response content: {result}"
                )

            return result
        except Exception as e:
            raise Exception(f"Request {request_num} failed: {str(e)}")

    # Create and run tasks
    tasks = [request_with_timing(i + 1) for i in range(num_requests)]
    await asyncio.gather(*tasks)

    total_elapsed = time.time() - start_time
    request_times.sort()  # Sort for easier analysis

    return total_elapsed, request_times


# Individual test functions for each concurrency level
@pytest.mark.asyncio
async def test_1_parallel_request_v2():
    """Test V2 performance with 1 concurrent request"""
    num_requests = 1
    total_time, request_times = await run_parallel_requests_with_timing(num_requests)

    print(f"\n📊 Request times: {[f'{t:.2f}s' for t in request_times]}")
    print(f"✅ [V2 PARALLEL TEST: {num_requests} request] COMPLETED\n")

    assert total_time > 0, "Test should take some time to complete"


@pytest.mark.asyncio
async def test_3_parallel_requests_v2():
    """Test V2 performance with 3 parallel requests"""
    num_requests = 3
    total_time, request_times = await run_parallel_requests_with_timing(num_requests)

    print(f"\n📊 Request times: {[f'{t:.2f}s' for t in request_times]}")
    print(f"✅ [V2 PARALLEL TEST: {num_requests} requests] COMPLETED\n")

    assert total_time > 0, "Test should take some time to complete"


@pytest.mark.asyncio
async def test_5_parallel_requests_v2():
    """Test V2 performance with 5 parallel requests"""
    num_requests = 5
    total_time, request_times = await run_parallel_requests_with_timing(num_requests)

    print(f"\n📊 Request times: {[f'{t:.2f}s' for t in request_times]}")
    print(f"✅ [V2 PARALLEL TEST: {num_requests} requests] COMPLETED\n")

    assert total_time > 0, "Test should take some time to complete"


@pytest.mark.asyncio
async def test_10_parallel_requests_v2():
    """Test V2 performance with 10 parallel requests"""
    num_requests = 10
    total_time, request_times = await run_parallel_requests_with_timing(num_requests)

    print(f"\n📊 Request times: {[f'{t:.2f}s' for t in request_times]}")
    print(f"✅ [V2 PARALLEL TEST: {num_requests} requests] COMPLETED\n")

    assert total_time > 0, "Test should take some time to complete"
