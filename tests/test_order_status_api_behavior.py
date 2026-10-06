"""
Behavior tests for the order status update API endpoint.
"""

from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.auth import get_current_user_data
from app.database.connection import get_db
from app.main import app


client = TestClient(app)

TENANT_ID = UUID(
    "25291ef5-0240-4042-aabc-b92c5aa4957a"
)


def _get_status_update_operation(
    openapi: dict,
) -> tuple[str, str, dict]:
    """
    Discover the order status update operation
    from the OpenAPI document.

    Returns:
        tuple[str, str, dict]:
            HTTP method, path, and operation definition.
    """

    for path, operations in openapi["paths"].items():
        if "{order_id}" not in path:
            continue

        for method, operation in operations.items():
            if method.lower() not in {
                "put",
                "patch",
                "post",
            }:
                continue

            request_body = operation.get(
                "requestBody"
            )

            if request_body is None:
                continue

            content = request_body.get(
                "content",
                {},
            )

            for media_type in content.values():
                schema = media_type.get(
                    "schema",
                    {},
                )

                reference = schema.get(
                    "$ref",
                    "",
                )

                if reference.endswith(
                    "/OrderStatusUpdate"
                ):
                    return (
                        method.upper(),
                        path,
                        operation,
                    )

    raise AssertionError(
        "Order status update operation was not found."
    )


def _get_status_field_name(
    openapi: dict,
) -> str:
    """
    Return the status field name from OrderStatusUpdate.
    """

    schemas = openapi["components"]["schemas"]

    schema = schemas["OrderStatusUpdate"]

    properties = schema.get(
        "properties",
        {},
    )

    if "status" in properties:
        return "status"

    if "new_status" in properties:
        return "new_status"

    raise AssertionError(
        "OrderStatusUpdate does not define a status field."
    )


def _get_valid_status_value(
    openapi: dict,
) -> str:
    """
    Return one valid order status value
    from the OpenAPI schema.
    """

    schemas = openapi["components"]["schemas"]

    schema = schemas["OrderStatusUpdate"]

    properties = schema["properties"]

    status_field = (
        "status"
        if "status" in properties
        else "new_status"
    )

    status_schema = properties[
        status_field
    ]

    enum_values = status_schema.get(
        "enum",
        [],
    )

    if enum_values:
        return enum_values[0]

    return "PREPARING"


@pytest.fixture
def authenticated_api():
    """
    Override authentication and database dependencies
    for API behavior tests.
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


def test_order_status_update_api_rejects_unauthenticated_request():
    """
    The order status update endpoint must require authentication.
    """

    openapi_response = client.get(
        "/openapi.json"
    )

    assert openapi_response.status_code == 200

    openapi = openapi_response.json()

    method, path, _ = (
        _get_status_update_operation(
            openapi
        )
    )

    status_field = _get_status_field_name(
        openapi
    )

    valid_status = _get_valid_status_value(
        openapi
    )

    order_id = uuid4()

    response = client.request(
        method,
        path.replace(
            "{order_id}",
            str(order_id),
        ),
        json={
            status_field: valid_status,
        },
    )

    assert response.status_code in {
        401,
        403,
    }


def test_order_status_update_api_rejects_invalid_order_id(
    authenticated_api,
):
    """
    The endpoint must reject an invalid UUID order_id.
    """

    openapi_response = client.get(
        "/openapi.json"
    )

    assert openapi_response.status_code == 200

    openapi = openapi_response.json()

    method, path, _ = (
        _get_status_update_operation(
            openapi
        )
    )

    status_field = _get_status_field_name(
        openapi
    )

    valid_status = _get_valid_status_value(
        openapi
    )

    response = client.request(
        method,
        path.replace(
            "{order_id}",
            "not-a-valid-uuid",
        ),
        json={
            status_field: valid_status,
        },
    )

    assert response.status_code == 422


def test_order_status_update_api_rejects_invalid_status(
    authenticated_api,
):
    """
    The endpoint must reject a status value
    that is not part of OrderStatus.
    """

    openapi_response = client.get(
        "/openapi.json"
    )

    assert openapi_response.status_code == 200

    openapi = openapi_response.json()

    method, path, _ = (
        _get_status_update_operation(
            openapi
        )
    )

    response = client.request(
        method,
        path.replace(
            "{order_id}",
            str(uuid4()),
        ),
        json={
            _get_status_field_name(openapi): (
                "INVALID_STATUS"
            ),
        },
    )

    assert response.status_code == 422


def test_order_status_update_api_requires_request_body(
    authenticated_api,
):
    """
    The endpoint must reject a request without
    the required status update body.
    """

    openapi_response = client.get(
        "/openapi.json"
    )

    assert openapi_response.status_code == 200

    openapi = openapi_response.json()

    method, path, _ = (
        _get_status_update_operation(
            openapi
        )
    )

    response = client.request(
        method,
        path.replace(
            "{order_id}",
            str(uuid4()),
        ),
    )

    assert response.status_code == 422


def test_order_status_update_api_passes_request_to_service(
    authenticated_api,
    monkeypatch,
):
    """
    Verify that the API passes the authenticated tenant,
    order_id, and requested status to the service layer.
    """

    openapi_response = client.get(
        "/openapi.json"
    )

    assert openapi_response.status_code == 200

    openapi = openapi_response.json()

    method, path, _ = (
        _get_status_update_operation(
            openapi
        )
    )

    status_field = _get_status_field_name(
        openapi
    )

    valid_status = _get_valid_status_value(
        openapi
    )

    order_id = uuid4()

    captured = {}

    def fake_update_order_status(
        **kwargs,
    ):
        captured.update(kwargs)

        raise HTTPException(
            status_code=400,
            detail="Service reached.",
        )

    monkeypatch.setattr(
        "app.api.v1.orders.update_order_status",
        fake_update_order_status,
    )

    response = client.request(
        method,
        path.replace(
            "{order_id}",
            str(order_id),
        ),
        json={
            status_field: valid_status,
        },
    )

    assert response.status_code == 400

    assert captured["tenant_id"] == TENANT_ID
    assert captured["order_id"] == order_id

    assert (
        captured["new_status"].value
        == valid_status
    )