from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class LowStockResponse(BaseModel):
    """Represent an inventory item that is at or below reorder level."""

    inventory_item_id: UUID
    branch_id: UUID
    ingredient_id: UUID
    quantity: Decimal
    reorder_level: Decimal
    shortage_quantity: Decimal


class ExpiryBatchResponse(BaseModel):
    """Represent an inventory batch with expiry information."""

    inventory_batch_id: UUID
    inventory_item_id: UUID
    branch_id: UUID
    ingredient_id: UUID
    batch_number: str
    quantity: Decimal
    expires_at: datetime
    days_until_expiry: int
    is_expired: bool
    is_expiring_soon: bool


class ExpirySummaryResponse(BaseModel):
    """Represent inventory expiry information for a branch."""

    branch_id: UUID
    expiring_soon_days: int
    expired_count: int
    expiring_soon_count: int
    batches: list[ExpiryBatchResponse]

    
class InventorySummaryResponse(BaseModel):
    """Represent inventory summary information for a branch."""

    branch_id: UUID

    active_inventory_item_count: int
    low_stock_count: int

    expired_batch_count: int
    expiring_soon_batch_count: int

    expiring_soon_days: int
    
    
class InventoryValuationResponse(BaseModel):
    """Represent the monetary value of inventory for a branch."""

    branch_id: UUID

    total_inventory_value: Decimal
    low_stock_inventory_value: Decimal

    expired_inventory_value: Decimal
    expiring_soon_inventory_value: Decimal

    expiring_soon_days: int
    

class InventoryConsumptionIngredientResponse(BaseModel):
    """Represent consumption analytics for one ingredient."""

    ingredient_id: UUID
    movement_count: int
    consumed_quantity: Decimal
    consumption_value: Decimal


class InventoryConsumptionResponse(BaseModel):
    """Represent inventory consumption analytics for a branch."""

    branch_id: UUID

    total_movement_count: int
    ingredient_count: int
    total_consumption_value: Decimal

    ingredients: list[InventoryConsumptionIngredientResponse]