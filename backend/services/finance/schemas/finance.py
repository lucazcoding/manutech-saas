from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import Query
from pydantic import BaseModel, ConfigDict, field_validator


# ─── Costs ───────────────────────────────────────────────────────────────────

class CostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    service_order_id: int
    description: str
    amount: Decimal
    cost_type: str
    created_at: datetime


class CreateCostRequest(BaseModel):
    service_order_id: int
    description: str
    amount: float
    cost_type: Optional[str] = "other"

    @field_validator("description")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Campo não pode ser vazio")
        return v.strip()

    @field_validator("cost_type")
    @classmethod
    def valid_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("material", "labor", "service", "other"):
            raise ValueError("cost_type deve ser material, labor, service ou other")
        return v

    @field_validator("amount")
    @classmethod
    def non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Valor não pode ser negativo")
        return v


class UpdateCostRequest(BaseModel):
    description: Optional[str] = None
    amount: Optional[float] = None
    cost_type: Optional[str] = None

    @field_validator("description")
    @classmethod
    def not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Campo não pode ser vazio")
        return v.strip() if v else v


@dataclass
class CostFilters:
    service_order_id: Optional[int] = Query(default=None)
    cost_type: Optional[str] = Query(default=None)
    page: int = Query(default=1, ge=1)
    page_size: int = Query(default=20, ge=1, le=100)


# ─── Budgets ─────────────────────────────────────────────────────────────────

class BudgetItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    description: str
    quantity: Decimal
    unit_price: Decimal
    created_at: datetime


class CreateBudgetItemRequest(BaseModel):
    description: str
    quantity: float
    unit_price: float

    @field_validator("quantity")
    @classmethod
    def positive_qty(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Quantidade deve ser maior que zero")
        return v

    @field_validator("unit_price")
    @classmethod
    def non_negative_price(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Preço não pode ser negativo")
        return v


class BudgetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    budget_number: int
    service_order_id: Optional[int] = None
    client_name: str
    description: Optional[str] = None
    total_amount: Decimal
    status: str
    valid_until: Optional[date] = None
    created_by: Optional[int] = None
    items: list[BudgetItemResponse] = []
    created_at: datetime
    updated_at: datetime


class CreateBudgetRequest(BaseModel):
    service_order_id: Optional[int] = None
    client_name: str
    description: Optional[str] = None
    valid_until: Optional[date] = None
    items: list[CreateBudgetItemRequest] = []

    @field_validator("client_name")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Campo não pode ser vazio")
        return v.strip()


class UpdateBudgetRequest(BaseModel):
    client_name: Optional[str] = None
    description: Optional[str] = None
    valid_until: Optional[date] = None
    items: Optional[list[CreateBudgetItemRequest]] = None

    @field_validator("client_name")
    @classmethod
    def not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Campo não pode ser vazio")
        return v.strip() if v else v


class UpdateBudgetStatusRequest(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def valid_status(cls, v: str) -> str:
        if v not in ("draft", "sent", "approved", "rejected", "expired"):
            raise ValueError("Status inválido")
        return v


@dataclass
class BudgetFilters:
    status: Optional[str] = Query(default=None)
    service_order_id: Optional[int] = Query(default=None)
    page: int = Query(default=1, ge=1)
    page_size: int = Query(default=20, ge=1, le=100)


# ─── Reports ─────────────────────────────────────────────────────────────────

class FinancialReport(BaseModel):
    total_costs: Decimal
    costs_by_type: dict[str, Decimal]
    orders_count: int
    avg_cost_per_order: Decimal
