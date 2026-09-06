from collections.abc import Callable
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_data
from app.core.dependencies import get_db
from app.services.authorization import user_has_permission


def require_permission(permission_code: str) -> Callable:
    """Create a dependency requiring a specific permission."""

    def permission_checker(
        current_user: dict[str, UUID] = Depends(get_current_user_data),
        db: Session = Depends(get_db),
    ) -> None:
        has_permission = user_has_permission(
            db=db,
            user_id=current_user["user_id"],
            tenant_id=current_user["tenant_id"],
            permission_code=permission_code,
        )

        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )

    return permission_checker