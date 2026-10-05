from uuid import UUID, uuid4

from app.database.models.order import OrderStatus
from app.repositories.order import OrderRepository
from app.repositories.order_status_history import (
    OrderStatusHistoryRepository,
)
from app.schemas.order import OrderCreate
from app.services.order import (
    create_order,
    get_kitchen_workload,
    get_order_status_history,
    update_order_status,
)


TENANT_ID = UUID("25291ef5-0240-4042-aabc-b92c5aa4957a")

BRANCH_ID = UUID("6146f071-baf4-40e9-bbff-71f86e0a7770")

PRODUCT_VARIANT_ID = UUID(
    "7c065b06-1422-446b-a163-d6a30b4b659b"
)


def _get_history_status(history_item, field_name: str):
    """
    Return a status-history field from either
    an ORM object or a dictionary-like result.
    """
    if hasattr(history_item, field_name):
        return getattr(history_item, field_name)

    return history_item[field_name]


def test_complete_order_workflow(db_session):
    """
    Verify the complete order workflow:

    REGISTERED -> PREPARING -> READY -> COMPLETED

    The test also verifies:
    - status history
    - inventory consumption timestamp
    - tenant/branch/product integration
    """

    # ---------------------------------------------------------
    # 1. Make sure the kitchen can accept another order
    # ---------------------------------------------------------

    workload = get_kitchen_workload(
        db=db_session,
        tenant_id=TENANT_ID,
        branch_id=BRANCH_ID,
    )

    assert workload["capacity_available"] > 0, (
        "The test branch has no available kitchen capacity. "
        f"Preparing: {workload['preparing_count']}, "
        f"Capacity: {workload['kitchen_capacity']}."
    )

    # ---------------------------------------------------------
    # 2. Create a unique test order
    # ---------------------------------------------------------

    order_number = f"TEST-WORKFLOW-{uuid4().hex[:8]}"

    order_data = OrderCreate(
        branch_id=BRANCH_ID,
        customer_id=None,
        customer_address_id=None,
        order_number=order_number,
        order_type="DINE_IN",
        note="Automated integration test order.",
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

    order_id = created_order["id"]

    assert created_order["tenant_id"] == TENANT_ID
    assert created_order["branch_id"] == BRANCH_ID
    assert created_order["order_number"] == order_number
    assert created_order["status"] == OrderStatus.REGISTERED
    assert created_order["items"]

    # ---------------------------------------------------------
    # 3. REGISTERED -> PREPARING
    # ---------------------------------------------------------

    preparing_order = update_order_status(
        db=db_session,
        tenant_id=TENANT_ID,
        order_id=order_id,
        new_status=OrderStatus.PREPARING,
    )

    assert preparing_order["status"] == OrderStatus.PREPARING
    assert preparing_order["inventory_consumed_at"] is None

    # ---------------------------------------------------------
    # 4. PREPARING -> READY
    # ---------------------------------------------------------

    ready_order = update_order_status(
        db=db_session,
        tenant_id=TENANT_ID,
        order_id=order_id,
        new_status=OrderStatus.READY,
    )

    assert ready_order["status"] == OrderStatus.READY
    assert ready_order["inventory_consumed_at"] is None

    # ---------------------------------------------------------
    # 5. READY -> COMPLETED
    # ---------------------------------------------------------

    completed_order = update_order_status(
        db=db_session,
        tenant_id=TENANT_ID,
        order_id=order_id,
        new_status=OrderStatus.COMPLETED,
    )

    assert completed_order["status"] == OrderStatus.COMPLETED
    assert completed_order["inventory_consumed_at"] is not None

    # ---------------------------------------------------------
    # 6. Verify status history
    # ---------------------------------------------------------

    history = get_order_status_history(
        db=db_session,
        order_id=order_id,
        tenant_id=TENANT_ID,
    )

    assert len(history) == 4

    history_transitions = {
        (
            _get_history_status(item, "from_status"),
            _get_history_status(item, "to_status"),
        )
        for item in history
    }

    expected_transitions = {
        (
            None,
            OrderStatus.REGISTERED.value,
        ),
        (
            OrderStatus.REGISTERED.value,
            OrderStatus.PREPARING.value,
        ),
        (
            OrderStatus.PREPARING.value,
            OrderStatus.READY.value,
        ),
        (
            OrderStatus.READY.value,
            OrderStatus.COMPLETED.value,
        ),
    }

    assert history_transitions == expected_transitions

    # ---------------------------------------------------------
    # 7. Verify repository can see the final state
    # ---------------------------------------------------------

    repository = OrderRepository(db_session)

    stored_order = repository.get_by_id(
        order_id=order_id,
        tenant_id=TENANT_ID,
    )

    assert stored_order is not None
    assert stored_order.status == OrderStatus.COMPLETED
    assert stored_order.inventory_consumed_at is not None
    assert stored_order.tenant_id == TENANT_ID

    # ---------------------------------------------------------
    # 8. Verify history belongs to this order
    # ---------------------------------------------------------

    history_repository = OrderStatusHistoryRepository(
        db_session
    )

    stored_history = history_repository.get_by_order_id(
        order_id=order_id,
    )

    assert len(stored_history) == 4