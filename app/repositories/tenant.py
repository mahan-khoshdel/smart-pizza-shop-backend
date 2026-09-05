from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.tenant import Tenant


class TenantRepository:
    """Handle database operations related to tenants."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_slug(self, slug: str) -> Tenant | None:
        """Find a tenant by its unique slug."""
        statement = select(Tenant).where(Tenant.slug == slug)

        return self.db.scalar(statement)