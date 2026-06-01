from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import Query
from pydantic import BaseModel, ConfigDict, field_validator


class MaterialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    sku: str
    unit_price: Decimal
    quantity_in_stock: Decimal
    min_quantity: Decimal
    status: str
    created_at: datetime
    updated_at: datetime


class CreateMaterialRequest(BaseModel):
    name: str
    sku: str
    unit_price: float
    quantity_in_stock: Optional[float] = 0.0
    min_quantity: Optional[float] = 5.0

    @field_validator("name", "sku")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Campo não pode ser vazio")
        return v.strip()

    @field_validator("unit_price")
    @classmethod
    def price_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Preço não pode ser negativo")
        return v


class UpdateMaterialRequest(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    unit_price: Optional[float] = None
    min_quantity: Optional[float] = None

    @field_validator("name", "sku")
    @classmethod
    def not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Campo não pode ser vazio")
        return v.strip() if v else v


class UpdateMaterialStatusRequest(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def valid_status(cls, v: str) -> str:
        if v not in ("active", "inactive"):
            raise ValueError("Status deve ser 'active' ou 'inactive'")
        return v


class MaterialStatusUpdateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    updated_at: datetime


class CreateMovementRequest(BaseModel):
    material_id: int
    service_order_id: Optional[int] = None
    movement_type: str
    quantity: float
    notes: Optional[str] = None

    @field_validator("movement_type")
    @classmethod
    def valid_type(cls, v: str) -> str:
        if v not in ("in", "out"):
            raise ValueError("Tipo de movimento deve ser 'in' ou 'out'")
        return v

    @field_validator("quantity")
    @classmethod
    def positive_quantity(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Quantidade deve ser maior que zero")
        return v


class MovementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    material_id: int
    service_order_id: Optional[int] = None
    movement_type: str
    quantity: Decimal
    notes: Optional[str] = None
    created_at: datetime


class StockReportItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    sku: str
    quantity_in_stock: Decimal
    min_quantity: Decimal
    unit_price: Decimal
    status: str
    is_low_stock: bool


@dataclass
class MaterialFilters:
    name: Optional[str] = Query(default=None)
    status: Optional[str] = Query(default=None)
    page: int = Query(default=1, ge=1)
    page_size: int = Query(default=20, ge=1, le=100)


@dataclass
class MovementFilters:
    material_id: Optional[int] = Query(default=None)
    movement_type: Optional[str] = Query(default=None)
    service_order_id: Optional[int] = Query(default=None)
    page: int = Query(default=1, ge=1)
    page_size: int = Query(default=20, ge=1, le=100)
