import json
import logging
from typing import Optional

from fastapi import Request, Response
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from src.config.settings import get_settings
from src.db.database import create_db_session
from src.logs.models import Log


class LoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._logger = logging.getLogger(__name__)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        settings = get_settings()
        if not settings.API_LOGGING_ENABLED:
            return await call_next(request)

        # Only log generate (v1) and chat completions (v2) endpoints
        should_log = (
            "/generate" in request.url.path or "/chat/completions" in request.url.path
        )
        if not should_log:
            return await call_next(request)

        request_body = await request.body()
        prompt = self._extract_prompt_from_body(request_body, request.url.path)

        async def receive() -> dict:
            return {"type": "http.request", "body": request_body}

        new_request = Request(request.scope, receive)

        db = create_db_session()
        error_details: Optional[str] = None
        generated_response: Optional[str] = None
        response: Optional[Response] = None

        try:
            response = await call_next(new_request)

            # We must capture the content type BEFORE consuming the stream.
            content_type = response.headers.get("content-type", "")
            is_streaming = "event-stream" in content_type

            response_body_bytes = b""
            async for chunk in response.body_iterator:
                response_body_bytes += chunk

            if is_streaming:
                generated_response = self._decode_sse_body(
                    response_body_bytes, request.url.path
                )
            else:
                generated_response = self._extract_text_from_json_body(
                    response_body_bytes, request.url.path
                )

            # Re-create the response since we've consumed the iterator
            response = Response(
                content=response_body_bytes,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

            if response.status_code >= 400:
                # For error responses, try to extract error details from the response body
                try:
                    response_data = json.loads(response_body_bytes)
                    error_details = response_data.get(
                        "detail", "[No error details in body]"
                    )
                except (json.JSONDecodeError, TypeError):
                    error_details = "[No error details in body]"

        except Exception as e:
            error_details = f"Exception: {str(e)}"
            # Return a 500 response instead of re-raising
            response = Response(
                content=json.dumps({"detail": "Internal server error"}),
                status_code=500,
                headers={"content-type": "application/json"},
            )
        finally:
            status_code = response.status_code if response else 500
            self._safe_log(
                db=db,
                request=request,
                status_code=status_code,
                prompt=prompt,
                generated_response=generated_response,
                error_details=error_details,
            )

        return response

    def _extract_prompt_from_body(self, body: bytes, path: str) -> Optional[str]:
        try:
            data = json.loads(body)

            # v1 API: extract from "prompt" field
            if "/api/v1/" in path:
                return data.get("prompt")

            # v2 API: extract from last message in "messages" array
            elif "/api/v2/" in path:
                messages = data.get("messages", [])
                if messages:
                    # Get the last user message content
                    for message in reversed(messages):
                        if message.get("role") == "user" and message.get("content"):
                            return message["content"]
                return None

            return data.get("prompt")  # fallback
        except (json.JSONDecodeError, TypeError):
            return None

    def _extract_text_from_json_body(self, body: bytes, path: str) -> Optional[str]:
        try:
            data = json.loads(body)

            # v1 API: extract from "response" field
            if "/api/v1/" in path:
                return data.get("response")

            # v2 API: extract from OpenAI-compatible response structure
            elif "/api/v2/" in path:
                choices = data.get("choices", [])
                if choices and len(choices) > 0:
                    message = choices[0].get("message", {})
                    content = message.get("content")
                    tool_calls = message.get("tool_calls")

                    if content:
                        return content
                    elif tool_calls:
                        # Log tool calls as summary
                        tool_names = [
                            tc.get("function", {}).get("name", "unknown")
                            for tc in tool_calls
                        ]
                        return f"[Tool Call: {', '.join(tool_names)}]"

                return None

            # Fallback for unknown paths
            return data.get("response")
        except (json.JSONDecodeError, TypeError):
            return body.decode("utf-8", errors="ignore")

    def _decode_sse_body(self, body_bytes: bytes, path: str) -> str:
        """
        Decodes a response body in Server-Sent Events (SSE) format.
        Supports both v1 and v2 API formats.
        """
        full_text = []
        for line in body_bytes.decode("utf-8").splitlines():
            if line.startswith("data:"):
                json_str = line[len("data:") :].strip()
                if json_str == "[DONE]":  # v2 completion indicator
                    break
                if json_str:
                    try:
                        data = json.loads(json_str)

                        # v1 API: extract from "response" field
                        if "/api/v1/" in path:
                            full_text.append(data.get("response", ""))

                        # v2 API: extract from OpenAI-compatible streaming format
                        elif "/api/v2/" in path:
                            choices = data.get("choices", [])
                            if choices and len(choices) > 0:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content")
                                if content:
                                    full_text.append(content)

                    except json.JSONDecodeError:
                        continue
        return "".join(full_text)

    def _safe_log(
        self,
        db: Session,
        request: Request,
        status_code: int,
        prompt: Optional[str],
        generated_response: Optional[str],
        error_details: Optional[str],
    ) -> None:
        try:
            log_entry = Log(
                client_host=request.client.host,
                request_method=request.method,
                request_path=str(request.url.path),
                response_status_code=status_code,
                prompt=prompt,
                generated_response=generated_response,
                error_details=error_details,
            )
            db.add(log_entry)
            db.commit()
        except Exception:
            db.rollback()
            self._logger.exception("Failed to write request log to the database.")
        finally:
            db.close()
