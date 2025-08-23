from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from src.db.database import SessionLocal
from src.models.log import Log


class LoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip logging for any non-generate endpoints
        if "/generate" not in request.url.path:
            return await call_next(request)

        db = SessionLocal()
        try:
            response = await call_next(request)
            log_entry = Log(
                client_host=request.client.host,
                request_method=request.method,
                request_path=str(request.url.path),
                response_status_code=response.status_code,
            )
            db.add(log_entry)
            db.commit()
            return response
        except Exception as e:
            # For exceptions, we still want to log the attempt.
            # FastAPI's default exception handler will turn this into a 500 response.
            # If using custom exception handlers, the status code might differ.
            status_code = getattr(e, "status_code", 500)
            log_entry = Log(
                client_host=request.client.host,
                request_method=request.method,
                request_path=str(request.url.path),
                response_status_code=status_code,
            )
            db.add(log_entry)
            db.commit()
            raise e  # Re-raise the exception to be handled by FastAPI
        finally:
            db.close()
