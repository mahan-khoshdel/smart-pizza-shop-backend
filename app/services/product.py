from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.category import Category
from app.database.models.product import Product
from app.repositories.product import ProductRepository
from app.schemas.product import ProductCreate


def create_product(
    db: Session,
    tenant_id: UUID,
    data: ProductCreate,
) -> Product:
    """
    Create a product for the current tenant.
    """

    category = db.scalar(
        select(Category).where(
            Category.id == data.category_id,
            Category.tenant_id == tenant_id,
        )
    )

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found.",
        )

    repository = ProductRepository(db)

    existing_product = repository.get_by_name(
        name=data.name,
        tenant_id=tenant_id,
    )

    if existing_product is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product name already exists.",
        )

    product = Product(
        tenant_id=tenant_id,
        category_id=data.category_id,
        name=data.name,
        description=data.description,
    )

    try:
        db.add(product)
        db.commit()
        db.refresh(product)

        return product

    except Exception:
        db.rollback()
        raise


def get_products(
    db: Session,
    tenant_id: UUID,
) -> list[Product]:
    """
    Return all products belonging to the current tenant.
    """

    repository = ProductRepository(db)

    return repository.get_all(tenant_id=tenant_id)