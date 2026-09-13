from uuid import UUID

from sqlalchemy.orm import Session

from app.database.models.customer import Customer
from app.schemas.customer import CustomerCreate


def create_customer(
    db: Session,
    tenant_id: UUID,
    data: CustomerCreate,
) -> Customer:
    """Create a customer for a tenant."""

    customer = Customer(
        tenant_id=tenant_id,
        first_name=data.first_name,
        last_name=data.last_name,
        phone=data.phone,
        email=data.email,
        notes=data.notes,
    )

    db.add(customer)
    db.commit()
    db.refresh(customer)

    return customer