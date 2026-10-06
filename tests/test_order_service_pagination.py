import pytest
from uuid import UUID, uuid4

from fastapi import HTTPException

from app.schemas.order import OrderCreate
from app.services.order import (
    create_order,
    get_orders,
    get_orders_page,
)


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
            f"TEST-SERVICE-PAGINATION-"
            f"{uuid4().hex[:8]}"
        ),
        order_type="DINE_IN",
        note="Automated service pagination test.",
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


def test_get_orders_limit(
    db_session,
):
    _create_order(db_session)
    _create_order(db_session)
    _create_order(db_session)

    orders = get_orders(
        db=db_session,
        tenant_id=TENANT_ID,
        limit=2,
    )

    assert len(orders) <= 2

    for order in orders:
        assert order["tenant_id"] == TENANT_ID


def test_get_orders_offset(
    db_session,
):
    _create_order(db_session)
    _create_order(db_session)
    _create_order(db_session)

    all_orders = get_orders(
        db=db_session,
        tenant_id=TENANT_ID,
    )

    paginated_orders = get_orders(
        db=db_session,
        tenant_id=TENANT_ID,
        limit=2,
        offset=1,
    )

    expected_ids = [
        order["id"]
        for order in all_orders[1:3]
    ]

    returned_ids = [
        order["id"]
        for order in paginated_orders
    ]

    assert returned_ids == expected_ids


def test_get_orders_pagination_preserves_ordering(
    db_session,
):
    _create_order(db_session)
    _create_order(db_session)
    _create_order(db_session)

    all_orders = get_orders(
        db=db_session,
        tenant_id=TENANT_ID,
    )

    paginated_orders = get_orders(
        db=db_session,
        tenant_id=TENANT_ID,
        limit=2,
        offset=1,
    )

    assert (
        paginated_orders
        == all_orders[1:3]
    )


def test_get_orders_page_returns_pagination_metadata(
    db_session,
):
    result = get_orders_page(
        db=db_session,
        tenant_id=TENANT_ID,
    )

    assert isinstance(result, dict)

    assert "items" in result
    assert "total" in result
    assert "limit" in result
    assert "offset" in result

    assert isinstance(result["items"], list)
    assert isinstance(result["total"], int)

    assert result["limit"] == 20
    assert result["offset"] == 0


def test_get_orders_page_respects_limit(
    db_session,
):
    _create_order(db_session)
    _create_order(db_session)
    _create_order(db_session)

    result = get_orders_page(
        db=db_session,
        tenant_id=TENANT_ID,
        limit=1,
    )

    assert len(result["items"]) <= 1
    assert result["limit"] == 1


def test_get_orders_page_respects_offset(
    db_session,
):
    _create_order(db_session)
    _create_order(db_session)
    _create_order(db_session)

    result = get_orders_page(
        db=db_session,
        tenant_id=TENANT_ID,
        limit=1,
        offset=1,
    )

    assert result["limit"] == 1
    assert result["offset"] == 1
    assert len(result["items"]) <= 1


def test_get_orders_page_total_ignores_pagination(
    db_session,
):
    _create_order(db_session)
    _create_order(db_session)
    _create_order(db_session)

    first_page = get_orders_page(
        db=db_session,
        tenant_id=TENANT_ID,
        limit=1,
        offset=0,
    )

    second_page = get_orders_page(
        db=db_session,
        tenant_id=TENANT_ID,
        limit=1,
        offset=1,
    )

    assert first_page["total"] == second_page["total"]


@pytest.mark.parametrize(
    ("limit", "expected_detail"),
    [
        (
            0,
            "Limit must be greater than zero.",
        ),
        (
            -1,
            "Limit must be greater than zero.",
        ),
        (
            101,
            "Limit cannot be greater than 100.",
        ),
    ],
)
def test_get_orders_page_rejects_invalid_limit(
    db_session,
    limit,
    expected_detail,
):
    with pytest.raises(HTTPException) as exc_info:
        get_orders_page(
            db=db_session,
            tenant_id=TENANT_ID,
            limit=limit,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == expected_detail


def test_get_orders_page_rejects_negative_offset(
    db_session,
):
    with pytest.raises(HTTPException) as exc_info:
        get_orders_page(
            db=db_session,
            tenant_id=TENANT_ID,
            offset=-1,
        )

    assert exc_info.value.status_code == 400
    assert (
        exc_info.value.detail
        == "Offset cannot be negative."
    )