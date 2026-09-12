from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PurchaseReceiveItem(BaseModel):
    """Represent batch information when receiving a purchase item."""

    purchase_item_id: UUID
    batch_number: str = Field(min_length=1, max_length=100)
    expires_at: datetime | None = None


class PurchaseReceiveRequest(BaseModel):
    """Represent the data required to receive a purchase."""

    items: list[PurchaseReceiveItem]