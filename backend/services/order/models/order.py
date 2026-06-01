from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    Enum as SAEnum,
    func,
    Identity,
    Numeric,
    String,
    Text,
    TIMESTAMP,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shared.shared.db.session import Base


class ServiceOrder(Base):
    __tablename__ = "service_orders"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    order_number: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False, unique=True)
    client_name: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        SAEnum("open", "in_progress", "completed", "cancelled", name="order_status"),
        nullable=False,
        default="open",
    )
    priority: Mapped[str] = mapped_column(
        SAEnum("low", "medium", "high", "urgent", name="order_priority"),
        nullable=False,
        default="medium",
    )
    total_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    start_date: Mapped[Optional[date]] = mapped_column(Date)
    asset_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class OrderAssignment(Base):
    __tablename__ = "order_assignments"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    service_order_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    technician_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    unassigned_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class OrderAttachment(Base):
    __tablename__ = "attachments"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    service_order_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    uploaded_by: Mapped[Optional[int]] = mapped_column(BigInteger)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    table_name: Mapped[str] = mapped_column(String(100), nullable=False)
    record_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    action: Mapped[str] = mapped_column(
        SAEnum("INSERT", "UPDATE", "DELETE", name="audit_action"),
        nullable=False,
    )
    delta: Mapped[dict] = mapped_column(JSONB, nullable=False)
    changed_by: Mapped[Optional[int]] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class OrderUser(Base):
    """Read-only reference to users table for technician lookups."""

    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    role: Mapped[str] = mapped_column(
        SAEnum("admin", "supervisor", "technician", "attendant", name="user_role"),
        nullable=False,
    )


class OrderAsset(Base):
    """Read-only reference to assets table."""

    __tablename__ = "assets"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    serial_number: Mapped[Optional[str]] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(
        SAEnum("active", "inactive", name="asset_status"),
        nullable=False,
    )
