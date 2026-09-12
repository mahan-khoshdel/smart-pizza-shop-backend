from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class InventoryConsumeRequest(BaseModel):
    """Represent a request to consume ingredient inventory."""

    branch_id: UUID
    ingredient_id: UUID
    quantity: Decimal = Field(gt=0)