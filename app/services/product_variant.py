from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.product import Product
from app.database.models.product_variant import ProductVariant
from app.repositories.product_variant import ProductVariantRepository
from app.schemas.product_variant import ProductVariantCreate


def create_product_variant(
    db: Session,
    tenant_id: UUID,
    data: ProductVariantCreate,
) -> ProductVariant:
    """
    Create a sellable product variant for the current tenant.
    """

    product = db.scalar(
        select(Product).where(
            Product.id == data.product_id,
            Product.tenant_id == tenant_id,
        )
    )

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    if data.price < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Price cannot be negative.",
        )

    repository = ProductVariantRepository(db)

    existing_sku = repository.get_by_sku(
        sku=data.sku,
        tenant_id=tenant_id,
    )

    if existing_sku is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="SKU already exists.",
        )

    existing_name = repository.get_by_product_and_name(
        product_id=data.product_id,
        name=data.name,
    )

    if existing_name is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Variant name already exists for this product.",
        )

    variant = ProductVariant(
        tenant_id=tenant_id,
        product_id=data.product_id,
        name=data.name,
        sku=data.sku,
        price=data.price,
    )

    try:
        db.add(variant)
        db.commit()
        db.refresh(variant)

        return variant

    except Exception:
        db.rollback()
        raise


def get_product_variants(
    db: Session,
    tenant_id: UUID,
) -> list[ProductVariant]:
    """
    Return all product variants belonging to the current tenant.
    """

    repository = ProductVariantRepository(db)

    return repository.get_all(tenant_id=tenant_id)