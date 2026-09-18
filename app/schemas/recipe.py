from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RecipeItemCreate(BaseModel):
    ingredient_id: UUID
    quantity: Decimal


class RecipeCreate(BaseModel):
    product_variant_id: UUID
    name: str
    items: list[RecipeItemCreate]


class RecipeItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ingredient_id: UUID
    quantity: Decimal


class RecipeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    product_variant_id: UUID
    name: str
    is_active: bool
    items: list[RecipeItemResponse]