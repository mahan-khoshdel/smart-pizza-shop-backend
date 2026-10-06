from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.database.models.order import OrderStatus
from app.repositories.order import OrderRepository
from app.schemas.order import OrderCreate
from app.services.order import (
    create_order,
    get_order,
    get_order_status_history,
    update_order_status,
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


def _create_ready_order(db: Session) -> dict:
    """
    Create a unique order and move it to READY.
    """

    order_data = OrderCreate(
        branch_id=BRANCH_ID,
        customer_id=None,
        customer_address_id=None,
        order_number=f"TEST-ROLLBACK-{uuid4().hex[:8]}",
        order_type="DINE_IN",
        note="Automated rollback integration test.",
        items=[
            {
                "product_variant_id": PRODUCT_VARIANT_ID,
                "quantity": 1,
            }
        ],
    )

    created_order = create_order(
        db=db,
        tenant_id=TENANT_ID,
        data=order_data,
    )

    assert created_order["status"] == OrderStatus.REGISTERED

    preparing_order = update_order_status(
        db=db,
        tenant_id=TENANT_ID,
        order_id=created_order["id"],
        new_status=OrderStatus.PREPARING,
    )

    assert preparing_order["status"] == OrderStatus.PREPARING

    ready_order = update_order_status(
        db=db,
        tenant_id=TENANT_ID,
        order_id=created_order["id"],
        new_status=OrderStatus.READY,
    )

    assert ready_order["status"] == OrderStatus.READY
    assert ready_order["inventory_consumed_at"] is None

    return ready_order


def test_order_completion_rolls_back_when_inventory_fails(
    db_session: Session,
    monkeypatch,
):
    """
    Verify that a failed inventory consumption rolls back
    the entire READY -> COMPLETED transaction.
    """

    ready_order = _create_ready_order(
        db=db_session,
    )

    order_id = ready_order["id"]

    def fake_consume_inventory(
        db,
        tenant_id,
        branch_id,
        ingredient_id,
        quantity,
        commit,
    ):
        raise HTTPException(
            status_code=409,
            detail="Insufficient inventory for test.",
        )

    monkeypatch.setattr(
        "app.services.order.consume_inventory",
        fake_consume_inventory,
    )

    with pytest.raises(HTTPException) as exc_info:
        update_order_status(
            db=db_session,
            tenant_id=TENANT_ID,
            order_id=order_id,
            new_status=OrderStatus.COMPLETED,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == (
        "Insufficient inventory for test."
    )

    order = get_order(
        db=db_session,
        tenant_id=TENANT_ID,
        order_id=order_id,
    )

    assert order["status"] == OrderStatus.READY
    assert order["inventory_consumed_at"] is None

    history = get_order_status_history(
        db=db_session,
        order_id=order_id,
        tenant_id=TENANT_ID,
    )

    assert len(history) == 3
    assert [item.to_status for item in history] == [
        OrderStatus.REGISTERED.value,
        OrderStatus.PREPARING.value,
        OrderStatus.READY.value,
    ]


def test_order_completion_rolls_back_on_unexpected_exception(
    db_session: Session,
    monkeypatch,
):
    """
    Verify that an unexpected inventory error also rolls back
    the order status and inventory timestamp.
    """

    ready_order = _create_ready_order(
        db=db_session,
    )

    order_id = ready_order["id"]

    def fake_consume_inventory(
        db,
        tenant_id,
        branch_id,
        ingredient_id,
        quantity,
        commit,
    ):
        raise RuntimeError(
            "Simulated unexpected inventory failure."
        )

    monkeypatch.setattr(
        "app.services.order.consume_inventory",
        fake_consume_inventory,
    )

    with pytest.raises(RuntimeError) as exc_info:
        update_order_status(
            db=db_session,
            tenant_id=TENANT_ID,
            order_id=order_id,
            new_status=OrderStatus.COMPLETED,
        )

    assert str(exc_info.value) == (
        "Simulated unexpected inventory failure."
    )

    order = get_order(
        db=db_session,
        tenant_id=TENANT_ID,
        order_id=order_id,
    )

    assert order["status"] == OrderStatus.READY
    assert order["inventory_consumed_at"] is None

    history = get_order_status_history(
        db=db_session,
        order_id=order_id,
        tenant_id=TENANT_ID,
    )

    assert len(history) == 3
    assert all(
        item.to_status != OrderStatus.COMPLETED.value
        for item in history
    )


def test_order_can_be_completed_after_failed_transaction(
    db_session: Session,
    monkeypatch,
):
    """
    Verify that an order can successfully complete after a
    previous failed completion attempt was rolled back.
    """

    ready_order = _create_ready_order(
        db=db_session,
    )

    order_id = ready_order["id"]

    original_consume_inventory = (
        __import__(
            "app.services.order",
            fromlist=["consume_inventory"],
        ).consume_inventory
    )

    calls = {"count": 0}

    def fail_once_then_continue(
        db,
        tenant_id,
        branch_id,
        ingredient_id,
        quantity,
        commit,
    ):
        calls["count"] += 1

        if calls["count"] == 1:
            raise HTTPException(
                status_code=409,
                detail="Temporary inventory failure.",
            )

        return original_consume_inventory(
            db=db,
            tenant_id=tenant_id,
            branch_id=branch_id,
            ingredient_id=ingredient_id,
            quantity=quantity,
            commit=commit,
        )

    monkeypatch.setattr(
        "app.services.order.consume_inventory",
        fail_once_then_continue,
    )

    with pytest.raises(HTTPException) as exc_info:
        update_order_status(
            db=db_session,
            tenant_id=TENANT_ID,
            order_id=order_id,
            new_status=OrderStatus.COMPLETED,
        )

    assert exc_info.value.status_code == 409

    failed_order = get_order(
        db=db_session,
        tenant_id=TENANT_ID,
        order_id=order_id,
    )

    assert failed_order["status"] == OrderStatus.READY
    assert failed_order["inventory_consumed_at"] is None

    completed_order = update_order_status(
        db=db_session,
        tenant_id=TENANT_ID,
        order_id=order_id,
        new_status=OrderStatus.COMPLETED,
    )

    assert completed_order["status"] == OrderStatus.COMPLETED
    assert completed_order["inventory_consumed_at"] is not None

    history = get_order_status_history(
        db=db_session,
        order_id=order_id,
        tenant_id=TENANT_ID,
    )

    assert len(history) == 4
    assert [item.to_status for item in history] == [
        OrderStatus.REGISTERED.value,
        OrderStatus.PREPARING.value,
        OrderStatus.READY.value,
        OrderStatus.COMPLETED.value,
    ]