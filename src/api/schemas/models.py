from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class ModelDetails(BaseModel):
    name: str
    modified_at: datetime = Field(alias="modified_at")
    size: int


class ModelList(BaseModel):
    models: List[ModelDetails]
