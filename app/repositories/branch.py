from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.branch import Branch


class BranchRepository:
    """Handle database operations related to branches."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(
        self,
        branch_id: UUID,
        tenant_id: UUID,
    ) -> Branch | None:
        """Find a branch by ID within a specific tenant."""
        statement = select(Branch).where(
            Branch.id == branch_id,
            Branch.tenant_id == tenant_id,
        )

        return self.db.scalar(statement)