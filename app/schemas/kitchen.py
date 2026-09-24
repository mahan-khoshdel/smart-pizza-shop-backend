from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class KitchenQueueOrderResponse(BaseModel):
    """Represent an order and its current kitchen queue position."""

    order_id: UUID
    order_number: str
    queue_position: int
    status: str
    created_at: datetime


class KitchenQueueResponse(BaseModel):
    """Represent the preparing-order queue for a branch."""

    branch_id: UUID
    total_preparing: int
    queue: list[KitchenQueueOrderResponse]