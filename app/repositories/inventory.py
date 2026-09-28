from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.inventory_batch import InventoryBatch
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
    
    def get_low_stock_items(
        self,
        branch_id: UUID,
    ) -> list[InventoryItem]:
        """
        Return active inventory items at or below reorder level.
        """

        statement = (
            select(InventoryItem)
            .where(
                InventoryItem.branch_id == branch_id,
                InventoryItem.is_active.is_(True),
                InventoryItem.quantity <= InventoryItem.reorder_level,
            )
            .order_by(
                InventoryItem.quantity.asc(),
            )
        )

        return list(self.db.scalars(statement).all())

    def get_expiring_batches(
        self,
        branch_id: UUID,
    ) -> list[tuple[InventoryBatch, InventoryItem]]:
        """
        Return active inventory batches with remaining quantity
        and a defined expiry date.
        """

        statement = (
            select(
                InventoryBatch,
                InventoryItem,
            )
            .join(
                InventoryItem,
                InventoryItem.id == InventoryBatch.inventory_item_id,
            )
            .where(
                InventoryItem.branch_id == branch_id,
                InventoryItem.is_active.is_(True),
                InventoryBatch.is_active.is_(True),
                InventoryBatch.quantity > 0,
                InventoryBatch.expires_at.is_not(None),
            )
            .order_by(
                InventoryBatch.expires_at.asc(),
            )
        )

        return list(self.db.execute(statement).all())