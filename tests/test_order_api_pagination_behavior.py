"""
Behavior tests for the order pagination API endpoint.
"""

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.auth import get_current_user_data
from app.database.connection import get_db
from app.main import app


client = TestClient(app)

TENANT_ID = UUID(
    "25291ef5-0240-4042-aabc-b92c5aa4957a"
)

CUSTOMER_ID = uuid4()
BRANCH_ID = UUID(
    "6146f071-baf4-40e9-bbff-71f86e0a7770"
)


@pytest.fixture
def api_dependencies():
    """
    Override authentication and database dependencies
    for isolated API behavior tests.
    """

    app.dependency_overrides[
        get_current_user_data
    ] = lambda: {
        "tenant_id": TENANT_ID,
    }

    def override_get_db():
        yield object()

    app.dependency_overrides[
        get_db
    ] = override_get_db

    yield

    app.dependency_overrides.pop(
        get_current_user_data,
        None,
    )

    app.dependency_overrides.pop(
        get_db,
        None,
    )


def _fake_page(
    *,
    limit: int,
    offset: int,
) -> dict:
    """
    Return a minimal valid paginated order response.
    """

    return {
        "items": [],
        "total": 42,
        "limit": limit,
        "offset": offset,
    }


def test_orders_api_passes_pagination_and_filters_to_service(
    api_dependencies,
    monkeypatch,
):
    captured = {}

    def fake_get_orders_page(
        db,
        tenant_id,
        status=None,
        customer_id=None,
        branch_id=None,
        limit=20,
        offset=0,
    ):
        captured["db"] = db
        captured["tenant_id"] = tenant_id
        captured["status"] = status
        captured["customer_id"] = customer_id
        captured["branch_id"] = branch_id
        captured["limit"] = limit
        captured["offset"] = offset

        return _fake_page(
            limit=limit,
            offset=offset,
        )

    monkeypatch.setattr(
        "app.api.v1.orders.get_orders_page",
        fake_get_orders_page,
    )

    response = client.get(
        "/api/v1/orders",
        params={
            "status": "PREPARING",
            "customer_id": str(CUSTOMER_ID),
            "branch_id": str(BRANCH_ID),
            "limit": 7,
            "offset": 14,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["items"] == []
    assert data["total"] == 42
    assert data["limit"] == 7
    assert data["offset"] == 14

    assert captured["tenant_id"] == TENANT_ID
    assert captured["status"].value == "PREPARING"
    assert captured["customer_id"] == CUSTOMER_ID
    assert captured["branch_id"] == BRANCH_ID
    assert captured["limit"] == 7
    assert captured["offset"] == 14


def test_orders_api_uses_default_pagination_values(
    api_dependencies,
    monkeypatch,
):
    captured = {}

    def fake_get_orders_page(
        db,
        tenant_id,
        status=None,
        customer_id=None,
        branch_id=None,
        limit=20,
        offset=0,
    ):
        captured["tenant_id"] = tenant_id
        captured["status"] = status
        captured["customer_id"] = customer_id
        captured["branch_id"] = branch_id
        captured["limit"] = limit
        captured["offset"] = offset

        return _fake_page(
            limit=limit,
            offset=offset,
        )

    monkeypatch.setattr(
        "app.api.v1.orders.get_orders_page",
        fake_get_orders_page,
    )

    response = client.get(
        "/api/v1/orders"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["items"] == []
    assert data["total"] == 42
    assert data["limit"] == 20
    assert data["offset"] == 0

    assert captured["tenant_id"] == TENANT_ID
    assert captured["status"] is None
    assert captured["customer_id"] is None
    assert captured["branch_id"] is None
    assert captured["limit"] == 20
    assert captured["offset"] == 0