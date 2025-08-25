import logging
import traceback
from typing import Optional

from fastapi import Request, Response
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from src.db.database import create_db_session
from src.models.log import Log


class LoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self._logger = logging.getLogger(__name__)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if "/generate" not in request.url.path:
            return await call_next(request)

        db = create_db_session()
        error_details: Optional[str] = None
        response = None

        try:
            response = await call_next(request)
            if response.status_code >= 400:
                # For streaming responses, we need to iterate to get the body.
                # This consumes the original response's stream.
                body_chunks = [chunk async for chunk in response.body_iterator]
                response_body = b"".join(body_chunks)
                error_details = response_body.decode("utf-8")

                # Re-create the response with the consumed body to send to the client.
                response = Response(
                    content=response_body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )
            return response
        except Exception:
            # This block will catch unhandled exceptions that crash the application
            # before a response is formed (e.g., middleware errors).
            error_details = traceback.format_exc()
            raise  # Re-raise to allow FastAPI's default error handling to take over
        finally:
            # Ensure logging happens even if an unhandled exception occurs.
            # If `response` is None, it means an exception was raised before a response was formed.
            status_code = response.status_code if response else 500
            self._safe_log(db, request, status_code, error_details)

    def _safe_log(
        self,
        db: Session,
        request: Request,
        status_code: int,
        error_details: Optional[str],
    ) -> None:
        """
        Log the request to the database in a "best-effort" manner.
        Failures in logging should not affect the API response.
        """
        try:
            log_entry = Log(
                client_host=request.client.host,
                request_method=request.method,
                request_path=str(request.url.path),
                response_status_code=status_code,
                prompt="[Not Logged]",
                generated_response="[Not Logged]",
                error_details=error_details,
            )
            db.add(log_entry)
            db.commit()
        except Exception:
            db.rollback()
            self._logger.exception("Failed to write request log to the database.")
        finally:
            db.close()
