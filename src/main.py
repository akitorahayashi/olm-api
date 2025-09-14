import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

import ollama
from src.api.v1.routers import chat as v1_chat
from src.api.v2.routers import chat as v2_chat
from src.logs import router as logs_router
from src.middlewares.db_logging_middleware import LoggingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for model warm-up.
    """
    # Startup logic: warm up the built-in model
    # Temporarily disabled to debug E2E test issues
    logging.info("Model warm-up temporarily disabled for debugging")

    yield
    # Shutdown logic (if any)


app = FastAPI(
    title="PVT-LLM-API",
    version="0.1.0",
    description="A private LLM API server using FastAPI and Ollama, with dynamic model management.",
    lifespan=lifespan,
)

# Add the logging middleware here. By adding it outside the lifespan, we ensure
# that dependency overrides from the test environment are applied before the
# middleware is instantiated. This is crucial for tests that mock dependencies
# used by the middleware, such as the database session.
app.add_middleware(LoggingMiddleware)


# Include the routers from the v1 API
app.include_router(v1_chat.router)

# Include the logs router
app.include_router(logs_router.router)

# Include the routers from the v2 API
app.include_router(v2_chat.router)


# ==============================================================================
# Global Exception Handlers
# ==============================================================================


@app.exception_handler(httpx.RequestError)
async def http_request_exception_handler(request: Request, exc: httpx.RequestError):
    """
    Handles connection errors to the Ollama service, returning a 502 Bad Gateway.
    This prevents leaking internal stack traces to the client.
    """
    # The request object might be None in some cases, so we access its URL safely.
    url = getattr(exc.request, "url", "unknown")
    return JSONResponse(
        status_code=502,
        content={"detail": f"Error connecting to upstream service: {url}"},
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


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Handles all unhandled exceptions, returning a 500 Internal Server Error.
    This prevents sensitive server information from being exposed to clients.
    """
    import traceback

    logging.error(f"Unhandled exception at {request.url}: {exc}")
    logging.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
    )


@app.get("/health", tags=["Health Check"])
async def health_check():
    """
    Simple health check endpoint to confirm the API is running.
    """
    return {"status": "ok"}
