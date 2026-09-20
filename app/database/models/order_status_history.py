from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class OrderStatusHistory(Base):
    """
    Stores the status changes of an order over time.
    """

    __tablename__ = "order_status_history"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    order_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "orders.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    from_status: Mapped[str | None] = mapped_column(
        Enum(
            "REGISTERED",
            "PREPARING",
            "READY",
            "COMPLETED",
            "CANCELLED",
            name="order_status_enum",
        ),
        nullable=True,
    )

    to_status: Mapped[str] = mapped_column(
        Enum(
            "REGISTERED",
            "PREPARING",
            "READY",
            "COMPLETED",
            "CANCELLED",
            name="order_status_enum",
        ),
        nullable=False,
    )

    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )