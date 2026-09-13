from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_data
from app.core.dependencies import get_db
from app.schemas.customer_address import (
    CustomerAddressCreate,
    CustomerAddressResponse,
)
from app.services.customer_address import create_customer_address


router = APIRouter(
    prefix="/customers",
    tags=["Customer Addresses"],
)


@router.post(
    "/{customer_id}/addresses",
    response_model=CustomerAddressResponse,
)
def create_customer_address_endpoint(
    customer_id: UUID,
    address_data: CustomerAddressCreate,
    current_user: dict[str, UUID] = Depends(get_current_user_data),
    db: Session = Depends(get_db),
) -> CustomerAddressResponse:
    """Create an address for a customer."""

    address = create_customer_address(
        db=db,
        tenant_id=current_user["tenant_id"],
        customer_id=customer_id,
        data=address_data,
    )

    return address