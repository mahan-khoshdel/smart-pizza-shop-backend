from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repositories.recipe import RecipeRepository
from app.schemas.order import OrderCreate
from app.services.order import (
    calculate_order_ingredient_requirements,
    create_order,
    get_order_ingredient_requirements,
)


TENANT_ID = UUID(
    "25291ef5-0240-4042-aabc-b92c5aa4957a"
)

FAKE_OTHER_TENANT_ID = UUID(
    "00000000-0000-0000-0000-000000000001"
)

BRANCH_ID = UUID(
    "6146f071-baf4-40e9-bbff-71f86e0a7770"
)

PRODUCT_VARIANT_ID = UUID(
    "7c065b06-1422-446b-a163-d6a30b4b659b"
)

NON_EXISTENT_ORDER_ID = UUID(
    "00000000-0000-0000-0000-000000000099"
)


def _create_test_order(
    db: Session,
    quantity: int = 1,
) -> dict:
    order_number = (
        f"TEST-INGREDIENT-"
        f"{uuid4().hex[:8]}"
    )

    order_data = OrderCreate(
        branch_id=BRANCH_ID,
        customer_id=None,
        customer_address_id=None,
        order_number=order_number,
        order_type="DINE_IN",
        note="Automated ingredient requirement test.",
        items=[
            {
                "product_variant_id": PRODUCT_VARIANT_ID,
                "quantity": quantity,
            }
        ],
    )

    return create_order(
        db=db,
        tenant_id=TENANT_ID,
        data=order_data,
    )


def test_calculate_order_ingredient_requirements_uses_active_recipe(
    db_session,
):
    created_order = _create_test_order(
        db=db_session,
        quantity=1,
    )

    requirements = calculate_order_ingredient_requirements(
        db=db_session,
        tenant_id=TENANT_ID,
        order_id=created_order["id"],
    )

    assert requirements
    assert all(
        ingredient_id is not None
        for ingredient_id in requirements
    )
    assert all(
        quantity > Decimal("0")
        for quantity in requirements.values()
    )

    recipe_repository = RecipeRepository(db_session)

    recipe = recipe_repository.get_active_by_product_variant(
        product_variant_id=PRODUCT_VARIANT_ID,
        tenant_id=TENANT_ID,
    )

    assert recipe is not None
    assert recipe.is_active is True

    recipe_items = recipe_repository.get_items(
        recipe_id=recipe.id,
    )

    assert recipe_items

    expected_requirements = {
        recipe_item.ingredient_id: recipe_item.quantity
        for recipe_item in recipe_items
    }

    assert requirements == expected_requirements


def test_calculate_order_ingredient_requirements_scales_with_order_quantity(
    db_session,
):
    created_order = _create_test_order(
        db=db_session,
        quantity=2,
    )

    requirements = calculate_order_ingredient_requirements(
        db=db_session,
        tenant_id=TENANT_ID,
        order_id=created_order["id"],
    )

    recipe_repository = RecipeRepository(db_session)

    recipe = recipe_repository.get_active_by_product_variant(
        product_variant_id=PRODUCT_VARIANT_ID,
        tenant_id=TENANT_ID,
    )

    assert recipe is not None

    recipe_items = recipe_repository.get_items(
        recipe_id=recipe.id,
    )

    assert recipe_items

    expected_requirements = {
        recipe_item.ingredient_id: (
            recipe_item.quantity * 2
        )
        for recipe_item in recipe_items
    }

    assert requirements == expected_requirements


def test_get_order_ingredient_requirements_returns_api_ready_structure(
    db_session,
):
    created_order = _create_test_order(
        db=db_session,
        quantity=1,
    )

    result = get_order_ingredient_requirements(
        db=db_session,
        tenant_id=TENANT_ID,
        order_id=created_order["id"],
    )

    assert result["order_id"] == created_order["id"]

    assert "requirements" in result
    assert result["requirements"]

    requirements = {
        item["ingredient_id"]: item["quantity"]
        for item in result["requirements"]
    }

    calculated_requirements = (
        calculate_order_ingredient_requirements(
            db=db_session,
            tenant_id=TENANT_ID,
            order_id=created_order["id"],
        )
    )

    assert requirements == calculated_requirements


def test_ingredient_requirements_are_tenant_scoped(
    db_session,
):
    created_order = _create_test_order(
        db=db_session,
        quantity=1,
    )

    with pytest.raises(HTTPException) as exc_info:
        calculate_order_ingredient_requirements(
            db=db_session,
            tenant_id=FAKE_OTHER_TENANT_ID,
            order_id=created_order["id"],
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Order not found."

    with pytest.raises(HTTPException) as exc_info:
        get_order_ingredient_requirements(
            db=db_session,
            tenant_id=FAKE_OTHER_TENANT_ID,
            order_id=created_order["id"],
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Order not found."


def test_ingredient_requirements_raise_404_for_missing_order(
    db_session,
):
    with pytest.raises(HTTPException) as exc_info:
        calculate_order_ingredient_requirements(
            db=db_session,
            tenant_id=TENANT_ID,
            order_id=NON_EXISTENT_ORDER_ID,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Order not found."

    with pytest.raises(HTTPException) as exc_info:
        get_order_ingredient_requirements(
            db=db_session,
            tenant_id=TENANT_ID,
            order_id=NON_EXISTENT_ORDER_ID,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Order not found."