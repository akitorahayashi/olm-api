from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

import ollama
from src.api.v1.routers import generate, logs
from src.middlewares.db_logging_middleware import LoggingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    """
    # Startup logic (if any)
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
app.include_router(generate.router)
app.include_router(logs.router)


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


@app.get("/health", tags=["Health Check"])
async def health_check():
    """
    Simple health check endpoint to confirm the API is running.
    """
    return {"status": "ok"}
