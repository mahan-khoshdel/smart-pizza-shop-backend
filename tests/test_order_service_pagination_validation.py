import pytest
from uuid import UUID
from fastapi import HTTPException

from app.services.order import get_orders


TENANT_ID = UUID(
    "25291ef5-0240-4042-aabc-b92c5aa4957a"
)


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
def test_get_orders_rejects_invalid_limit(
    db_session,
    limit,
    expected_detail,
):
    with pytest.raises(HTTPException) as exc_info:
        get_orders(
            db=db_session,
            tenant_id=TENANT_ID,
            limit=limit,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == expected_detail


def test_get_orders_rejects_negative_offset(
    db_session,
):
    with pytest.raises(HTTPException) as exc_info:
        get_orders(
            db=db_session,
            tenant_id=TENANT_ID,
            offset=-1,
        )

    assert exc_info.value.status_code == 400
    assert (
        exc_info.value.detail
        == "Offset cannot be negative."
    )


def test_get_orders_accepts_maximum_limit(
    db_session,
):
    orders = get_orders(
        db=db_session,
        tenant_id=TENANT_ID,
        limit=100,
    )

    assert len(orders) <= 100


def test_get_orders_accepts_zero_offset(
    db_session,
):
    orders = get_orders(
        db=db_session,
        tenant_id=TENANT_ID,
        offset=0,
    )

    assert isinstance(orders, list)