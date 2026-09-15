from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_data
from app.database.connection import get_db
from app.schemas.category import CategoryCreate, CategoryResponse
from app.services.category import create_category, get_categories


router = APIRouter(
    prefix="/categories",
    tags=["Categories"],
)


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=201,
)
def create_category_endpoint(
    category_data: CategoryCreate,
    current_user=Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Create a new category for the current tenant.
    """

    return create_category(
        db=db,
        tenant_id=current_user["tenant_id"],
        data=category_data,
    )


@router.get(
    "",
    response_model=list[CategoryResponse],
)
def get_categories_endpoint(
    current_user=Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Return all categories for the current tenant.
    """

    return get_categories(
        db=db,
        tenant_id=current_user["tenant_id"],
    )