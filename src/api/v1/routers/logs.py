from typing import List

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from src.api.v1.schemas import LogRead
from src.db.database import get_db
from src.db.models.log import Log

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
    return templates.TemplateResponse("logs.html", {"request": request})
