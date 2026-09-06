from decimal import Decimal
from uuid import UUID

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class RecipeItem(Base):
    """Represent an ingredient and its quantity in a recipe."""

    __tablename__ = "recipe_items"

    recipe_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "recipes.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    ingredient_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "ingredients.id",
            ondelete="RESTRICT",
        ),
        primary_key=True,
    )

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        nullable=False,
    )