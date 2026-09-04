from uuid import UUID

from sqlalchemy import ForeignKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class UserRole(Base):
    """Represent a role assigned to a user within a tenant."""

    __tablename__ = "user_roles"

    tenant_id: Mapped[UUID] = mapped_column(
        nullable=False,
    )

    user_id: Mapped[UUID] = mapped_column(
        primary_key=True,
    )

    role_id: Mapped[UUID] = mapped_column(
        primary_key=True,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "user_id"],
            ["users.tenant_id", "users.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "role_id"],
            ["roles.tenant_id", "roles.id"],
            ondelete="CASCADE",
        ),
    )