from uuid import UUID

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict

from app.database.models.order import OrderStatus, OrderType


class OrderItemCreate(BaseModel):
    product_variant_id: UUID
    quantity: int


class OrderCreate(BaseModel):
    branch_id: UUID
    customer_id: UUID | None = None
    customer_address_id: UUID | None = None
    order_number: str
    order_type: OrderType
    note: str | None = None
    items: list[OrderItemCreate]


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_variant_id: UUID
    quantity: int
    unit_price: int
    total_price: int


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    branch_id: UUID
    customer_id: UUID | None

    order_number: str
    order_type: OrderType
    status: OrderStatus
    note: str | None

    delivery_recipient_name: str | None
    delivery_phone: str | None
    delivery_address_line: str | None
    delivery_city: str | None
    delivery_postal_code: str | None

    subtotal: int
    discount_total: int
    tax_total: int
    total: int
    
    inventory_consumed_at: datetime | None

    items: list[OrderItemResponse]
    

class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderIngredientRequirementResponse(BaseModel):
    ingredient_id: UUID
    quantity: Decimal


class OrderIngredientRequirementsResponse(BaseModel):
    order_id: UUID
    requirements: list[OrderIngredientRequirementResponse]