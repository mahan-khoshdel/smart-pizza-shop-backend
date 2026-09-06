from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.user_role import UserRole


class UserRoleRepository:
    """Handle database operations related to user-role assignments."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def has_role(
        self,
        user_id: UUID,
        role_id: UUID,
    ) -> bool:
        """Check whether a user has a specific role."""
        statement = select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id,
        )

        return self.db.scalar(statement) is not None