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

        try:
            response = await call_next(request)
            self._safe_log(db, request, response.status_code, None)
            return response
        except Exception:
            error_details = traceback.format_exc()
            self._safe_log(db, request, 500, error_details)
            raise

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
