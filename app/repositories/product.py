from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.product import Product


class ProductRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(
        self,
        product_id: UUID,
        tenant_id: UUID,
    ) -> Product | None:
        statement = select(Product).where(
            Product.id == product_id,
            Product.tenant_id == tenant_id,
        )

        return self.db.scalar(statement)

    def get_by_name(
        self,
        name: str,
        tenant_id: UUID,
    ) -> Product | None:
        statement = select(Product).where(
            Product.name == name,
            Product.tenant_id == tenant_id,
        )

        return self.db.scalar(statement)

    def get_all(
        self,
        tenant_id: UUID,
    ) -> list[Product]:
        statement = (
            select(Product)
            .where(Product.tenant_id == tenant_id)
            .order_by(Product.name.asc())
        )

        return list(self.db.scalars(statement).all())