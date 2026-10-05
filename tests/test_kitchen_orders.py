from uuid import UUID

from app.database.models.order import OrderStatus
from app.repositories.order import OrderRepository


TENANT_ID = UUID(
    "25291ef5-0240-4042-aabc-b92c5aa4957a"
)

BRANCH_ID = UUID(
    "6146f071-baf4-40e9-bbff-71f86e0a7770"
)

FAKE_OTHER_TENANT_ID = UUID(
    "00000000-0000-0000-0000-000000000001"
)

FAKE_OTHER_BRANCH_ID = UUID(
    "00000000-0000-0000-0000-000000000002"
)


def test_kitchen_order_repository_returns_only_kitchen_statuses(
    db_session,
):
    """
    Verify that the kitchen order query returns only
    PREPARING and READY orders for the requested branch.
    """

    repository = OrderRepository(db_session)

    orders = repository.get_kitchen_orders(
        tenant_id=TENANT_ID,
        branch_id=BRANCH_ID,
    )

    assert orders

    allowed_statuses = {
        OrderStatus.PREPARING,
        OrderStatus.READY,
    }

    assert all(
        order.tenant_id == TENANT_ID
        for order in orders
    )

    assert all(
        order.branch_id == BRANCH_ID
        for order in orders
    )

    assert all(
        order.status in allowed_statuses
        for order in orders
    )


def test_kitchen_order_repository_enforces_tenant_and_branch_isolation(
    db_session,
):
    """
    Verify that kitchen orders cannot be returned
    for another tenant or another branch.
    """

    repository = OrderRepository(db_session)

    other_tenant_orders = repository.get_kitchen_orders(
        tenant_id=FAKE_OTHER_TENANT_ID,
        branch_id=BRANCH_ID,
    )

    other_branch_orders = repository.get_kitchen_orders(
        tenant_id=TENANT_ID,
        branch_id=FAKE_OTHER_BRANCH_ID,
    )

    assert other_tenant_orders == []
    assert other_branch_orders == []