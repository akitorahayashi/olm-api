from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.models.log import Log

router = APIRouter()
templates = Jinja2Templates(directory="src/templates")


@router.get("/api/v1/logs", tags=["logs"])
def get_logs(db: Session = Depends(get_db)):
    """
    Retrieve all logs from the database, ordered by the most recent first.
    """
    return db.query(Log).order_by(Log.timestamp.desc()).all()


@router.get("/logs/view", response_class=HTMLResponse, tags=["logs"])
async def view_logs(request: Request):
    """
    Serves the HTML page to view logs.
    """
    return templates.TemplateResponse(request, "logs.html")
