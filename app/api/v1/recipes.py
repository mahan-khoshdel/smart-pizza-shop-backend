from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_data
from app.database.connection import get_db
from app.schemas.recipe import RecipeCreate, RecipeResponse
from app.services.recipe import create_recipe


router = APIRouter(
    prefix="/recipes",
    tags=["Recipes"],
)


@router.post(
    "",
    response_model=RecipeResponse,
    status_code=201,
)
def create_recipe_endpoint(
    recipe_data: RecipeCreate,
    current_user=Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Create a new recipe for the current tenant.
    """

    return create_recipe(
        db=db,
        tenant_id=current_user["tenant_id"],
        data=recipe_data,
    )