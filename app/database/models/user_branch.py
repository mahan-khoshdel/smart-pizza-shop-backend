from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class UserBranch(Base):
    """Represent a user's access to a branch."""

    __tablename__ = "user_branches"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    branch_id: Mapped[UUID] = mapped_column(
        ForeignKey("branches.id", ondelete="CASCADE"),
        primary_key=True,
    )

    is_primary: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


Index(
    "ix_user_branches_user_primary",
    UserBranch.user_id,
    unique=True,
    postgresql_where=text("is_primary = true"),
)