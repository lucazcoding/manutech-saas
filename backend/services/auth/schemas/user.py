import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from fastapi import Query
from pydantic import BaseModel, ConfigDict, field_validator

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_VALID_ROLES = {"admin", "supervisor", "technician", "attendant"}
_VALID_STATUSES = {"active", "inactive"}


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    login: str
    email: str
    role: str
    status: str
    created_at: datetime


@dataclass
class UserFilters:
    name: Optional[str] = Query(default=None, description="Busca parcial por nome")
    role: Optional[str] = Query(default=None, description="Filtra por role")
    status: Optional[str] = Query(default=None, description="Filtra por status")
    page: int = Query(default=1, ge=1)
    page_size: int = Query(default=20, ge=1, le=100)


class CreateUserRequest(BaseModel):
    name: str
    login: str
    email: str
    password: str
    role: str

    @field_validator("login")
    @classmethod
    def validate_login(cls, v: str) -> str:
        if len(v) < 3 or " " in v:
            raise ValueError("Login deve ter no mínimo 3 caracteres e não pode conter espaços")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not _EMAIL_RE.match(v):
            raise ValueError("Email inválido")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Senha deve ter no mínimo 8 caracteres")
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in _VALID_ROLES:
            raise ValueError(f"Role inválido. Aceitos: {', '.join(sorted(_VALID_ROLES))}")
        return v


class UpdateUserRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not _EMAIL_RE.match(v):
            raise ValueError("Email inválido")
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in _VALID_ROLES:
            raise ValueError(f"Role inválido. Aceitos: {', '.join(sorted(_VALID_ROLES))}")
        return v


class UpdateStatusRequest(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in _VALID_STATUSES:
            raise ValueError("Status deve ser 'active' ou 'inactive'")
        return v


class StatusUpdateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    updated_at: datetime
