from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class ModelDetails(BaseModel):
    name: str = Field(alias="model")
    modified_at: datetime
    size: int


class ModelList(BaseModel):
    models: List[ModelDetails]
