from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.database.models.customer import Customer
from app.database.models.customer_address import CustomerAddress
from app.repositories.customer_address import CustomerAddressRepository
from app.schemas.customer_address import (
    CustomerAddressCreate,
    CustomerAddressUpdate,
)


def get_customer(
    db: Session,
    tenant_id: UUID,
    customer_id: UUID,
) -> Customer:
    """Find a customer within the current tenant."""

    customer = db.get(Customer, customer_id)

    if customer is None or customer.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found.",
        )

    return customer


def create_customer_address(
    db: Session,
    tenant_id: UUID,
    customer_id: UUID,
    data: CustomerAddressCreate,
) -> CustomerAddress:
    """Create an address for a customer within the current tenant."""

    get_customer(
        db=db,
        tenant_id=tenant_id,
        customer_id=customer_id,
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


def get_customer_addresses(
    db: Session,
    tenant_id: UUID,
    customer_id: UUID,
) -> list[CustomerAddress]:
    """Return all addresses belonging to a customer."""

    get_customer(
        db=db,
        tenant_id=tenant_id,
        customer_id=customer_id,
    )

    address_repository = CustomerAddressRepository(db)

    return address_repository.get_all(
        tenant_id=tenant_id,
        customer_id=customer_id,
    )


def get_customer_address(
    db: Session,
    tenant_id: UUID,
    customer_id: UUID,
    address_id: UUID,
) -> CustomerAddress:
    """Return one customer address within the current tenant."""

    get_customer(
        db=db,
        tenant_id=tenant_id,
        customer_id=customer_id,
    )

    address_repository = CustomerAddressRepository(db)

    address = address_repository.get_by_id(
        address_id=address_id,
        tenant_id=tenant_id,
        customer_id=customer_id,
    )

    if address is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer address not found.",
        )

    return address


def update_customer_address(
    db: Session,
    tenant_id: UUID,
    customer_id: UUID,
    address_id: UUID,
    data: CustomerAddressUpdate,
) -> CustomerAddress:
    """
    Update an existing customer address.

    If the address becomes the default address, the previous default
    address is unset first to satisfy the database unique constraint.
    """

    address = get_customer_address(
        db=db,
        tenant_id=tenant_id,
        customer_id=customer_id,
        address_id=address_id,
    )

    repository = CustomerAddressRepository(db)

    try:
        update_data = data.model_dump(exclude_unset=True)

        # If this address is becoming the default,
        # remove the previous default first.
        if update_data.get("is_default") is True:
            current_default = repository.get_default_address(
                tenant_id=tenant_id,
                customer_id=customer_id,
            )

            if current_default is not None and current_default.id != address.id:
                current_default.is_default = False

                # Important:
                # Send the old default change to PostgreSQL
                # before setting the new address as default.
                db.flush()

        # Apply the requested changes.
        for field, value in update_data.items():
            setattr(address, field, value)

        db.commit()
        db.refresh(address)

        return address

    except Exception:
        db.rollback()
        raise


def delete_customer_address(
    db: Session,
    tenant_id: UUID,
    customer_id: UUID,
    address_id: UUID,
) -> None:
    """Delete a customer address within the current tenant."""

    address = get_customer_address(
        db=db,
        tenant_id=tenant_id,
        customer_id=customer_id,
        address_id=address_id,
    )

    try:
        db.delete(address)
        db.commit()

    except Exception:
        db.rollback()
        raise