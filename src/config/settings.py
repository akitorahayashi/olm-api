from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    A configuration class for managing environment variables.

    This class loads configuration values used throughout the application from environment variables.
    Since Docker Compose automatically loads the .env file (symbolic link) in the project root,
    it is not necessary to explicitly specify the file path.
    """

    BUILT_IN_OLLAMA_MODEL: str
    DATABASE_URL: str
    CONCURRENT_REQUEST_LIMIT: int = 2


@lru_cache
def get_settings() -> Settings:
    return Settings()
