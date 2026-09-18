from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.recipe import Recipe
from app.database.models.recipe_item import RecipeItem


class RecipeRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_active_by_product_variant(
        self,
        product_variant_id: UUID,
        tenant_id: UUID,
    ) -> Recipe | None:
        statement = select(Recipe).where(
            Recipe.product_variant_id == product_variant_id,
            Recipe.tenant_id == tenant_id,
            Recipe.is_active.is_(True),
        )

        return self.db.scalar(statement)

    def get_items(
        self,
        recipe_id: UUID,
    ) -> list[RecipeItem]:
        statement = (
            select(RecipeItem)
            .where(RecipeItem.recipe_id == recipe_id)
            .order_by(RecipeItem.ingredient_id.asc())
        )

        return list(self.db.scalars(statement).all())