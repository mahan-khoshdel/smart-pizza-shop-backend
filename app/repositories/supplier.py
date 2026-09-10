from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.supplier import Supplier


class SupplierRepository:
    """Handle database operations related to suppliers."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(
        self,
        supplier_id: UUID,
        tenant_id: UUID,
    ) -> Supplier | None:
        """Find a supplier by ID within a specific tenant."""
        statement = select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.tenant_id == tenant_id,
        )

        return self.db.scalar(statement)