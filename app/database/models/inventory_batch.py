from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class InventoryBatch(Base):
    """Represent a batch of an ingredient received into inventory."""

    __tablename__ = "inventory_batches"

    __table_args__ = (
        UniqueConstraint(
            "inventory_item_id",
            "batch_number",
            name="uq_inventory_batches_item_batch",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    inventory_item_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "inventory_items.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    batch_number: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(14, 3),
        nullable=False,
    )

    cost_per_unit: Mapped[Decimal] = mapped_column(
        Numeric(14, 3),
        nullable=False,
    )

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )