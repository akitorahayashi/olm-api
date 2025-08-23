from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from src.db.database import Base


class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    client_host = Column(String, index=True)
    request_method = Column(String)
    request_path = Column(String)
    response_status_code = Column(Integer, index=True)

    def __repr__(self):
        return (
            f"<Log(id={self.id}, timestamp='{self.timestamp}', "
            f"client_host='{self.client_host}', request_path='{self.request_path}', "
            f"response_status_code={self.response_status_code})>"
        )
