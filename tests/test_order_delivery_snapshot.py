from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.customer_address import CustomerAddress
from app.database.models.order import Order, OrderStatus
from app.database.models.product_variant import ProductVariant
from app.schemas.order import OrderCreate
from app.services.order import create_order


TENANT_ID = UUID(
    "25291ef5-0240-4042-aabc-b92c5aa4957a"
)

BRANCH_ID = UUID(
    "6146f071-baf4-40e9-bbff-71f86e0a7770"
)

PRODUCT_VARIANT_ID = UUID(
    "7c065b06-1422-446b-a163-d6a30b4b659b"
)


def _get_existing_customer_address(
    db_session: Session,
) -> CustomerAddress:
    address = db_session.scalar(
        select(CustomerAddress)
        .where(
            CustomerAddress.tenant_id == TENANT_ID,
        )
        .limit(1)
    )

    assert address is not None, (
        "The test tenant must have at least one "
        "customer address."
    )

    return address


def _create_delivery_order(
    db_session: Session,
    address: CustomerAddress,
) -> dict:
    order_data = OrderCreate(
        branch_id=BRANCH_ID,
        customer_id=address.customer_id,
        customer_address_id=address.id,
        order_number=f"TEST-DELIVERY-SNAPSHOT-{uuid4().hex[:8]}",
        order_type="DELIVERY",
        note="Automated delivery snapshot test.",
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


def test_delivery_order_copies_customer_address_snapshot(
    db_session: Session,
):
    """
    Verify that delivery address data is copied into the order.
    """

    address = _get_existing_customer_address(
        db_session,
    )

    created_order = _create_delivery_order(
        db_session,
        address,
    )

    assert created_order["order_type"] == "DELIVERY"
    assert created_order["status"] == OrderStatus.REGISTERED
    assert created_order["customer_id"] == address.customer_id

    assert (
        created_order["delivery_recipient_name"]
        == address.recipient_name
    )
    assert (
        created_order["delivery_phone"]
        == address.phone
    )
    assert (
        created_order["delivery_address_line"]
        == address.address_line
    )
    assert (
        created_order["delivery_city"]
        == address.city
    )
    assert (
        created_order["delivery_postal_code"]
        == address.postal_code
    )


def test_delivery_order_snapshot_does_not_change_when_address_changes(
    db_session: Session,
):
    """
    Verify that changing the customer address later does not
    modify the historical address stored on the order.
    """

    address = _get_existing_customer_address(
        db_session,
    )

    created_order = _create_delivery_order(
        db_session,
        address,
    )

    original_recipient_name = (
        address.recipient_name
    )
    original_phone = address.phone
    original_address_line = address.address_line
    original_city = address.city
    original_postal_code = address.postal_code

    address.recipient_name = (
        f"{original_recipient_name} Updated"
    )
    address.phone = "09999999999"
    address.address_line = (
        f"{original_address_line} Updated"
    )
    address.city = f"{original_city} Updated"
    address.postal_code = "9999999999"

    db_session.flush()
    db_session.refresh(address)

    order = db_session.scalar(
        select(Order).where(
            Order.id == created_order["id"],
            Order.tenant_id == TENANT_ID,
        )
    )

    assert order is not None

    assert (
        order.delivery_recipient_name
        == original_recipient_name
    )
    assert order.delivery_phone == original_phone
    assert (
        order.delivery_address_line
        == original_address_line
    )
    assert order.delivery_city == original_city
    assert (
        order.delivery_postal_code
        == original_postal_code
    )