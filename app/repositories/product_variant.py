from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.product_variant import ProductVariant


class ProductVariantRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(
        self,
        variant_id: UUID,
        tenant_id: UUID,
    ) -> ProductVariant | None:
        statement = select(ProductVariant).where(
            ProductVariant.id == variant_id,
            ProductVariant.tenant_id == tenant_id,
        )

        return self.db.scalar(statement)

    def get_by_sku(
        self,
        sku: str,
        tenant_id: UUID,
    ) -> ProductVariant | None:
        statement = select(ProductVariant).where(
            ProductVariant.sku == sku,
            ProductVariant.tenant_id == tenant_id,
        )

        return self.db.scalar(statement)

    def get_by_product_and_name(
        self,
        product_id: UUID,
        name: str,
    ) -> ProductVariant | None:
        statement = select(ProductVariant).where(
            ProductVariant.product_id == product_id,
            ProductVariant.name == name,
        )

        return self.db.scalar(statement)

    def get_all(
        self,
        tenant_id: UUID,
    ) -> list[ProductVariant]:
        statement = (
            select(ProductVariant)
            .where(ProductVariant.tenant_id == tenant_id)
            .order_by(ProductVariant.name.asc())
        )

        return list(self.db.scalars(statement).all())