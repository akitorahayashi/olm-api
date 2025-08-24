from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.config.settings import Settings
from src.config.state import app_state
from src.dependencies.common import get_settings
from src.dependencies.logging import LoggingMiddleware
from src.routers import generate, models


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    settings: Settings = get_settings()
    app_state.set_current_model(settings.DEFAULT_GENERATION_MODEL)
    yield
    # Shutdown logic (if any)


app = FastAPI(
    title="PVT-LLM-API",
    version="0.1.0",
    description="A private LLM API server using FastAPI and Ollama, with dynamic model management.",
    lifespan=lifespan,
)

# Add the logging middleware
app.add_middleware(LoggingMiddleware)

# Include the routers
app.include_router(generate.router)
app.include_router(models.router)


@app.get("/health", tags=["Health Check"])
async def health_check():
    """
    Simple health check endpoint to confirm the API is running.
    """
    return {"status": "ok"}
