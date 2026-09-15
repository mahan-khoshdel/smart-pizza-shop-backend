from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.category import Category


class CategoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(
        self,
        category_id: UUID,
        tenant_id: UUID,
    ) -> Category | None:
        statement = select(Category).where(
            Category.id == category_id,
            Category.tenant_id == tenant_id,
        )

        return self.db.scalar(statement)

    def get_by_name(
        self,
        name: str,
        tenant_id: UUID,
    ) -> Category | None:
        statement = select(Category).where(
            Category.name == name,
            Category.tenant_id == tenant_id,
        )

        return self.db.scalar(statement)

    def get_all(
        self,
        tenant_id: UUID,
    ) -> list[Category]:
        statement = (
            select(Category)
            .where(Category.tenant_id == tenant_id)
            .order_by(Category.name.asc())
        )

        return list(self.db.scalars(statement).all())