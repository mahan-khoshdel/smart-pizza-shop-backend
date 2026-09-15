from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_data
from app.database.connection import get_db
from app.schemas.product_variant import (
    ProductVariantCreate,
    ProductVariantResponse,
)
from app.services.product_variant import (
    create_product_variant,
    get_product_variants,
)


router = APIRouter(
    prefix="/product-variants",
    tags=["Product Variants"],
)


@router.post(
    "",
    response_model=ProductVariantResponse,
    status_code=201,
)
def create_product_variant_endpoint(
    variant_data: ProductVariantCreate,
    current_user=Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Create a new product variant for the current tenant.
    """

    return create_product_variant(
        db=db,
        tenant_id=current_user["tenant_id"],
        data=variant_data,
    )


@router.get(
    "",
    response_model=list[ProductVariantResponse],
)
def get_product_variants_endpoint(
    current_user=Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Return all product variants for the current tenant.
    """

    return get_product_variants(
        db=db,
        tenant_id=current_user["tenant_id"],
    )