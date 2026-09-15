from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProductCreate(BaseModel):
    category_id: UUID
    name: str
    description: str | None = None


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    category_id: UUID
    name: str
    description: str | None
    is_active: bool