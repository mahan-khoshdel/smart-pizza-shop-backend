from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_data
from app.core.dependencies import get_db
from app.schemas.auth import LoginRequest
from app.services.auth import login_user


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post("/login")
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Authenticate a user and return an access token."""
    access_token = login_user(
        db=db,
        tenant_slug=login_data.tenant_slug,
        email=login_data.email,
        password=login_data.password,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.get("/me")
def get_me(
    current_user: dict[str, UUID] = Depends(get_current_user_data),
) -> dict[str, str]:
    """Return the identity contained in the access token."""
    return {
        "user_id": str(current_user["user_id"]),
        "tenant_id": str(current_user["tenant_id"]),
    }