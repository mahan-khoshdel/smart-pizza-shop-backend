from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Enum,
    ForeignKey,
    Numeric,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class PurchaseItem(Base):
    """Represent one ingredient purchased within a purchase."""

    __tablename__ = "purchase_items"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    purchase_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "purchases.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    ingredient_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "ingredients.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(14, 3),
        nullable=False,
    )

    unit: Mapped[str] = mapped_column(
        Enum(
            "GRAM",
            "KILOGRAM",
            "MILLILITER",
            "LITER",
            "PIECE",
            name="purchase_unit",
        ),
        nullable=False,
    )

    unit_cost: Mapped[Decimal] = mapped_column(
        Numeric(16, 2),
        nullable=False,
    )

    total_cost: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )