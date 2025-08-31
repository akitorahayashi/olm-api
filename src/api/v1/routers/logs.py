from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.models.log import Log


class LogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    client_host: Optional[str] = None
    request_method: Optional[str] = None
    request_path: Optional[str] = None
    response_status_code: Optional[int] = None
    prompt: Optional[str] = None
    generated_response: Optional[str] = None
    error_details: Optional[str] = None


router = APIRouter()
templates = Jinja2Templates(directory="src/templates")


@router.get("/api/v1/logs", response_model=List[LogRead], tags=["logs"])
def get_logs(db: Session = Depends(get_db)):
    """
    Retrieve all logs from the database, ordered by the most recent first.
    """
    logs = db.query(Log).order_by(Log.timestamp.desc()).all()
    return logs


@router.get("/logs/view", response_class=HTMLResponse, tags=["logs"])
async def view_logs(request: Request):
    """
    Serves the HTML page to view logs.
    """
    return templates.TemplateResponse(request, "logs.html")
