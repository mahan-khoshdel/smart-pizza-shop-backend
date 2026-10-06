from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select

from app.database.models.branch import Branch
from app.database.models.order import Order, OrderStatus, OrderType
from app.database.models.order_status_history import OrderStatusHistory
from app.database.models.tenant import Tenant
from app.repositories.order_status_history import (
    OrderStatusHistoryRepository,
)


def test_order_status_history_is_returned_in_chronological_order(
    db_session,
):
    """
    Verify that order status history is returned
    from the oldest transition to the newest transition.

    The test creates a real order so that the history records
    satisfy the order_status_history foreign key constraint.

    History records are intentionally inserted in reverse
    chronological order to verify that the repository relies
    on explicit ordering.
    """

    tenant_id = db_session.scalar(
        select(Tenant.id).limit(1)
    )

    assert tenant_id is not None, (
        "At least one tenant is required for this test."
    )

    branch_id = db_session.scalar(
        select(Branch.id)
        .where(
            Branch.tenant_id == tenant_id,
        )
        .limit(1)
    )

    assert branch_id is not None, (
        "At least one branch is required for this test tenant."
    )

    order = Order(
        tenant_id=tenant_id,
        branch_id=branch_id,
        order_number=f"TEST-HISTORY-{uuid4().hex[:12]}",
        order_type=OrderType.DINE_IN,
        status=OrderStatus.REGISTERED,
        subtotal=0,
        discount_total=0,
        tax_total=0,
        total=0,
    )

    db_session.add(order)
    db_session.flush()

    base_time = datetime.now(timezone.utc)

    completed_history = OrderStatusHistory(
        order_id=order.id,
        from_status=OrderStatus.READY.value,
        to_status=OrderStatus.COMPLETED.value,
        changed_at=base_time + timedelta(seconds=3),
    )

    ready_history = OrderStatusHistory(
        order_id=order.id,
        from_status=OrderStatus.PREPARING.value,
        to_status=OrderStatus.READY.value,
        changed_at=base_time + timedelta(seconds=2),
    )

    preparing_history = OrderStatusHistory(
        order_id=order.id,
        from_status=OrderStatus.REGISTERED.value,
        to_status=OrderStatus.PREPARING.value,
        changed_at=base_time + timedelta(seconds=1),
    )

    registered_history = OrderStatusHistory(
        order_id=order.id,
        from_status=None,
        to_status=OrderStatus.REGISTERED.value,
        changed_at=base_time,
    )

    db_session.add_all(
        [
            completed_history,
            ready_history,
            preparing_history,
            registered_history,
        ]
    )

    db_session.commit()

    repository = OrderStatusHistoryRepository(
        db_session
    )

    history = repository.get_by_order_id(
        order_id=order.id,
    )

    assert len(history) == 4

    assert history[0].to_status == OrderStatus.REGISTERED.value
    assert history[1].to_status == OrderStatus.PREPARING.value
    assert history[2].to_status == OrderStatus.READY.value
    assert history[3].to_status == OrderStatus.COMPLETED.value