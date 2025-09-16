from typing import List

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..db.database import get_db
from .models import Log
from .schemas import LogRead

router = APIRouter(prefix="/logs", tags=["logs"])
templates = Jinja2Templates(directory="src/olm_api/logs/templates")


@router.get("/data", response_model=List[LogRead], tags=["logs"])
def get_logs(db: Session = Depends(get_db)):
    """
    Retrieve all logs from the database, ordered by the most recent first.
    """
    logs = db.query(Log).order_by(Log.timestamp.desc()).all()
    return logs


@router.get("/", response_class=HTMLResponse, tags=["logs"])
async def view_logs(request: Request):
    """
    Serves the HTML page to view logs.
    """
    return templates.TemplateResponse(request, "logs.html")
