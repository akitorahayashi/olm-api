from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text

from src.db.database import Base


class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    client_host = Column(String, index=True)
    request_method = Column(String)
    request_path = Column(String)
    response_status_code = Column(Integer, index=True)
    prompt = Column(Text, nullable=True)
    generated_response = Column(Text, nullable=True)
    error_details = Column(Text, nullable=True)

    def __repr__(self):
        return (
            f"<Log(id={self.id}, timestamp='{self.timestamp}', "
            f"client_host='{self.client_host}', request_path='{self.request_path}', "
            f"response_status_code={self.response_status_code}, "
            f"error_details='{self.error_details is not None}')>"
        )
