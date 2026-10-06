from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.category import Category
from app.database.models.product import Product
from app.repositories.product import ProductRepository
from app.schemas.product import ProductCreate
from app.services.product import create_product, get_products


TENANT_ID = UUID("25291ef5-0240-4042-aabc-b92c5aa4957a")
FAKE_OTHER_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
NON_EXISTENT_CATEGORY_ID = UUID(
    "00000000-0000-0000-0000-000000000088"
)


def _get_existing_category_id(
    db: Session,
    tenant_id: UUID,
) -> UUID:
    category = db.scalar(
        select(Category).where(
            Category.tenant_id == tenant_id,
        )
    )

    assert category is not None, (
        "No category was found for the test tenant."
    )

    return category.id


def test_create_product_successfully(db_session):
    category_id = _get_existing_category_id(
        db=db_session,
        tenant_id=TENANT_ID,
    )

    product_name = f"TEST-PRODUCT-{uuid4().hex[:8]}"

    product_data = ProductCreate(
        category_id=category_id,
        name=product_name,
        description="Automated Product Service test.",
    )

    created_product = create_product(
        db=db_session,
        tenant_id=TENANT_ID,
        data=product_data,
    )

    assert isinstance(created_product, Product)
    assert created_product.tenant_id == TENANT_ID
    assert created_product.category_id == category_id
    assert created_product.name == product_name
    assert (
        created_product.description
        == "Automated Product Service test."
    )

    repository = ProductRepository(db_session)

    stored_product = repository.get_by_id(
        product_id=created_product.id,
        tenant_id=TENANT_ID,
    )

    assert stored_product is not None
    assert stored_product.id == created_product.id
    assert stored_product.tenant_id == TENANT_ID


def test_create_product_rejects_duplicate_name(db_session):
    existing_product = db_session.scalar(
        select(Product).where(
            Product.tenant_id == TENANT_ID,
        )
    )

    assert existing_product is not None, (
        "No existing product was found for duplicate-name testing."
    )

    product_data = ProductCreate(
        category_id=existing_product.category_id,
        name=existing_product.name,
        description=existing_product.description,
    )

    with pytest.raises(HTTPException) as exc_info:
        create_product(
            db=db_session,
            tenant_id=TENANT_ID,
            data=product_data,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Product name already exists."


def test_create_product_rejects_missing_category(db_session):
    product_data = ProductCreate(
        category_id=NON_EXISTENT_CATEGORY_ID,
        name=f"TEST-NO-CATEGORY-{uuid4().hex[:8]}",
        description="Category validation test.",
    )

    with pytest.raises(HTTPException) as exc_info:
        create_product(
            db=db_session,
            tenant_id=TENANT_ID,
            data=product_data,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Category not found."


def test_get_products_is_tenant_scoped(db_session):
    tenant_products = get_products(
        db=db_session,
        tenant_id=TENANT_ID,
    )

    assert all(
        product.tenant_id == TENANT_ID
        for product in tenant_products
    )

    other_tenant_products = get_products(
        db=db_session,
        tenant_id=FAKE_OTHER_TENANT_ID,
    )

    assert other_tenant_products == []
    
    
def test_create_product_rejects_category_from_other_tenant(
    db_session,
):
    category_id = _get_existing_category_id(
        db=db_session,
        tenant_id=TENANT_ID,
    )

    product_data = ProductCreate(
        category_id=category_id,
        name=f"TEST-CROSS-TENANT-{uuid4().hex[:8]}",
        description="Cross-tenant category test.",
    )

    with pytest.raises(HTTPException) as exc_info:
        create_product(
            db=db_session,
            tenant_id=FAKE_OTHER_TENANT_ID,
            data=product_data,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Category not found."