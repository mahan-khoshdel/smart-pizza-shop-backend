from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.ingredient import Ingredient
from app.database.models.product_variant import ProductVariant
from app.database.models.recipe import Recipe
from app.database.models.recipe_item import RecipeItem
from app.repositories.recipe import RecipeRepository
from app.schemas.recipe import RecipeCreate


def create_recipe(
    db: Session,
    tenant_id: UUID,
    data: RecipeCreate,
) -> dict:
    """
    Create a recipe for a product variant and its ingredient items.
    """

    product_variant = db.scalar(
        select(ProductVariant).where(
            ProductVariant.id == data.product_variant_id,
            ProductVariant.tenant_id == tenant_id,
        )
    )

    if product_variant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product variant not found.",
        )

    recipe_repository = RecipeRepository(db)

    existing_recipe = recipe_repository.get_active_by_product_variant(
        product_variant_id=data.product_variant_id,
        tenant_id=tenant_id,
    )

    if existing_recipe is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An active recipe already exists for this product variant.",
        )

    if not data.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recipe must contain at least one ingredient.",
        )

    recipe = Recipe(
        tenant_id=tenant_id,
        product_variant_id=data.product_variant_id,
        name=data.name,
        is_active=True,
    )

    try:
        db.add(recipe)
        db.flush()

        for item_data in data.items:
            if item_data.quantity <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Recipe ingredient quantity must be greater than zero.",
                )

            ingredient = db.scalar(
                select(Ingredient).where(
                    Ingredient.id == item_data.ingredient_id,
                    Ingredient.tenant_id == tenant_id,
                )
            )

            if ingredient is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=(
                        "Ingredient not found: "
                        f"{item_data.ingredient_id}"
                    ),
                )

            recipe_item = RecipeItem(
                recipe_id=recipe.id,
                ingredient_id=ingredient.id,
                quantity=item_data.quantity,
            )

            db.add(recipe_item)

        db.commit()
        db.refresh(recipe)

        items = recipe_repository.get_items(
            recipe_id=recipe.id,
        )

        return {
            "id": recipe.id,
            "tenant_id": recipe.tenant_id,
            "product_variant_id": recipe.product_variant_id,
            "name": recipe.name,
            "is_active": recipe.is_active,
            "items": items,
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise