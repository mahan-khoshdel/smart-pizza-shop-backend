from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.role import Role


class RoleRepository:
    """Handle database operations related to roles."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(
        self,
        role_id: UUID,
        tenant_id: UUID,
    ) -> Role | None:
        """Find a role by ID within a specific tenant."""
        statement = select(Role).where(
            Role.id == role_id,
            Role.tenant_id == tenant_id,
        )

        return self.db.scalar(statement)