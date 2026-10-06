from uuid import UUID

from sqlalchemy import select

from app.database.models.product import Product
from app.repositories.product import ProductRepository


TENANT_ID = UUID("25291ef5-0240-4042-aabc-b92c5aa4957a")
FAKE_OTHER_TENANT_ID = UUID(
    "00000000-0000-0000-0000-000000000001"
)


def test_product_repository_get_by_id_is_tenant_scoped(db_session):
    existing_product = db_session.scalar(
        select(Product).where(
            Product.tenant_id == TENANT_ID,
        )
    )

    assert existing_product is not None

    repository = ProductRepository(db_session)

    product = repository.get_by_id(
        product_id=existing_product.id,
        tenant_id=TENANT_ID,
    )

    assert product is not None
    assert product.id == existing_product.id
    assert product.tenant_id == TENANT_ID

    other_tenant_product = repository.get_by_id(
        product_id=existing_product.id,
        tenant_id=FAKE_OTHER_TENANT_ID,
    )

    assert other_tenant_product is None


def test_product_repository_get_by_name_is_tenant_scoped(db_session):
    existing_product = db_session.scalar(
        select(Product).where(
            Product.tenant_id == TENANT_ID,
        )
    )

    assert existing_product is not None

    repository = ProductRepository(db_session)

    product = repository.get_by_name(
        name=existing_product.name,
        tenant_id=TENANT_ID,
    )

    assert product is not None
    assert product.id == existing_product.id
    assert product.name == existing_product.name
    assert product.tenant_id == TENANT_ID

    other_tenant_product = repository.get_by_name(
        name=existing_product.name,
        tenant_id=FAKE_OTHER_TENANT_ID,
    )

    assert other_tenant_product is None


def test_product_repository_get_all_returns_sorted_tenant_products(
    db_session,
):
    repository = ProductRepository(db_session)

    products = repository.get_all(
        tenant_id=TENANT_ID,
    )

    assert products
    assert all(
        product.tenant_id == TENANT_ID
        for product in products
    )

    names = [product.name for product in products]

    assert names == sorted(names)
    
    
def test_product_repository_get_by_id_returns_none_for_missing_product(
    db_session,
):
    repository = ProductRepository(db_session)

    missing_product_id = UUID(
        "00000000-0000-0000-0000-000000000099"
    )

    product = repository.get_by_id(
        product_id=missing_product_id,
        tenant_id=TENANT_ID,
    )

    assert product is None


def test_product_repository_get_by_name_returns_none_for_missing_product(
    db_session,
):
    repository = ProductRepository(db_session)

    product = repository.get_by_name(
        name="THIS-PRODUCT-DOES-NOT-EXIST",
        tenant_id=TENANT_ID,
    )

    assert product is None