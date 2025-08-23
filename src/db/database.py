from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./pvt-llm-api.db"
# The application will use a SQLite database file named 'pvt-llm-api.db'
# in the root directory of the project.

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    # connect_args is needed only for SQLite. It's to prevent accidental
    # sharing of the same connection between different threads, which can
    # happen with FastAPI's dependency injection system.
    connect_args={"check_same_thread": False},
)

# Each instance of the SessionLocal class will be a database session.
# The class itself is not a session yet, but will create one when called.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# We will inherit from this class to create each of the ORM models.
Base = declarative_base()
