from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _find_product_paths(openapi: dict) -> list[str]:
    paths = openapi["paths"]

    return [
        path
        for path in paths
        if "product" in path.lower()
        and "order" not in path.lower()
        and "inventory" not in path.lower()
    ]


def _get_product_operations(openapi: dict) -> list[tuple[str, str, dict]]:
    operations = []

    for path in _find_product_paths(openapi):
        path_operations = openapi["paths"][path]

        for method in [
            "get",
            "post",
            "put",
            "patch",
            "delete",
        ]:
            if method not in path_operations:
                continue

            operations.append(
                (
                    path,
                    method,
                    path_operations[method],
                )
            )

    return operations


def test_product_api_routes_are_registered():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    openapi = response.json()

    matching_paths = _find_product_paths(openapi)

    assert matching_paths, (
        "No Product API route "
        "was found in OpenAPI."
    )


def test_product_api_requires_authentication():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    openapi = response.json()

    matching_paths = _find_product_paths(openapi)

    assert matching_paths, (
        "No Product API route "
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
        "No protected Product API operation "
        "was found in OpenAPI."
    )


def test_product_api_exposes_get_operation():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    openapi = response.json()

    operations = _get_product_operations(openapi)

    assert operations, (
        "No Product API operation "
        "was found in OpenAPI."
    )

    get_operations = [
        (path, method)
        for path, method, operation in operations
        if method == "get"
    ]

    assert get_operations, (
        "No GET Product API operation "
        "was found in OpenAPI."
    )


def test_product_api_exposes_post_operation():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    openapi = response.json()

    operations = _get_product_operations(openapi)

    assert operations, (
        "No Product API operation "
        "was found in OpenAPI."
    )

    post_operations = [
        (path, method)
        for path, method, operation in operations
        if method == "post"
    ]

    assert post_operations, (
        "No POST Product API operation "
        "was found in OpenAPI."
    )


def test_all_product_api_operations_are_protected():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    openapi = response.json()

    operations = _get_product_operations(openapi)

    assert operations, (
        "No Product API operation "
        "was found in OpenAPI."
    )

    for path, method, operation in operations:
        assert (
            operation.get("security")
            or openapi.get("security")
        ), (
            f"Product API operation is not protected: "
            f"{method.upper()} {path}"
        )


def test_all_product_api_operations_define_responses():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    openapi = response.json()

    operations = _get_product_operations(openapi)

    assert operations, (
        "No Product API operation "
        "was found in OpenAPI."
    )

    for path, method, operation in operations:
        assert operation.get("responses"), (
            f"Product API operation has no response definitions: "
            f"{method.upper()} {path}"
        )