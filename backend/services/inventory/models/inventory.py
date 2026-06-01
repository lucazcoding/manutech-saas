from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, Enum as SAEnum, func, Numeric, String, Text, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from shared.shared.db.session import Base


class Material(Base):
    __tablename__ = "materials"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sku: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    quantity_in_stock: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False, default=0)
    min_quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False, default=5)
    status: Mapped[str] = mapped_column(
        SAEnum("active", "inactive", name="material_status"),
        nullable=False,
        default="active",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class StockMovement(Base):
    __tablename__ = "stock_movements"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    material_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    service_order_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    movement_type: Mapped[str] = mapped_column(
        SAEnum("in", "out", name="movement_type"),
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
