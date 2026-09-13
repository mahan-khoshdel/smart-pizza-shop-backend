from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CustomerCreate(BaseModel):
    """Represent customer creation data."""

    first_name: str
    last_name: str
    phone: str | None = None
    email: str | None = None
    notes: str | None = None


class CustomerResponse(BaseModel):
    """Represent a customer API response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str
    last_name: str
    phone: str | None
    email: str | None
    notes: str | None
    is_active: bool