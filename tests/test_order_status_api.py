from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _find_order_status_paths(openapi: dict) -> list[str]:
    paths = openapi["paths"]

    return [
        path
        for path in paths
        if "order" in path.lower()
        and "kitchen" not in path.lower()
        and (
            "status" in path.lower()
            or "history" in path.lower()
        )
    ]


def test_order_status_api_routes_are_registered():
    """
    Verify that Order Status / History API routes
    are registered in OpenAPI.
    """

    response = client.get("/openapi.json")

    assert response.status_code == 200

    openapi = response.json()

    matching_paths = _find_order_status_paths(openapi)

    assert matching_paths, (
        "No Order Status or Status History API route "
        "was found in OpenAPI."
    )


def test_order_status_api_requires_authentication():
    """
    Verify that Order Status / History API routes
    are protected by the authentication layer.
    """

    response = client.get("/openapi.json")

    assert response.status_code == 200

    openapi = response.json()

    matching_paths = _find_order_status_paths(openapi)

    assert matching_paths, (
        "No Order Status or Status History API route "
        "was found in OpenAPI."
    )

    protected_operation_found = False

    for path in matching_paths:
        operations = openapi["paths"][path]

        for method in [
            "get",
            "post",
            "put",
            "patch",
            "delete",
        ]:
            if method not in operations:
                continue

            operation = operations[method]

            if (
                operation.get("security")
                or openapi.get("security")
            ):
                protected_operation_found = True
                break

        if protected_operation_found:
            break

    assert protected_operation_found, (
        "No protected Order Status / History API "
        "operation was found in OpenAPI."
    )