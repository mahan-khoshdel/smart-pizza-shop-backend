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
    
    
class SupplierPerformanceItem(BaseModel):
    """Represent purchasing performance for one supplier."""

    supplier_id: UUID
    supplier_name: str
    purchase_count: int
    total_purchase_cost: Decimal
    average_purchase_cost: Decimal
    last_purchase_date: datetime


class SupplierPerformanceResponse(BaseModel):
    """Represent supplier purchasing performance analytics."""

    items: list[SupplierPerformanceItem]

    
class SupplierPriceAnalysisItem(BaseModel):
    """Represent price analysis for one supplier and ingredient."""

    supplier_id: UUID
    supplier_name: str

    ingredient_id: UUID
    ingredient_name: str
    base_unit: str

    purchase_count: int

    first_unit_cost: Decimal
    latest_unit_cost: Decimal
    average_unit_cost: Decimal
    minimum_unit_cost: Decimal
    maximum_unit_cost: Decimal

    price_change_percent: Decimal

    first_purchase_date: datetime
    latest_purchase_date: datetime


class SupplierPriceAnalysisResponse(BaseModel):
    """Represent supplier ingredient price analysis."""

    items: list[SupplierPriceAnalysisItem]
    
    
class PurchaseIngredientCostItem(BaseModel):
    """Represent purchase cost analytics for one ingredient."""

    ingredient_id: UUID
    ingredient_name: str
    base_unit: str

    purchase_count: int
    total_quantity: Decimal
    total_purchase_cost: Decimal
    average_purchase_cost: Decimal
    latest_purchase_cost: Decimal


class PurchaseIngredientCostResponse(BaseModel):
    """Represent purchase cost analytics grouped by ingredient."""

    items: list[PurchaseIngredientCostItem]
    
    
class PurchaseTrendItem(BaseModel):
    """Represent purchase activity for one date."""

    date: datetime
    purchase_count: int
    total_purchase_cost: Decimal


class PurchaseTrendResponse(BaseModel):
    """Represent purchase trends over time."""

    items: list[PurchaseTrendItem]
    
    
class PurchaseDashboardSummaryResponse(BaseModel):
    """Represent the complete purchase dashboard."""

    summary: PurchaseSummaryResponse
    supplier_performance: list[SupplierPerformanceItem]
    supplier_price_analysis: list[SupplierPriceAnalysisItem]
    cost_by_ingredient: list[PurchaseIngredientCostItem]
    trends: list[PurchaseTrendItem]