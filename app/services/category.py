from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.database.models.category import Category
from app.repositories.category import CategoryRepository
from app.schemas.category import CategoryCreate


def create_category(
    db: Session,
    tenant_id: UUID,
    data: CategoryCreate,
) -> Category:
    """
    Create a category for the current tenant.
    """

    repository = CategoryRepository(db)

    existing_category = repository.get_by_name(
        name=data.name,
        tenant_id=tenant_id,
    )

    if existing_category is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category name already exists.",
        )

    category = Category(
        tenant_id=tenant_id,
        name=data.name,
    )

    try:
        db.add(category)
        db.commit()
        db.refresh(category)

        return category

    except Exception:
        db.rollback()
        raise


def get_categories(
    db: Session,
    tenant_id: UUID,
) -> list[Category]:
    """
    Return all categories belonging to the current tenant.
    """

    repository = CategoryRepository(db)

    return repository.get_all(tenant_id=tenant_id)