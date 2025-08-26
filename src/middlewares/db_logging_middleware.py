import json
import logging
import traceback
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import StreamingResponse

from src.db.database import create_db_session
from src.db.models.log import Log


class LoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._logger = logging.getLogger(__name__)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if "/generate" not in request.url.path:
            return await call_next(request)

        request_body = await request.body()
        prompt = self._extract_prompt_from_body(request_body)

        async def receive() -> dict:
            return {"type": "http.request", "body": request_body}

        new_request = Request(request.scope, receive)

        db = create_db_session()
        error_details: Optional[str] = None
        generated_response: Optional[str] = None
        response: Optional[Response] = None

        try:
            response = await call_next(new_request)
            response_body_bytes = b""
            async for chunk in response.body_iterator:
                response_body_bytes += chunk

            if isinstance(response, StreamingResponse):
                generated_response = self._decode_streamed_body(response_body_bytes)
            else:
                generated_response = self._extract_text_from_json_body(
                    response_body_bytes
                )

            # Re-create the response since we've consumed the iterator
            response = Response(
                content=response_body_bytes,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

            if response.status_code >= 400:
                error_details = generated_response or "[No error details in body]"

            return response
        except Exception:
            error_details = traceback.format_exc()
            raise
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

    def _extract_prompt_from_body(self, body: bytes) -> Optional[str]:
        try:
            data = json.loads(body)
            return data.get("prompt")
        except (json.JSONDecodeError, TypeError):
            return None

    def _extract_text_from_json_body(self, body: bytes) -> Optional[str]:
        try:
            data = json.loads(body)
            return data.get("response")
        except (json.JSONDecodeError, TypeError):
            return body.decode("utf-8", errors="ignore")

    def _decode_streamed_body(self, body_bytes: bytes) -> str:
        """
        Decodes the full byte string from a streaming response.
        Each chunk is a JSON object, so we need to parse them line by line.
        """
        full_text = []
        # The body may contain multiple JSON objects, not separated by newlines
        # e.g., b'{"key":"val1"}{"key":"val2"}'
        # A robust solution would use a streaming JSON parser.
        # For this case, we can split on the boundary of JSON objects.
        decoded_body = body_bytes.decode("utf-8").strip()
        # This is a simplification assuming each JSON object is sent as a chunk.
        # We replace '}{' with '}\n{' to handle concatenated JSONs.
        for line in decoded_body.replace("}{", "}\n{").splitlines():
            if line:
                try:
                    data = json.loads(line)
                    full_text.append(data.get("response", ""))
                except json.JSONDecodeError:
                    continue
        return "".join(full_text)

    def _safe_log(
        self,
        db,
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
