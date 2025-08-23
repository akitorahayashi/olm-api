from fastapi import FastAPI

from src.dependencies.logging import LoggingMiddleware
from src.routers import generate

app = FastAPI(
    title="PVT-LLM-API",
    version="0.1.0",
    description="A private LLM API server using FastAPI and Ollama, refactored into a layered architecture.",
)

# Add the logging middleware
app.add_middleware(LoggingMiddleware)

# Include the router from the generate module
app.include_router(generate.router)


@app.get("/health", tags=["Health Check"])
async def health_check():
    """
    Simple health check endpoint to confirm the API is running.
    """
    return {"status": "ok"}
