from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from app.database.models.order import OrderStatus
from app.repositories.order import OrderRepository
from app.schemas.order import OrderCreate
from app.services import order as order_service
from app.services.order import create_order, get_kitchen_queue, update_order_status


TENANT_ID = UUID(
    "25291ef5-0240-4042-aabc-b92c5aa4957a"
)

BRANCH_ID = UUID(
    "6146f071-baf4-40e9-bbff-71f86e0a7770"
)

PRODUCT_VARIANT_ID = UUID(
    "7c065b06-1422-446b-a163-d6a30b4b659b"
)

FIXED_NOW = datetime(
    2026,
    10,
    6,
    10,
    0,
    0,
    tzinfo=timezone.utc,
)


class FixedDateTime:
    """
    Minimal datetime replacement for deterministic tests.
    """

    @classmethod
    def now(cls, tz=None):
        return FIXED_NOW


def _create_preparing_order(
    db_session,
    monkeypatch,
):
    """
    Create a test order and move it to PREPARING.
    """

    monkeypatch.setattr(
        order_service,
        "datetime",
        FixedDateTime,
    )

    def fake_get_kitchen_workload(
        self,
        tenant_id,
        branch_id,
    ):
        return {
            "preparing_count": 0,
            "ready_count": 0,
            "active_count": 0,
        }

    monkeypatch.setattr(
        OrderRepository,
        "get_kitchen_workload",
        fake_get_kitchen_workload,
    )

    order_data = OrderCreate(
        branch_id=BRANCH_ID,
        customer_id=None,
        customer_address_id=None,
        order_number=f"TEST-TIMING-{uuid4().hex[:8]}",
        order_type="DINE_IN",
        note="Kitchen timing automated test.",
        items=[
            {
                "product_variant_id": PRODUCT_VARIANT_ID,
                "quantity": 1,
            }
        ],
    )

    created_order = create_order(
        db=db_session,
        tenant_id=TENANT_ID,
        data=order_data,
    )

    preparing_order = update_order_status(
        db=db_session,
        tenant_id=TENANT_ID,
        order_id=created_order["id"],
        new_status=OrderStatus.PREPARING,
    )

    return preparing_order


def test_kitchen_queue_reports_remaining_preparation_time(
    db_session,
    monkeypatch,
):
    """
    Verify preparation elapsed time and remaining time
    when the order is still within the expected duration.
    """

    preparing_order = _create_preparing_order(
        db_session,
        monkeypatch,
    )

    assert preparing_order["status"] == OrderStatus.PREPARING

    def fake_get_kitchen_preparation_durations(
        self,
        tenant_id,
        branch_id,
    ):
        return [300]

    monkeypatch.setattr(
        OrderRepository,
        "get_kitchen_preparation_durations",
        fake_get_kitchen_preparation_durations,
    )

    order = db_session.get(
        order_service.Order,
        preparing_order["id"],
    )

    order.preparing_at = FIXED_NOW - timedelta(seconds=120)

    db_session.flush()

    queue = get_kitchen_queue(
        db=db_session,
        tenant_id=TENANT_ID,
        branch_id=BRANCH_ID,
    )

    item = next(
        item
        for item in queue["queue"]
        if item["order_id"] == preparing_order["id"]
    )

    assert queue["total_preparing"] >= 1
    assert item["status"] == OrderStatus.PREPARING.value
    assert item["preparation_elapsed_seconds"] == 120.0
    assert item["preparation_elapsed_minutes"] == 2.0

    assert item["expected_preparation_seconds"] == 300.0
    assert item["expected_preparation_minutes"] == 5.0

    assert item["remaining_preparation_seconds"] == 180.0
    assert item["remaining_preparation_minutes"] == 3.0

    assert item["is_overdue"] is False
    assert item["overdue_seconds"] is None
    assert item["overdue_minutes"] is None

    assert item["estimated_ready_at"] == (
        FIXED_NOW + timedelta(seconds=180)
    )


def test_kitchen_queue_detects_overdue_preparation(
    db_session,
    monkeypatch,
):
    """
    Verify that a PREPARING order is marked overdue
    when its preparation time exceeds the historical average.
    """

    preparing_order = _create_preparing_order(
        db_session,
        monkeypatch,
    )

    def fake_get_kitchen_preparation_durations(
        self,
        tenant_id,
        branch_id,
    ):
        return [300]

    monkeypatch.setattr(
        OrderRepository,
        "get_kitchen_preparation_durations",
        fake_get_kitchen_preparation_durations,
    )

    order = db_session.get(
        order_service.Order,
        preparing_order["id"],
    )

    order.preparing_at = FIXED_NOW - timedelta(seconds=480)

    db_session.flush()

    queue = get_kitchen_queue(
        db=db_session,
        tenant_id=TENANT_ID,
        branch_id=BRANCH_ID,
    )

    item = next(
        item
        for item in queue["queue"]
        if item["order_id"] == preparing_order["id"]
    )

    assert item["preparation_elapsed_seconds"] == 480.0
    assert item["preparation_elapsed_minutes"] == 8.0

    assert item["expected_preparation_seconds"] == 300.0
    assert item["expected_preparation_minutes"] == 5.0

    assert item["remaining_preparation_seconds"] == 0
    assert item["remaining_preparation_minutes"] == 0

    assert item["is_overdue"] is True
    assert item["overdue_seconds"] == 180.0
    assert item["overdue_minutes"] == 3.0

    assert item["estimated_ready_at"] == FIXED_NOW