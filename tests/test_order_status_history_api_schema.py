"""
OpenAPI and API contract tests for the order status history endpoint.
"""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


STATUS_HISTORY_PATH = (
    "/api/v1/orders/{order_id}/status-history"
)

EXPECTED_HISTORY_FIELDS = {
    "id",
    "order_id",
    "from_status",
    "to_status",
    "changed_at",
    "note",
}


def _get_openapi() -> dict:
    """
    Return the application's OpenAPI document.
    """
    response = client.get("/openapi.json")

    assert response.status_code == 200

    return response.json()


def _get_status_history_operation(openapi: dict) -> dict:
    """
    Return the GET operation for the order status history endpoint.
    """
    paths = openapi["paths"]

    assert STATUS_HISTORY_PATH in paths, (
        "Order status history endpoint is missing "
        "from OpenAPI."
    )

    operation = paths[STATUS_HISTORY_PATH].get("get")

    assert operation is not None, (
        "GET operation for order status history "
        "was not found."
    )

    return operation


def test_order_status_history_endpoint_exists():
    """
    Verify that the order status history endpoint
    is exposed as a GET endpoint.
    """
    openapi = _get_openapi()

    operation = _get_status_history_operation(
        openapi
    )

    assert operation is not None


def test_order_status_history_uses_order_id_uuid():
    """
    Verify that order_id is declared as a UUID path parameter.
    """
    openapi = _get_openapi()

    operation = _get_status_history_operation(
        openapi
    )

    parameters = operation.get(
        "parameters",
        [],
    )

    order_id_parameter = next(
        (
            parameter
            for parameter in parameters
            if parameter.get("name") == "order_id"
        ),
        None,
    )

    assert order_id_parameter is not None, (
        "order_id path parameter is missing."
    )

    assert order_id_parameter.get("in") == "path"
    assert order_id_parameter.get("required") is True

    schema = order_id_parameter.get(
        "schema",
        {},
    )

    assert schema.get("type") == "string"
    assert schema.get("format") == "uuid"


def test_order_status_history_requires_authentication():
    """
    Verify that the endpoint declares an authentication requirement.
    """
    openapi = _get_openapi()

    operation = _get_status_history_operation(
        openapi
    )

    security = operation.get(
        "security",
        [],
    )

    global_security = openapi.get(
        "security",
        [],
    )

    assert security or global_security, (
        "Order status history endpoint does not "
        "declare an authentication requirement."
    )


def test_order_status_history_returns_history_response_list():
    """
    Verify that the successful response is an array of
    OrderStatusHistoryResponse objects.
    """
    openapi = _get_openapi()

    operation = _get_status_history_operation(
        openapi
    )

    responses = operation.get(
        "responses",
        {},
    )

    success_response = responses.get("200")

    assert success_response is not None, (
        "Successful 200 response is missing."
    )

    content = success_response.get(
        "content",
        {},
    )

    assert "application/json" in content

    response_schema = content[
        "application/json"
    ].get(
        "schema",
        {},
    )

    assert response_schema.get("type") == "array"

    items_schema = response_schema.get(
        "items",
        {},
    )

    assert items_schema.get(
        "$ref",
        "",
    ).endswith(
        "/OrderStatusHistoryResponse"
    )


def test_order_status_history_response_schema_contains_expected_fields():
    """
    Verify that OrderStatusHistoryResponse exposes all
    fields required by the API contract.
    """
    openapi = _get_openapi()

    schemas = openapi.get(
        "components",
        {},
    ).get(
        "schemas",
        {},
    )

    history_schema = schemas.get(
        "OrderStatusHistoryResponse"
    )

    assert history_schema is not None, (
        "OrderStatusHistoryResponse schema "
        "is missing from OpenAPI."
    )

    properties = history_schema.get(
        "properties",
        {},
    )

    assert EXPECTED_HISTORY_FIELDS.issubset(
        properties.keys()
    )


def test_order_status_history_rejects_unauthenticated_request():
    """
    Verify that a request without authentication
    cannot access order status history.
    """
    order_id = (
        "00000000-0000-0000-0000-000000000099"
    )

    response = client.get(
        f"/api/v1/orders/{order_id}/status-history"
    )

    assert response.status_code in {
        401,
        403,
    }