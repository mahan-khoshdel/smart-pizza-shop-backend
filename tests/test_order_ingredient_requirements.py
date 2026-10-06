from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repositories.recipe import RecipeRepository
from app.schemas.order import OrderCreate
from app.services.order import (
    create_order,
    get_order_ingredient_requirements,
)


TENANT_ID = UUID(
    "25291ef5-0240-4042-aabc-b92c5aa4957a"
)

BRANCH_ID = UUID(
    "6146f071-baf4-40e9-bbff-71f86e0a7770"
)

PRODUCT_VARIANT_ID = UUID(
    "7c065b06-1422-446b-a163-d6a30b4b659b"
)

FAKE_OTHER_TENANT_ID = UUID(
    "00000000-0000-0000-0000-000000000001"
)


def _create_test_order(
    db: Session,
    quantity: int,
):
    """
    Create a unique test order for ingredient
    requirement calculations.
    """

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


def test_order_ingredient_requirements_are_calculated_from_active_recipe(
    db_session: Session,
):
    """
    Verify that ingredient requirements are calculated from
    the active recipe and scaled by the ordered quantity.
    """

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

    order_quantity = 2

    created_order = _create_test_order(
        db=db_session,
        quantity=order_quantity,
    )

    result = get_order_ingredient_requirements(
        db=db_session,
        tenant_id=TENANT_ID,
        order_id=created_order["id"],
    )

    assert result["order_id"] == created_order["id"]
    assert result["requirements"]

    expected_requirements: dict[UUID, Decimal] = {}

    for recipe_item in recipe_items:
        required_quantity = (
            recipe_item.quantity * order_quantity
        )

        expected_requirements[recipe_item.ingredient_id] = (
            expected_requirements.get(
                recipe_item.ingredient_id,
                Decimal("0"),
            )
            + required_quantity
        )

    actual_requirements = {
        item["ingredient_id"]: item["quantity"]
        for item in result["requirements"]
    }

    assert actual_requirements == expected_requirements


def test_order_ingredient_requirements_are_tenant_scoped(
    db_session: Session,
):
    """
    Verify that ingredient requirements cannot be accessed
    through another tenant context.
    """

    created_order = _create_test_order(
        db=db_session,
        quantity=1,
    )

    with pytest.raises(HTTPException) as exc_info:
        get_order_ingredient_requirements(
            db=db_session,
            tenant_id=FAKE_OTHER_TENANT_ID,
            order_id=created_order["id"],
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Order not found."