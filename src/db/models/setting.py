from sqlalchemy import Column, String

from src.db.database import Base


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True, index=True)
    value = Column(String, nullable=False)
