from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.customer import Customer
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


def _get_existing_customer_id(
    db_session: Session,
) -> UUID:
    customer_id = db_session.scalar(
        select(Customer.id).where(
            Customer.tenant_id == TENANT_ID
        )
    )

    assert customer_id is not None

    return customer_id


def _create_order(
    db_session: Session,
    customer_id: UUID | None,
) -> dict:
    order_data = OrderCreate(
        branch_id=BRANCH_ID,
        customer_id=customer_id,
        customer_address_id=None,
        order_number=(
            f"TEST-FILTERED-PAGINATION-"
            f"{uuid4().hex[:8]}"
        ),
        order_type="DINE_IN",
        note="Automated filtered pagination test.",
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


def test_order_repository_customer_filter_is_applied_before_pagination(
    db_session: Session,
):
    customer_id = _get_existing_customer_id(
        db_session
    )

    first_customer_order = _create_order(
        db_session,
        customer_id,
    )

    _create_order(
        db_session,
        None,
    )

    second_customer_order = _create_order(
        db_session,
        customer_id,
    )

    third_customer_order = _create_order(
        db_session,
        customer_id,
    )

    repository = OrderRepository(db_session)

    all_customer_orders = repository.get_all(
        tenant_id=TENANT_ID,
        customer_id=customer_id,
    )

    paginated_customer_orders = repository.get_all(
        tenant_id=TENANT_ID,
        customer_id=customer_id,
        limit=2,
        offset=1,
    )

    all_customer_ids = [
        order.id
        for order in all_customer_orders
    ]

    expected_ids = all_customer_ids[1:3]

    returned_ids = [
        order.id
        for order in paginated_customer_orders
    ]

    assert (
        first_customer_order["id"]
        in all_customer_ids
    )

    assert (
        second_customer_order["id"]
        in all_customer_ids
    )

    assert (
        third_customer_order["id"]
        in all_customer_ids
    )

    assert returned_ids == expected_ids

    for order in paginated_customer_orders:
        assert order.customer_id == customer_id


def test_order_repository_status_filter_is_applied_before_pagination(
    db_session: Session,
):
    first_order = _create_order(
        db_session,
        None,
    )

    second_order = _create_order(
        db_session,
        None,
    )

    third_order = _create_order(
        db_session,
        None,
    )

    repository = OrderRepository(db_session)

    all_registered_orders = repository.get_all(
        tenant_id=TENANT_ID,
        status="REGISTERED",
    )

    paginated_registered_orders = repository.get_all(
        tenant_id=TENANT_ID,
        status="REGISTERED",
        limit=2,
        offset=1,
    )

    all_registered_ids = [
        order.id
        for order in all_registered_orders
    ]

    expected_ids = all_registered_ids[1:3]

    returned_ids = [
        order.id
        for order in paginated_registered_orders
    ]

    assert first_order["id"] in all_registered_ids
    assert second_order["id"] in all_registered_ids
    assert third_order["id"] in all_registered_ids

    assert returned_ids == expected_ids

    for order in paginated_registered_orders:
        assert order.status == "REGISTERED"