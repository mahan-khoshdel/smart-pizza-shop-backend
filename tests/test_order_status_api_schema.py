"""
OpenAPI contract tests for the order status update endpoint.
"""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _get_status_update_operation(openapi: dict) -> tuple[str, dict]:
    """
    Find the Order status update operation from OpenAPI.

    The HTTP method is discovered from the request schema
    instead of being hard-coded.
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
                    return method.upper(), operation

    raise AssertionError(
        "Order status update operation was not found in OpenAPI."
    )


def test_order_status_update_endpoint_exists():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    openapi = response.json()

    method, operation = _get_status_update_operation(
        openapi
    )

    assert method in {
        "PUT",
        "PATCH",
        "POST",
    }

    assert operation is not None


def test_order_status_update_endpoint_uses_order_id():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    openapi = response.json()

    paths = openapi["paths"]

    matching_paths = [
        path
        for path in paths
        if (
            "/orders/" in path
            and "{order_id}" in path
        )
    ]

    assert matching_paths


def test_order_status_update_requires_authentication():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    openapi = response.json()

    _, operation = _get_status_update_operation(
        openapi
    )

    security = operation.get(
        "security",
        [],
    )

    assert security


def test_order_status_update_returns_order_response():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    openapi = response.json()

    _, operation = _get_status_update_operation(
        openapi
    )

    responses = operation["responses"]

    success_response = None

    for status_code in (
        "200",
        "201",
    ):
        if status_code in responses:
            success_response = responses[status_code]
            break

    assert success_response is not None

    content = success_response["content"]

    json_schema = content["application/json"][
        "schema"
    ]

    assert json_schema["$ref"].endswith(
        "/OrderResponse"
    )