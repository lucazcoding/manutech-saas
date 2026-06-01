from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from fastapi import Query
from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    type: str
    title: str
    message: str
    read: bool
    related_id: Optional[int] = None
    created_at: datetime


class NotificationReadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    read: bool


@dataclass
class NotificationFilters:
    read: Optional[bool] = Query(default=None)
    page: int = Query(default=1, ge=1)
    page_size: int = Query(default=20, ge=1, le=100)
