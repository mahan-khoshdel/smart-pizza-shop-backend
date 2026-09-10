from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class PurchaseItemCreate(BaseModel):
    """Represent one item in a purchase."""

    ingredient_id: UUID
    quantity: Decimal
    unit: str
    unit_cost: Decimal


class PurchaseCreate(BaseModel):
    """Represent the data required to create a purchase."""

    branch_id: UUID
    supplier_id: UUID
    purchase_number: str
    items: list[PurchaseItemCreate]
    note: str | None = None