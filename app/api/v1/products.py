from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_data
from app.database.connection import get_db
from app.schemas.product import ProductCreate, ProductResponse
from app.services.product import create_product, get_products


router = APIRouter(
    prefix="/products",
    tags=["Products"],
)


@router.post(
    "",
    response_model=ProductResponse,
    status_code=201,
)
def create_product_endpoint(
    product_data: ProductCreate,
    current_user=Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Create a new product for the current tenant.
    """

    return create_product(
        db=db,
        tenant_id=current_user["tenant_id"],
        data=product_data,
    )


@router.get(
    "",
    response_model=list[ProductResponse],
)
def get_products_endpoint(
    current_user=Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Return all products for the current tenant.
    """

    return get_products(
        db=db,
        tenant_id=current_user["tenant_id"],
    )