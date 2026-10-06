from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _find_customer_paths(openapi: dict) -> list[str]:
    paths = openapi["paths"]

    return [
        path
        for path in paths
        if "customers" in path.lower()
        and "addresses" not in path.lower()
    ]


def test_customer_api_routes_are_registered():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    openapi = response.json()

    matching_paths = _find_customer_paths(openapi)

    assert matching_paths, (
        "No Customer API route "
        "was found in OpenAPI."
    )


def test_customer_api_requires_authentication():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    openapi = response.json()

    matching_paths = _find_customer_paths(openapi)

    assert matching_paths, (
        "No Customer API route "
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
        "No protected Customer API operation "
        "was found in OpenAPI."
    )