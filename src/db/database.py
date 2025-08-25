import threading

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.config.settings import Settings

# --- Lazy Initialization for Database Engine and Session Factory ---

_engine = None
_SessionLocal = None
_lock = threading.Lock()


def _initialize_factory():
    """
    Lazy initializer for the database engine and session factory.
    This prevents settings from being loaded at import time and is thread-safe.
    """
    global _engine, _SessionLocal
    # Use a lock to ensure that the engine and session factory are created only once.
    with _lock:
        if _engine is None:
            settings = Settings()
            _engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
            _SessionLocal = sessionmaker(
                autocommit=False, autoflush=False, bind=_engine
            )


def create_db_session():
    """
    Creates a new SQLAlchemy session.
    For direct use in places like middleware or background tasks.
    """
    _initialize_factory()
    return _SessionLocal()


def get_db():
    """
    FastAPI dependency that provides a database session and ensures it's closed.
    """
    session = create_db_session()
    try:
        yield session
    finally:
        session.close()


# --- Declarative Base for Models ---

Base = declarative_base()
