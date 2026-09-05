from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.user import User


class UserRepository:
    """Handle database operations related to users."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_email(
        self,
        email: str,
        tenant_id: UUID,
    ) -> User | None:
        """Find a user by email within a specific tenant."""
        statement = select(User).where(
            User.email == email,
            User.tenant_id == tenant_id,
        )

        return self.db.scalar(statement)

    def get_by_id(
        self,
        user_id: UUID,
        tenant_id: UUID,
    ) -> User | None:
        """Find a user by ID within a specific tenant."""
        statement = select(User).where(
            User.id == user_id,
            User.tenant_id == tenant_id,
        )

        return self.db.scalar(statement)