import asyncio
import os
import time

import httpx
import pytest

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
        if "response" not in response_data:
            raise Exception(
                f"Request {request_number} returned invalid response format: {response_data}"
            )

        return response_data, elapsed
    except Exception as e:
        elapsed = time.time() - start_time
        raise Exception(
            f"Request {request_number} failed after {elapsed:.2f}s: {str(e)}"
        )


async def run_concurrent_requests_with_timing(
    num_requests: int,
) -> tuple[float, list[float]]:
    """
    Run concurrent requests and return total elapsed time and individual request times.
    """
    host_port = os.getenv("HOST_PORT", "8000")
    model_name = os.getenv("BUILT_IN_OLLAMA_MODEL")
    assert model_name, "BUILT_IN_OLLAMA_MODEL environment variable must be set"

    generate_url = f"http://localhost:{host_port}/api/v1/generate"
    request_payload = {
        "prompt": "What is 2+2?",
        "model_name": model_name,
        "stream": False,
    }

    start_time = time.time()
    request_times = []

    async def request_with_timing(request_num):
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                result, individual_time = await make_api_request(
                    client, generate_url, request_payload, request_num
                )

            request_times.append(individual_time)

            # Validate response
            if (
                not isinstance(result.get("response"), str)
                or len(result.get("response", "")) == 0
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
async def test_1_concurrent_request():
    """Test performance with 1 concurrent request"""
    num_requests = 1
    total_time, request_times = await run_concurrent_requests_with_timing(num_requests)

    print(f"\n📊 Request times: {[f'{t:.2f}s' for t in request_times]}")
    print(f"✅ [CONCURRENCY TEST: {num_requests} request] COMPLETED\n")

    assert total_time > 0, "Test should take some time to complete"


@pytest.mark.asyncio
async def test_2_concurrent_requests():
    """Test performance with 2 concurrent requests"""
    num_requests = 2
    total_time, request_times = await run_concurrent_requests_with_timing(num_requests)

    print(f"\n📊 Request times: {[f'{t:.2f}s' for t in request_times]}")
    print(f"✅ [CONCURRENCY TEST: {num_requests} requests] COMPLETED\n")

    assert total_time > 0, "Test should take some time to complete"


@pytest.mark.asyncio
async def test_5_concurrent_requests():
    """Test performance with 5 concurrent requests"""
    num_requests = 5
    total_time, request_times = await run_concurrent_requests_with_timing(num_requests)

    print(f"\n📊 Request times: {[f'{t:.2f}s' for t in request_times]}")
    print(f"✅ [CONCURRENCY TEST: {num_requests} requests] COMPLETED\n")

    assert total_time > 0, "Test should take some time to complete"


@pytest.mark.asyncio
# @pytest.mark.skip(reason="Heavy load test - enable manually if needed")
async def test_10_concurrent_requests():
    """Test performance with 10 concurrent requests"""
    num_requests = 10
    total_time, request_times = await run_concurrent_requests_with_timing(num_requests)

    print(f"\n📊 Request times: {[f'{t:.2f}s' for t in request_times]}")
    print(f"✅ [CONCURRENCY TEST: {num_requests} requests] COMPLETED\n")

    assert total_time > 0, "Test should take some time to complete"
