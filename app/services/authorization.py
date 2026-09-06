from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.permission import Permission
from app.database.models.role_permission import RolePermission
from app.database.models.user_role import UserRole


def user_has_permission(
    db: Session,
    user_id: UUID,
    tenant_id: UUID,
    permission_code: str,
) -> bool:
    """Check whether a user has a permission within a tenant."""

    statement = (
        select(Permission.id)
        .join(
            RolePermission,
            RolePermission.permission_id == Permission.id,
        )
        .join(
            UserRole,
            UserRole.role_id == RolePermission.role_id,
        )
        .where(
            UserRole.user_id == user_id,
            UserRole.tenant_id == tenant_id,
            Permission.code == permission_code,
        )
    )

    return db.scalar(statement) is not None