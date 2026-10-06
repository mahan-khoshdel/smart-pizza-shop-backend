from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.database.models.order import OrderStatus
from app.repositories.order import OrderRepository
from app.schemas.order import OrderCreate
from app.services.order import create_order


TENANT_ID = UUID(
    "25291ef5-0240-4042-aabc-b92c5aa4957a"
)

FAKE_OTHER_TENANT_ID = UUID(
    "00000000-0000-0000-0000-000000000001"
)

BRANCH_ID = UUID(
    "6146f071-baf4-40e9-bbff-71f86e0a7770"
)

PRODUCT_VARIANT_ID = UUID(
    "7c065b06-1422-446b-a163-d6a30b4b659b"
)

NON_EXISTENT_ORDER_ID = UUID(
    "00000000-0000-0000-0000-000000000099"
)


def _create_test_order(
    db: Session,
    prefix: str,
) -> dict:
    order_data = OrderCreate(
        branch_id=BRANCH_ID,
        customer_id=None,
        customer_address_id=None,
        order_number=f"{prefix}-{uuid4().hex[:8]}",
        order_type="DINE_IN",
        note="Automated repository test order.",
        items=[
            {
                "product_variant_id": PRODUCT_VARIANT_ID,
                "quantity": 1,
            }
        ],
    )

    return create_order(
        db=db,
        tenant_id=TENANT_ID,
        data=order_data,
    )


def test_get_by_id_returns_current_tenant_order(
    db_session,
):
    created_order = _create_test_order(
        db=db_session,
        prefix="TEST-REPO-ID",
    )

    repository = OrderRepository(db_session)

    order = repository.get_by_id(
        order_id=created_order["id"],
        tenant_id=TENANT_ID,
    )

    assert order is not None
    assert order.id == created_order["id"]
    assert order.tenant_id == TENANT_ID
    assert order.branch_id == BRANCH_ID


def test_get_by_id_rejects_other_tenant(
    db_session,
):
    created_order = _create_test_order(
        db=db_session,
        prefix="TEST-REPO-SCOPE",
    )

    repository = OrderRepository(db_session)

    order = repository.get_by_id(
        order_id=created_order["id"],
        tenant_id=FAKE_OTHER_TENANT_ID,
    )

    assert order is None


def test_get_by_id_returns_none_for_missing_order(
    db_session,
):
    repository = OrderRepository(db_session)

    order = repository.get_by_id(
        order_id=NON_EXISTENT_ORDER_ID,
        tenant_id=TENANT_ID,
    )

    assert order is None


def test_get_all_returns_only_current_tenant_orders(
    db_session,
):
    first_order = _create_test_order(
        db=db_session,
        prefix="TEST-REPO-ALL-A",
    )

    second_order = _create_test_order(
        db=db_session,
        prefix="TEST-REPO-ALL-B",
    )

    repository = OrderRepository(db_session)

    orders = repository.get_all(
        tenant_id=TENANT_ID,
    )

    order_ids = {
        order.id
        for order in orders
    }

    assert first_order["id"] in order_ids
    assert second_order["id"] in order_ids

    assert all(
        order.tenant_id == TENANT_ID
        for order in orders
    )


def test_get_all_can_filter_by_status(
    db_session,
):
    created_order = _create_test_order(
        db=db_session,
        prefix="TEST-REPO-STATUS",
    )

    repository = OrderRepository(db_session)

    registered_orders = repository.get_all(
        tenant_id=TENANT_ID,
        status=OrderStatus.REGISTERED.value,
    )

    order_ids = {
        order.id
        for order in registered_orders
    }

    assert created_order["id"] in order_ids

    assert all(
        order.status == OrderStatus.REGISTERED
        for order in registered_orders
    )


def test_get_all_returns_empty_for_unknown_tenant(
    db_session,
):
    repository = OrderRepository(db_session)

    orders = repository.get_all(
        tenant_id=FAKE_OTHER_TENANT_ID,
    )

    assert orders == []


def test_get_items_returns_order_items(
    db_session,
):
    created_order = _create_test_order(
        db=db_session,
        prefix="TEST-REPO-ITEMS",
    )

    repository = OrderRepository(db_session)

    items = repository.get_items(
        order_id=created_order["id"],
    )

    assert items
    assert len(items) == 1

    item = items[0]

    assert item.order_id == created_order["id"]
    assert item.product_variant_id == (
        PRODUCT_VARIANT_ID
    )
    assert item.quantity == 1