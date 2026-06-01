from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Enum as SAEnum, func, String, Text, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from shared.shared.db.session import Base


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    model: Mapped[Optional[str]] = mapped_column(String(150))
    manufacturer: Mapped[Optional[str]] = mapped_column(String(150))
    serial_number: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    location: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        SAEnum("active", "inactive", name="asset_status"),
        nullable=False,
        default="active",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
