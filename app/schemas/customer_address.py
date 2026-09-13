from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CustomerAddressCreate(BaseModel):
    """Represent customer address creation data."""

    label: str
    recipient_name: str
    phone: str
    address_line: str
    city: str
    postal_code: str | None = None
    is_default: bool = False


class CustomerAddressResponse(BaseModel):
    """Represent a customer address API response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    label: str
    recipient_name: str
    phone: str
    address_line: str
    city: str
    postal_code: str | None
    is_default: bool