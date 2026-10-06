"""
Tests for OrderRepository.count_all().
"""

from uuid import UUID

from app.repositories.order import OrderRepository


TENANT_ID = UUID(
    "25291ef5-0240-4042-aabc-b92c5aa4957a"
)


def test_count_all_matches_unpaginated_orders(
    db_session,
):
    """
    Verify that count_all() matches the number of
    unpaginated orders returned by get_all().
    """

    repository = OrderRepository(db_session)

    orders = repository.get_all(
        tenant_id=TENANT_ID,
    )

    count = repository.count_all(
        tenant_id=TENANT_ID,
    )

    assert count == len(orders)


def test_count_all_with_status_matches_filtered_orders(
    db_session,
):
    """
    Verify that status filtering is applied consistently
    by count_all() and get_all().
    """

    repository = OrderRepository(db_session)

    statuses = {
        order.status
        for order in repository.get_all(
            tenant_id=TENANT_ID,
        )
    }

    for order_status in statuses:
        orders = repository.get_all(
            tenant_id=TENANT_ID,
            status=order_status.value,
        )

        count = repository.count_all(
            tenant_id=TENANT_ID,
            status=order_status.value,
        )

        assert count == len(orders)


def test_count_all_returns_zero_for_unknown_tenant(
    db_session,
):
    """
    Verify that count_all() does not return orders
    belonging to another tenant.
    """

    repository = OrderRepository(db_session)

    unknown_tenant_id = UUID(
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    )

    count = repository.count_all(
        tenant_id=unknown_tenant_id,
    )

    assert count == 0