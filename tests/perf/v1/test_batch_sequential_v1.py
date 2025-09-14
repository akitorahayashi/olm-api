import asyncio
import json
import os
import time

import httpx
import pytest

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


# Define test cases for sequential requests
# Each tuple represents (num_requests, interval_seconds)
SEQUENTIAL_TEST_CASES = [
    pytest.param(15, 1.0, id="15_requests_1.0s_interval"),
    pytest.param(15, 2.0, id="15_requests_2.0s_interval"),
    pytest.param(15, 3.0, id="15_requests_3.0s_interval"),
]


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

        # Log the JSON response with formatted think tags
        if "response" in response_data:
            formatted_response_text = response_data["response"].replace(
                "</think>", "</think>\n\n"
            )
            formatted_response_data = response_data.copy()
            formatted_response_data["response"] = formatted_response_text
            print(
                f"\nRequest {request_number}: {elapsed:.2f}s - Response JSON: {json.dumps(formatted_response_data, ensure_ascii=False)}"
            )
        else:
            print(
                f"\nRequest {request_number}: {elapsed:.2f}s - Response JSON: {json.dumps(response_data, ensure_ascii=False)}"
            )

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


async def run_sequential_requests_with_interval(
    num_requests: int, interval_seconds: float, prompt: str, model_name: str
) -> tuple[float, list[float]]:
    """
    Run sequential requests with specified interval and return total elapsed time and individual request times.
    """
    host_port = os.getenv("TEST_PORT", "8002")

    generate_url = f"http://localhost:{host_port}/api/v1/generate"
    request_payload = {
        "prompt": prompt,
        "model_name": model_name,
        "stream": False,
    }

    start_time = time.time()
    request_times = []

    async with httpx.AsyncClient(timeout=600) as client:
        for i in range(num_requests):
            try:
                result, individual_time = await make_api_request(
                    client, generate_url, request_payload, i + 1
                )

                request_times.append(individual_time)

                # Validate response
                if (
                    not isinstance(result.get("response"), str)
                    or len(result.get("response", "")) == 0
                ):
                    raise Exception(
                        f"Request {i + 1} returned invalid response content: {result}"
                    )

                # Wait for the specified interval before next request (except for the last one)
                if i < num_requests - 1:
                    await asyncio.sleep(interval_seconds)

            except Exception as e:
                raise Exception(f"Request {i + 1} failed: {str(e)}")

    total_elapsed = time.time() - start_time
    return total_elapsed, request_times


@pytest.mark.asyncio
@pytest.mark.parametrize("num_requests, interval", SEQUENTIAL_TEST_CASES)
async def test_sequential_performance(
    num_requests: int,
    interval: float,
    load_prompt,
    get_model_name,
):
    """
    Test performance with sequential requests for various configurations.
    """
    total_time, request_times = await run_sequential_requests_with_interval(
        num_requests, interval, load_prompt, get_model_name
    )

    assert request_times, "Should have recorded request times"
    avg_time = sum(request_times) / len(request_times)
    min_time = min(request_times)
    max_time = max(request_times)

    print(f"\n📊 Sequential Test ({num_requests} requests, {interval}s interval):")
    print(f"   Total time: {total_time:.2f}s")
    print(f"   Average response time: {avg_time:.2f}s")
    print(f"   Min/Max response time: {min_time:.2f}s / {max_time:.2f}s")
    print(
        f"✅ [SEQUENTIAL TEST: {num_requests} requests @ {interval}s intervals] COMPLETED\n"
    )

    assert total_time > 0, "Test should take some time to complete"
    assert (
        len(request_times) == num_requests
    ), f"Should have {num_requests} response times"
