from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.customer import Customer


class CustomerRepository:
    """Provide database access for customers."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(
        self,
        customer_id: UUID,
        tenant_id: UUID,
    ) -> Customer | None:
        """Find a customer within a tenant."""

        statement = select(Customer).where(
            Customer.id == customer_id,
            Customer.tenant_id == tenant_id,
        )

        return self.db.scalar(statement)