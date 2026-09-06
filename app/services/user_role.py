from uuid import UUID

from sqlalchemy.orm import Session

from app.database.models.user_role import UserRole


def assign_role_to_user(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    role_id: UUID,
) -> None:
    """Assign a role to a user within a tenant."""

    assignment = UserRole(
        tenant_id=tenant_id,
        user_id=user_id,
        role_id=role_id,
    )

    db.add(assignment)
    db.flush()