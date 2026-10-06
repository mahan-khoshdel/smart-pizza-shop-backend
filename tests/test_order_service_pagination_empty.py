"""
Tests for paginated order queries when no orders exist.
"""

from uuid import uuid4

from app.services.order import get_orders_page


def test_get_orders_page_for_tenant_without_orders(
    db_session,
):
    """
    Verify that pagination works correctly when the tenant
    has no orders.
    """

    tenant_id = uuid4()

    result = get_orders_page(
        db=db_session,
        tenant_id=tenant_id,
        limit=20,
        offset=0,
    )

    assert isinstance(result, dict)

    assert result["items"] == []
    assert result["total"] == 0
    assert result["limit"] == 20
    assert result["offset"] == 0


def test_get_orders_page_for_empty_tenant_with_offset(
    db_session,
):
    """
    Verify that an empty tenant remains valid when an offset
    is provided.
    """

    tenant_id = uuid4()

    result = get_orders_page(
        db=db_session,
        tenant_id=tenant_id,
        limit=5,
        offset=50,
    )

    assert result["items"] == []
    assert result["total"] == 0
    assert result["limit"] == 5
    assert result["offset"] == 50