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

    preparation_elapsed_seconds: float | None = None
    preparation_elapsed_minutes: float | None = None

    expected_preparation_seconds: float | None = None
    expected_preparation_minutes: float | None = None

    remaining_preparation_seconds: float | None = None
    remaining_preparation_minutes: float | None = None

    estimated_ready_at: datetime | None = None

    is_overdue: bool = False
    overdue_seconds: float | None = None
    overdue_minutes: float | None = None


class KitchenQueueResponse(BaseModel):
    """Represent the preparing-order queue for a branch."""

    branch_id: UUID
    total_preparing: int
    queue: list[KitchenQueueOrderResponse]