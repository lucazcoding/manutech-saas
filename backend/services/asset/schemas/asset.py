from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from fastapi import Query
from pydantic import BaseModel, ConfigDict, field_validator


class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    serial_number: Optional[str] = None
    location: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime


class CreateAssetRequest(BaseModel):
    name: str
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    serial_number: Optional[str] = None
    location: Optional[str] = None

    @field_validator("name")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Campo não pode ser vazio")
        return v.strip()


class UpdateAssetRequest(BaseModel):
    name: Optional[str] = None
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    serial_number: Optional[str] = None
    location: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Campo não pode ser vazio")
        return v.strip() if v else v


class UpdateAssetStatusRequest(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def valid_status(cls, v: str) -> str:
        if v not in ("active", "inactive"):
            raise ValueError("Status deve ser 'active' ou 'inactive'")
        return v


class AssetStatusUpdateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    updated_at: datetime


@dataclass
class AssetFilters:
    name: Optional[str] = Query(default=None)
    status: Optional[str] = Query(default=None)
    location: Optional[str] = Query(default=None)
    page: int = Query(default=1, ge=1)
    page_size: int = Query(default=20, ge=1, le=100)
