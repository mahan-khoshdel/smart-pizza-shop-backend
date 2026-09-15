from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProductVariantCreate(BaseModel):
    product_id: UUID
    name: str
    sku: str
    price: int


class ProductVariantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    product_id: UUID
    name: str
    sku: str
    price: int
    is_available: bool