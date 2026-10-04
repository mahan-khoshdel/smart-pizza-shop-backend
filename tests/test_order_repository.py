from uuid import UUID

from app.repositories.order import OrderRepository


TENANT_ID = UUID("25291ef5-0240-4042-aabc-b92c5aa4957a")

FAKE_OTHER_TENANT_ID = UUID(
    "00000000-0000-0000-0000-000000000001"
)


def test_order_repository_returns_only_current_tenant_orders(db_session):
    repository = OrderRepository(db_session)

    orders = repository.get_all(
        tenant_id=TENANT_ID,
    )

    assert orders

    assert all(
        order.tenant_id == TENANT_ID
        for order in orders
    )


def test_order_repository_does_not_return_other_tenant_orders(
    db_session,
):
    repository = OrderRepository(db_session)

    orders = repository.get_all(
        tenant_id=FAKE_OTHER_TENANT_ID,
    )

    assert orders == []