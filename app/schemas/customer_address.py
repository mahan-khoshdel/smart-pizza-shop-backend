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


class CustomerAddressUpdate(BaseModel):
    """Represent customer address update data."""

    label: str | None = None
    recipient_name: str | None = None
    phone: str | None = None
    address_line: str | None = None
    city: str | None = None
    postal_code: str | None = None
    is_default: bool | None = None


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