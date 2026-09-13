from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.customer_address import CustomerAddress


class CustomerAddressRepository:
    """Provide database access for customer addresses."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(
        self,
        address_id: UUID,
        tenant_id: UUID,
        customer_id: UUID,
    ) -> CustomerAddress | None:
        """Find an address belonging to a customer within a tenant."""

        statement = select(CustomerAddress).where(
            CustomerAddress.id == address_id,
            CustomerAddress.tenant_id == tenant_id,
            CustomerAddress.customer_id == customer_id,
        )

        return self.db.scalar(statement)

    def get_default_address(
        self,
        tenant_id: UUID,
        customer_id: UUID,
    ) -> CustomerAddress | None:
        """Find the default address of a customer."""

        statement = select(CustomerAddress).where(
            CustomerAddress.tenant_id == tenant_id,
            CustomerAddress.customer_id == customer_id,
            CustomerAddress.is_default.is_(True),
        )

        return self.db.scalar(statement)