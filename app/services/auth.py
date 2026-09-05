from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.repositories.tenant import TenantRepository
from app.repositories.user import UserRepository


def login_user(
    db: Session,
    tenant_slug: str,
    email: str,
    password: str,
) -> str:
    """Authenticate a user and return an access token."""

    tenant_repository = TenantRepository(db)
    user_repository = UserRepository(db)

    tenant = tenant_repository.get_by_slug(tenant_slug)

    if tenant is None or tenant.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid tenant or credentials.",
        )

    user = user_repository.get_by_email(
        email=email,
        tenant_id=tenant.id,
    )

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid tenant or credentials.",
        )

    if not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid tenant or credentials.",
        )

    return create_access_token(
        user_id=str(user.id),
        tenant_id=str(tenant.id),
    )