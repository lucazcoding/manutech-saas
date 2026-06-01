from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from fastapi import Query
from pydantic import BaseModel, ConfigDict, field_validator


class AssetSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    serial_number: Optional[str] = None


class TechnicianSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_number: int
    client_name: str
    location: str
    description: Optional[str] = None
    status: str
    priority: str
    total_cost: Decimal
    start_date: Optional[date] = None
    asset: Optional[AssetSummary] = None
    assigned_technician: Optional[TechnicianSummary] = None
    created_at: datetime
    updated_at: datetime


class CreateOrderRequest(BaseModel):
    client_name: str
    location: str
    description: Optional[str] = None
    priority: Optional[str] = "medium"
    start_date: Optional[date] = None
    asset_id: Optional[int] = None

    @field_validator("client_name", "location")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Campo não pode ser vazio")
        return v.strip()

    @field_validator("priority")
    @classmethod
    def valid_priority(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("low", "medium", "high", "urgent"):
            raise ValueError("Priority deve ser low, medium, high ou urgent")
        return v


class UpdateOrderRequest(BaseModel):
    client_name: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    start_date: Optional[date] = None
    asset_id: Optional[int] = None

    @field_validator("client_name", "location")
    @classmethod
    def not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Campo não pode ser vazio")
        return v.strip() if v else v

    @field_validator("priority")
    @classmethod
    def valid_priority(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("low", "medium", "high", "urgent"):
            raise ValueError("Priority deve ser low, medium, high ou urgent")
        return v


class UpdateOrderStatusRequest(BaseModel):
    status: str
    reason: Optional[str] = None

    @field_validator("status")
    @classmethod
    def valid_status(cls, v: str) -> str:
        if v not in ("open", "in_progress", "completed", "cancelled"):
            raise ValueError("Status inválido")
        return v


class AssignOrderRequest(BaseModel):
    technician_id: int


class AttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_name: str
    mime_type: str
    size_bytes: int
    file_path: str
    created_at: datetime


class OrderStats(BaseModel):
    total: int
    by_status: dict[str, int]
    by_priority: dict[str, int]


class AuditLogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    delta: Any
    changed_by: Optional[int] = None
    created_at: datetime


@dataclass
class OrderFilters:
    status: Optional[str] = Query(default=None)
    priority: Optional[str] = Query(default=None)
    technician_id: Optional[int] = Query(default=None)
    client_name: Optional[str] = Query(default=None)
    order_number: Optional[int] = Query(default=None)
    asset_id: Optional[int] = Query(default=None)
    start_date_from: Optional[date] = Query(default=None)
    start_date_to: Optional[date] = Query(default=None)
    page: int = Query(default=1, ge=1)
    page_size: int = Query(default=20, ge=1, le=100)
