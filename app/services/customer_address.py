from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.database.models.customer import Customer
from app.database.models.customer_address import CustomerAddress
from app.repositories.customer_address import CustomerAddressRepository
from app.schemas.customer_address import CustomerAddressCreate


def create_customer_address(
    db: Session,
    tenant_id: UUID,
    customer_id: UUID,
    data: CustomerAddressCreate,
) -> CustomerAddress:
    """Create an address for a customer within the current tenant."""

    customer = db.get(Customer, customer_id)

    if customer is None or customer.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found.",
        )

    address_repository = CustomerAddressRepository(db)

    try:
        if data.is_default:
            current_default = address_repository.get_default_address(
                tenant_id=tenant_id,
                customer_id=customer_id,
            )

            if current_default is not None:
                current_default.is_default = False

        address = CustomerAddress(
            tenant_id=tenant_id,
            customer_id=customer_id,
            label=data.label,
            recipient_name=data.recipient_name,
            phone=data.phone,
            address_line=data.address_line,
            city=data.city,
            postal_code=data.postal_code,
            is_default=data.is_default,
        )

        db.add(address)
        db.commit()
        db.refresh(address)

        return address

    except Exception:
        db.rollback()
        raise