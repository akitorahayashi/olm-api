from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

import ollama
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
    # Add the logging middleware here, so it's instantiated after mocks can be applied
    app.add_middleware(LoggingMiddleware)
    yield
    # Shutdown logic (if any)


app = FastAPI(
    title="PVT-LLM-API",
    version="0.1.0",
    description="A private LLM API server using FastAPI and Ollama, with dynamic model management.",
    lifespan=lifespan,
)

# Include the routers
app.include_router(generate.router)
app.include_router(models.router)


# ==============================================================================
# Global Exception Handlers
# ==============================================================================


@app.exception_handler(httpx.RequestError)
async def http_request_exception_handler(request: Request, exc: httpx.RequestError):
    """
    Handles connection errors to the Ollama service, returning a 502 Bad Gateway.
    This prevents leaking internal stack traces to the client.
    """
    return JSONResponse(
        status_code=502,
        content={"detail": f"Error connecting to upstream service: {exc.request.url}"},
    )


@app.exception_handler(ollama.ResponseError)
async def ollama_response_exception_handler(
    request: Request, exc: ollama.ResponseError
):
    """
    Handles errors reported by the Ollama service itself, returning a 503 Service Unavailable.
    This could indicate the model is not available, the service is overloaded, etc.
    """
    return JSONResponse(
        status_code=503,
        content={"detail": f"Upstream service unavailable: {exc.error}"},
    )


@app.get("/health", tags=["Health Check"])
async def health_check():
    """
    Simple health check endpoint to confirm the API is running.
    """
    return {"status": "ok"}
