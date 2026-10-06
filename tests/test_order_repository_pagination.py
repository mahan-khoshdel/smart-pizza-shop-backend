from uuid import UUID, uuid4

from app.repositories.order import OrderRepository
from app.schemas.order import OrderCreate
from app.services.order import create_order


TENANT_ID = UUID(
    "25291ef5-0240-4042-aabc-b92c5aa4957a"
)

BRANCH_ID = UUID(
    "6146f071-baf4-40e9-bbff-71f86e0a7770"
)

PRODUCT_VARIANT_ID = UUID(
    "7c065b06-1422-446b-a163-d6a30b4b659b"
)


def _create_order(db_session):
    order_data = OrderCreate(
        branch_id=BRANCH_ID,
        customer_id=None,
        customer_address_id=None,
        order_number=(
            f"TEST-PAGINATION-"
            f"{uuid4().hex[:8]}"
        ),
        order_type="DINE_IN",
        note="Automated pagination test.",
        items=[
            {
                "product_variant_id": PRODUCT_VARIANT_ID,
                "quantity": 1,
            }
        ],
    )

    return create_order(
        db=db_session,
        tenant_id=TENANT_ID,
        data=order_data,
    )


def test_order_repository_limit(
    db_session,
):
    _create_order(db_session)
    _create_order(db_session)
    _create_order(db_session)

    repository = OrderRepository(db_session)

    orders = repository.get_all(
        tenant_id=TENANT_ID,
        limit=2,
    )

    assert len(orders) <= 2


def test_order_repository_offset(
    db_session,
):
    first_order = _create_order(db_session)
    second_order = _create_order(db_session)
    third_order = _create_order(db_session)

    repository = OrderRepository(db_session)

    orders = repository.get_all(
        tenant_id=TENANT_ID,
        limit=2,
        offset=1,
    )

    returned_ids = [
        order.id
        for order in orders
    ]

    all_orders = repository.get_all(
        tenant_id=TENANT_ID,
    )

    all_ids = [
        order.id
        for order in all_orders
    ]

    expected_ids = all_ids[1:3]

    assert returned_ids == expected_ids

    assert first_order["id"] in all_ids
    assert second_order["id"] in all_ids
    assert third_order["id"] in all_ids


def test_order_repository_pagination_keeps_newest_first(
    db_session,
):
    _create_order(db_session)
    _create_order(db_session)
    _create_order(db_session)

    repository = OrderRepository(db_session)

    all_orders = repository.get_all(
        tenant_id=TENANT_ID,
    )

    paginated_orders = repository.get_all(
        tenant_id=TENANT_ID,
        limit=2,
        offset=1,
    )

    expected_ids = [
        order.id
        for order in all_orders[1:3]
    ]

    returned_ids = [
        order.id
        for order in paginated_orders
    ]

    assert returned_ids == expected_ids