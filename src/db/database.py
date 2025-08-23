from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.config.settings import Settings

# We use lru_cache to ensure the Settings object is created only once.
@lru_cache()
def get_settings():
    return Settings()

# We will lazy-load the engine and session factory to prevent
# pydantic from trying to validate settings at import time, which
# happens before pytest fixtures can set environment variables.
_engine = None
_SessionLocal = None


def get_db_session():
    """
    Returns a new database session.
    Initializes the engine and SessionLocal factory on the first call.
    """
    global _engine, _SessionLocal
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.DATABASE_URL,
            connect_args={
                "check_same_thread": False
            }
            if settings.DATABASE_URL.startswith("sqlite")
            else {},
        )
        _SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=_engine
        )

    return _SessionLocal()


# Base class for our models to inherit from.
Base = declarative_base()
