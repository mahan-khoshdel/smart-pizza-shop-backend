from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.permission import Permission
from app.database.models.role import Role
from app.database.models.role_permission import RolePermission


def create_role(
    db: Session,
    tenant_id: UUID,
    name: str,
    description: str | None = None,
) -> Role:
    """Create a role for a specific tenant."""

    role = Role(
        tenant_id=tenant_id,
        name=name,
        description=description,
    )

    db.add(role)
    db.flush()

    return role


def add_permission_to_role(
    db: Session,
    role_id: UUID,
    permission_code: str,
) -> None:
    """Assign a system permission to a role."""

    permission = db.scalar(
        select(Permission).where(
            Permission.code == permission_code,
        )
    )

    if permission is None:
        raise ValueError(
            f"Permission '{permission_code}' does not exist."
        )

    existing_assignment = db.scalar(
        select(RolePermission).where(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission.id,
        )
    )

    if existing_assignment is None:
        db.add(
            RolePermission(
                role_id=role_id,
                permission_id=permission.id,
            )
        )