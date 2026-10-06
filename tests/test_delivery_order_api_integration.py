"""
Integration tests for delivery orders and address snapshots.
"""

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_data
from app.core.dependencies import get_db as core_get_db
from app.database.connection import get_db as connection_get_db
from app.main import app


TENANT_ID = UUID(
    "25291ef5-0240-4042-aabc-b92c5aa4957a"
)

USER_ID = UUID(
    "00000000-0000-0000-0000-000000000010"
)

BRANCH_ID = UUID(
    "6146f071-baf4-40e9-bbff-71f86e0a7770"
)

PRODUCT_VARIANT_ID = UUID(
    "7c065b06-1422-446b-a163-d6a30b4b659b"
)


@pytest.fixture
def authenticated_client(
    db_session: Session,
):
    """
    Provide an authenticated API client backed by
    the real PostgreSQL test session.
    """
    original_overrides = (
        app.dependency_overrides.copy()
    )

    def override_current_user():
        return {
            "user_id": USER_ID,
            "tenant_id": TENANT_ID,
        }

    def override_get_db():
        yield db_session

    app.dependency_overrides[
        get_current_user_data
    ] = override_current_user

    app.dependency_overrides[
        connection_get_db
    ] = override_get_db

    app.dependency_overrides[
        core_get_db
    ] = override_get_db

    client = TestClient(app)

    try:
        yield client

    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(
            original_overrides
        )


def test_delivery_order_keeps_address_snapshot(
    authenticated_client,
):
    """
    Verify the complete delivery address flow:

    CREATE CUSTOMER
        ->
    CREATE CUSTOMER ADDRESS
        ->
    CREATE DELIVERY ORDER
        ->
    UPDATE CUSTOMER ADDRESS
        ->
    VERIFY ORDER SNAPSHOT IS UNCHANGED
    """
    client = authenticated_client

    # ---------------------------------------------------------
    # 1. Create customer
    # ---------------------------------------------------------

    unique_suffix = uuid4().hex[:8]

    customer_payload = {
        "first_name": "Integration",
        "last_name": f"Customer-{unique_suffix}",
        "phone": "09120000000",
        "email": (
            f"integration-{unique_suffix}"
            "@example.com"
        ),
        "notes": "Delivery integration test customer.",
    }

    customer_response = client.post(
        "/api/v1/customers",
        json=customer_payload,
    )

    assert customer_response.status_code == 200

    customer = customer_response.json()

    customer_id = customer["id"]

    assert customer["first_name"] == "Integration"
    assert (
        customer["last_name"]
        == customer_payload["last_name"]
    )

    # ---------------------------------------------------------
    # 2. Create customer address
    # ---------------------------------------------------------

    address_payload = {
        "label": "Home",
        "recipient_name": "Integration Customer",
        "phone": "09120000000",
        "address_line": "Original Delivery Address 123",
        "city": "Baku",
        "postal_code": "AZ1000",
        "is_default": True,
    }

    address_response = client.post(
        f"/api/v1/customers/{customer_id}/addresses",
        json=address_payload,
    )

    assert address_response.status_code == 200

    address = address_response.json()

    address_id = address["id"]

    assert address["customer_id"] == customer_id
    assert (
        address["recipient_name"]
        == address_payload["recipient_name"]
    )
    assert (
        address["address_line"]
        == address_payload["address_line"]
    )
    assert (
        address["city"]
        == address_payload["city"]
    )
    assert (
        address["postal_code"]
        == address_payload["postal_code"]
    )

    # ---------------------------------------------------------
    # 3. Create delivery order
    # ---------------------------------------------------------

    order_number = (
        f"TEST-DELIVERY-{uuid4().hex[:8]}"
    )

    order_payload = {
        "branch_id": str(BRANCH_ID),
        "customer_id": customer_id,
        "customer_address_id": address_id,
        "order_number": order_number,
        "order_type": "DELIVERY",
        "note": "Delivery snapshot integration test.",
        "items": [
            {
                "product_variant_id": str(
                    PRODUCT_VARIANT_ID
                ),
                "quantity": 1,
            }
        ],
    }

    order_response = client.post(
        "/api/v1/orders",
        json=order_payload,
    )

    assert order_response.status_code == 201

    created_order = order_response.json()

    order_id = created_order["id"]

    assert (
        created_order["customer_id"]
        == customer_id
    )
    assert (
        created_order["order_type"]
        == "DELIVERY"
    )
    assert (
        created_order["status"]
        == "REGISTERED"
    )

    # Verify delivery address snapshot
    assert (
        created_order["delivery_recipient_name"]
        == address_payload["recipient_name"]
    )
    assert (
        created_order["delivery_phone"]
        == address_payload["phone"]
    )
    assert (
        created_order["delivery_address_line"]
        == address_payload["address_line"]
    )
    assert (
        created_order["delivery_city"]
        == address_payload["city"]
    )
    assert (
        created_order["delivery_postal_code"]
        == address_payload["postal_code"]
    )

    # ---------------------------------------------------------
    # 4. Update the customer's address
    # ---------------------------------------------------------

    updated_address_payload = {
        "recipient_name": "Updated Recipient",
        "phone": "09990000000",
        "address_line": "New Delivery Address 456",
        "city": "Sumqayit",
        "postal_code": "AZ5000",
    }

    update_response = client.put(
        (
            f"/api/v1/customers/"
            f"{customer_id}/addresses/{address_id}"
        ),
        json=updated_address_payload,
    )

    assert update_response.status_code == 200

    updated_address = update_response.json()

    assert (
        updated_address["recipient_name"]
        == updated_address_payload["recipient_name"]
    )
    assert (
        updated_address["phone"]
        == updated_address_payload["phone"]
    )
    assert (
        updated_address["address_line"]
        == updated_address_payload["address_line"]
    )
    assert (
        updated_address["city"]
        == updated_address_payload["city"]
    )
    assert (
        updated_address["postal_code"]
        == updated_address_payload["postal_code"]
    )

    # ---------------------------------------------------------
    # 5. Verify the customer's address really changed
    # ---------------------------------------------------------

    address_get_response = client.get(
        (
            f"/api/v1/customers/"
            f"{customer_id}/addresses/{address_id}"
        )
    )

    assert address_get_response.status_code == 200

    current_address = address_get_response.json()

    assert (
        current_address["address_line"]
        == updated_address_payload["address_line"]
    )
    assert (
        current_address["city"]
        == updated_address_payload["city"]
    )
    assert (
        current_address["postal_code"]
        == updated_address_payload["postal_code"]
    )

    # ---------------------------------------------------------
    # 6. Verify the old order still contains the old snapshot
    # ---------------------------------------------------------

    order_get_response = client.get(
        f"/api/v1/orders/{order_id}"
    )

    assert order_get_response.status_code == 200

    fetched_order = order_get_response.json()

    assert fetched_order["id"] == order_id
    assert (
        fetched_order["customer_id"]
        == customer_id
    )
    assert (
        fetched_order["order_number"]
        == order_number
    )
    assert (
        fetched_order["order_type"]
        == "DELIVERY"
    )

    # Snapshot must remain unchanged.
    assert (
        fetched_order["delivery_recipient_name"]
        == address_payload["recipient_name"]
    )
    assert (
        fetched_order["delivery_phone"]
        == address_payload["phone"]
    )
    assert (
        fetched_order["delivery_address_line"]
        == address_payload["address_line"]
    )
    assert (
        fetched_order["delivery_city"]
        == address_payload["city"]
    )
    assert (
        fetched_order["delivery_postal_code"]
        == address_payload["postal_code"]
    )

    # The order snapshot must not contain
    # the newly updated customer address.
    assert (
        fetched_order["delivery_address_line"]
        != updated_address_payload["address_line"]
    )
    assert (
        fetched_order["delivery_city"]
        != updated_address_payload["city"]
    )
    assert (
        fetched_order["delivery_postal_code"]
        != updated_address_payload["postal_code"]
    )