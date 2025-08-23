from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.dependencies.common import get_settings

# --- Lazy Initialization for Database Engine and Session Factory ---

_engine = None
_SessionLocal = None


def _initialize_factory():
    """
    Lazy initializer for the database engine and session factory.
    This prevents settings from being loaded at import time.
    """
    global _engine, _SessionLocal
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(settings.DATABASE_URL)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


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
