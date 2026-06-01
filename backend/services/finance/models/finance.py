from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, Date, Enum as SAEnum, func, Identity, Numeric, String, Text, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from shared.shared.db.session import Base


class ServiceCost(Base):
    __tablename__ = "service_costs"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    service_order_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    cost_type: Mapped[str] = mapped_column(
        SAEnum("material", "labor", "service", "other", name="cost_type"),
        nullable=False,
        default="other",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class Budget(Base):
    __tablename__ = "budgets"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    budget_number: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False, unique=True)
    service_order_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    client_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        SAEnum("draft", "sent", "approved", "rejected", "expired", name="budget_status"),
        nullable=False,
        default="draft",
    )
    valid_until: Mapped[Optional[date]] = mapped_column(Date)
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class BudgetItem(Base):
    __tablename__ = "budget_items"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    budget_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


class FinanceOrder(Base):
    """Read-only reference to service_orders for cost/budget linkage."""

    __tablename__ = "service_orders"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        SAEnum("open", "in_progress", "completed", "cancelled", name="order_status"),
        nullable=False,
    )
