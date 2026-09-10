from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class InventoryMovement(Base):
    """Represent a change in inventory quantity."""

    __tablename__ = "inventory_movements"

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
    
    inventory_batch_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "inventory_batches.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    movement_type: Mapped[str] = mapped_column(
        Enum(
            "PURCHASE",
            "SALE_CONSUMPTION",
            "WASTE",
            "ADJUSTMENT",
            "RETURN",
            "TRANSFER_IN",
            "TRANSFER_OUT",
            name="inventory_movement_type",
        ),
        nullable=False,
    )

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(14, 3),
        nullable=False,
    )

    note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )