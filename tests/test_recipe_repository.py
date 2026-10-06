from uuid import UUID

from app.repositories.recipe import RecipeRepository


TENANT_ID = UUID(
    "25291ef5-0240-4042-aabc-b92c5aa4957a"
)

FAKE_OTHER_TENANT_ID = UUID(
    "00000000-0000-0000-0000-000000000001"
)

PRODUCT_VARIANT_ID = UUID(
    "7c065b06-1422-446b-a163-d6a30b4b659b"
)


def test_recipe_repository_returns_active_recipe_for_product_variant(
    db_session,
):
    """
    Verify that RecipeRepository can find the active recipe
    for the expected product variant and tenant.
    """

    repository = RecipeRepository(db_session)

    recipe = repository.get_active_by_product_variant(
        product_variant_id=PRODUCT_VARIANT_ID,
        tenant_id=TENANT_ID,
    )

    assert recipe is not None
    assert recipe.product_variant_id == PRODUCT_VARIANT_ID
    assert recipe.tenant_id == TENANT_ID
    assert recipe.is_active is True


def test_recipe_repository_does_not_return_recipe_for_other_tenant(
    db_session,
):
    """
    Verify that an active recipe cannot be accessed
    through another tenant context.
    """

    repository = RecipeRepository(db_session)

    recipe = repository.get_active_by_product_variant(
        product_variant_id=PRODUCT_VARIANT_ID,
        tenant_id=FAKE_OTHER_TENANT_ID,
    )

    assert recipe is None


def test_recipe_repository_returns_items_for_recipe(
    db_session,
):
    """
    Verify that RecipeRepository returns the ingredient
    items belonging to the active recipe.
    """

    repository = RecipeRepository(db_session)

    recipe = repository.get_active_by_product_variant(
        product_variant_id=PRODUCT_VARIANT_ID,
        tenant_id=TENANT_ID,
    )

    assert recipe is not None

    recipe_items = repository.get_items(
        recipe_id=recipe.id,
    )

    assert recipe_items

    assert all(
        recipe_item.recipe_id == recipe.id
        for recipe_item in recipe_items
    )

    assert all(
        recipe_item.ingredient_id is not None
        for recipe_item in recipe_items
    )

    assert all(
        recipe_item.quantity > 0
        for recipe_item in recipe_items
    )