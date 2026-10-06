from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _find_customer_address_paths(openapi: dict) -> list[str]:
    paths = openapi["paths"]

    return [
        path
        for path in paths
        if "customers" in path.lower()
        and "addresses" in path.lower()
    ]


def test_customer_address_api_routes_are_registered():
    """
    Verify that Customer Address API routes
    are registered in OpenAPI.
    """

    response = client.get("/openapi.json")

    assert response.status_code == 200

    openapi = response.json()

    matching_paths = _find_customer_address_paths(
        openapi
    )

    assert matching_paths, (
        "No Customer Address API route "
        "was found in OpenAPI."
    )


def test_customer_address_api_requires_authentication():
    """
    Verify that Customer Address API operations
    are protected by the authentication layer.
    """

    response = client.get("/openapi.json")

    assert response.status_code == 200

    openapi = response.json()

    matching_paths = _find_customer_address_paths(
        openapi
    )

    assert matching_paths, (
        "No Customer Address API route "
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
        "No protected Customer Address API operation "
        "was found in OpenAPI."
    )