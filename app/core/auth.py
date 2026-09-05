from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.core.security import decode_access_token
from app.repositories.user import UserRepository


bearer_scheme = HTTPBearer()


def get_current_user_data(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> dict[str, UUID]:
    """Return authenticated user and tenant identifiers from the JWT."""

    try:
        payload = decode_access_token(credentials.credentials)

        user_id = UUID(payload["sub"])
        tenant_id = UUID(payload["tenant_id"])

    except (KeyError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_repository = UserRepository(db)

    user = user_repository.get_by_id(
        user_id=user_id,
        tenant_id=tenant_id,
    )

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "user_id": user.id,
        "tenant_id": user.tenant_id,
    }