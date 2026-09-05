from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """Credentials required to log in."""

    tenant_slug: str
    email: EmailStr
    password: str