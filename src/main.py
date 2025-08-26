from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

import ollama
from src.api.v1.routers import generate, logs, models
from src.api.v1.services import setting_service
from src.config.settings import Settings
from src.db.database import create_db_session
from src.middlewares.db_logging_middleware import LoggingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    - On startup, it ensures that a valid, available model is set as the
      active model in the database.
    - It validates the current active model against the available Ollama models.
    - If the active model is not valid, it falls back to the BUILT_IN_OLLAMA_MODEL.
    - On shutdown, it performs any necessary cleanup.
    """
    # Startup logic
    db: Session | None = None
    settings = Settings()
    try:
        db = create_db_session()
        ollama_service = ollama.Client()

        # 1. Get the current active model from the DB
        active_model_name = setting_service.get_active_model(db)

        # 2. Get all available local models from Ollama
        local_models_data = ollama_service.list()
        local_model_names = {
            model.get("name")
            for model in local_models_data.get("models", [])
            if model.get("name")
        }

        # 3. Validate if the active model is available
        is_active_model_valid = (
            active_model_name is not None and active_model_name in local_model_names
        )

        # 4. If not valid, fallback to the built-in model
        if not is_active_model_valid:
            active_model_name = settings.BUILT_IN_OLLAMA_MODEL
            # Ensure the built-in model is available, raise error if not
            if active_model_name not in local_model_names:
                raise RuntimeError(
                    f"The built-in model '{active_model_name}' is not available in Ollama."
                )
            setting_service.set_active_model(db, active_model_name)

    except (OperationalError, ProgrammingError) as e:
        # If the database is not ready or migrations are not applied,
        # this will raise a more informative error.
        raise RuntimeError(
            "Database is not ready. Please ensure it is running and migrations are applied."
        ) from e
    except httpx.RequestError as e:
        # If Ollama service is not reachable, this will raise a more informative error.
        url = getattr(e.request, "url", "unknown")
        raise RuntimeError(
            f"Could not connect to Ollama service at {url}. "
            "Please ensure Ollama is running and accessible."
        ) from e
    finally:
        if db:
            db.close()

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
app.include_router(models.router)
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
