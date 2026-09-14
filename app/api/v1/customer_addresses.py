from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_data
from app.core.dependencies import get_db
from app.schemas.customer_address import (
    CustomerAddressCreate,
    CustomerAddressResponse,
    CustomerAddressUpdate,
)
from app.services.customer_address import (
    create_customer_address,
    delete_customer_address,
    get_customer_address,
    get_customer_addresses,
    update_customer_address,
)


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


@router.get(
    "/{customer_id}/addresses",
    response_model=list[CustomerAddressResponse],
)
def get_customer_addresses_endpoint(
    customer_id: UUID,
    current_user: dict[str, UUID] = Depends(get_current_user_data),
    db: Session = Depends(get_db),
) -> list[CustomerAddressResponse]:
    """Return all addresses of a customer."""

    return get_customer_addresses(
        db=db,
        tenant_id=current_user["tenant_id"],
        customer_id=customer_id,
    )


@router.get(
    "/{customer_id}/addresses/{address_id}",
    response_model=CustomerAddressResponse,
)
def get_customer_address_endpoint(
    customer_id: UUID,
    address_id: UUID,
    current_user: dict[str, UUID] = Depends(get_current_user_data),
    db: Session = Depends(get_db),
) -> CustomerAddressResponse:
    """Return one customer address."""

    return get_customer_address(
        db=db,
        tenant_id=current_user["tenant_id"],
        customer_id=customer_id,
        address_id=address_id,
    )


@router.put(
    "/{customer_id}/addresses/{address_id}",
    response_model=CustomerAddressResponse,
)
def update_customer_address_endpoint(
    customer_id: UUID,
    address_id: UUID,
    address_data: CustomerAddressUpdate,
    current_user: dict[str, UUID] = Depends(get_current_user_data),
    db: Session = Depends(get_db),
) -> CustomerAddressResponse:
    """Update a customer address."""

    return update_customer_address(
        db=db,
        tenant_id=current_user["tenant_id"],
        customer_id=customer_id,
        address_id=address_id,
        data=address_data,
    )


@router.delete(
    "/{customer_id}/addresses/{address_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_customer_address_endpoint(
    customer_id: UUID,
    address_id: UUID,
    current_user: dict[str, UUID] = Depends(get_current_user_data),
    db: Session = Depends(get_db),
) -> None:
    """Delete a customer address."""

    delete_customer_address(
        db=db,
        tenant_id=current_user["tenant_id"],
        customer_id=customer_id,
        address_id=address_id,
    )