from datetime import datetime
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


class PurchaseItemResponse(BaseModel):
    """Represent a purchase item in API responses."""

    id: UUID
    purchase_id: UUID
    ingredient_id: UUID
    quantity: Decimal
    unit: str
    unit_cost: Decimal
    total_cost: Decimal


class PurchaseListItemResponse(BaseModel):
    """Represent one purchase in a purchase list."""

    id: UUID
    tenant_id: UUID
    branch_id: UUID
    supplier_id: UUID
    purchase_number: str
    purchase_date: datetime
    status: str
    note: str | None
    created_at: datetime
    updated_at: datetime


class PurchaseListResponse(BaseModel):
    """Represent a filtered purchase list."""

    items: list[PurchaseListItemResponse]
    total_count: int


class PurchaseDetailResponse(BaseModel):
    """Represent a purchase with its items."""

    id: UUID
    tenant_id: UUID
    branch_id: UUID
    supplier_id: UUID
    purchase_number: str
    purchase_date: datetime
    status: str
    note: str | None
    created_at: datetime
    updated_at: datetime
    items: list[PurchaseItemResponse]
    
    
class PurchaseSummaryResponse(BaseModel):
    """Represent aggregated purchase statistics."""

    branch_id: UUID | None
    supplier_id: UUID | None

    total_purchase_count: int
    total_purchase_cost: Decimal

    draft_purchase_count: int
    received_purchase_count: int
    cancelled_purchase_count: int