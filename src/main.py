from fastapi import FastAPI

from src.dependencies.logging import LoggingMiddleware
from src.pvt_llm_api.v1.routers import generate

app = FastAPI(
    title="PVT-LLM-API",
    version="0.1.0",
    description="A private LLM API server using FastAPI and Ollama, refactored into a layered architecture.",
)

# Add the logging middleware
app.add_middleware(LoggingMiddleware)

# Include the router from the generate module
app.include_router(generate.router)
