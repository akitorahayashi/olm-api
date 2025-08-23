import logging

from fastapi import Request, Response
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from src.db.database import get_db_session
from src.models.log import Log


class LoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self._logger = logging.getLogger(__name__)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip logging for any non-generate endpoints.
        if "/generate" not in request.url.path:
            return await call_next(request)

        db = get_db_session()
        try:
            # First, try to get the response from the endpoint
            try:
                response = await call_next(request)
                # If successful, log the outcome and return the response
                self._safe_log(db, request, response.status_code)
                return response
            except Exception as e:
                # If an exception occurs in the endpoint, log the failure
                # and then re-raise the exception to be handled by FastAPI.
                status_code = getattr(e, "status_code", 500)
                self._safe_log(db, request, status_code)
                raise
        finally:
            # Ensure the database session is closed.
            db.close()

    def _safe_log(self, db: Session, request: Request, status_code: int) -> None:
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
            )
            db.add(log_entry)
            db.commit()
        except Exception:
            # If logging fails, rollback the transaction and log the error
            # to the console, but do not re-raise the exception.
            db.rollback()
            self._logger.exception("Failed to write request log to the database.")
