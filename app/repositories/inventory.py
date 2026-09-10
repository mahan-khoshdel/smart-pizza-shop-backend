from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.inventory_item import InventoryItem


class InventoryItemRepository:
    """Handle database operations related to inventory items."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_branch_and_ingredient(
        self,
        branch_id: UUID,
        ingredient_id: UUID,
    ) -> InventoryItem | None:
        """Find inventory for an ingredient at a branch."""
        statement = select(InventoryItem).where(
            InventoryItem.branch_id == branch_id,
            InventoryItem.ingredient_id == ingredient_id,
        )

        return self.db.scalar(statement)