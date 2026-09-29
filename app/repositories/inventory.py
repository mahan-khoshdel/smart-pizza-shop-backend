from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models.inventory_batch import InventoryBatch
from app.database.models.inventory_item import InventoryItem
from app.database.models.inventory_movement import InventoryMovement


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
    
    def get_active_item_count(
        self,
        branch_id: UUID,
    ) -> int:
        """Return the number of active inventory items at a branch."""

        statement = select(
            func.count(InventoryItem.id)
        ).where(
            InventoryItem.branch_id == branch_id,
            InventoryItem.is_active.is_(True),
        )

        return int(self.db.scalar(statement) or 0)
    
    def get_active_batches_for_valuation(
        self,
        branch_id: UUID,
    ) -> list[tuple[InventoryBatch, InventoryItem]]:
        """
        Return active non-empty inventory batches for valuation.
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
            )
        )

        return list(self.db.execute(statement).all())
    
    def get_consumption_analytics(
        self,
        branch_id: UUID,
        start_at=None,
        end_at=None,
    ) -> list[tuple[UUID, int, object, object]]:
        """
        Return aggregated sale-consumption analytics by ingredient.
        """

        statement = (
            select(
                InventoryItem.ingredient_id,
                func.count(InventoryMovement.id).label(
                    "movement_count"
                ),
                func.sum(
                    InventoryMovement.quantity
                ).label(
                    "consumed_quantity"
                ),
                func.sum(
                    InventoryMovement.quantity
                    * InventoryBatch.cost_per_unit
                ).label(
                    "consumption_value"
                ),
            )
            .join(
                InventoryMovement,
                InventoryMovement.inventory_item_id
                == InventoryItem.id,
            )
            .join(
                InventoryBatch,
                InventoryBatch.id
                == InventoryMovement.inventory_batch_id,
            )
            .where(
                InventoryItem.branch_id == branch_id,
                InventoryMovement.movement_type
                == "SALE_CONSUMPTION",
            )
            .group_by(
                InventoryItem.ingredient_id,
            )
            .order_by(
                InventoryItem.ingredient_id.asc(),
            )
        )

        if start_at is not None:
            statement = statement.where(
                InventoryMovement.created_at >= start_at,
            )

        if end_at is not None:
            statement = statement.where(
                InventoryMovement.created_at <= end_at,
            )

        rows = self.db.execute(statement).all()

        return [
            (
                ingredient_id,
                int(movement_count),
                consumed_quantity,
                consumption_value,
            )
            for (
                ingredient_id,
                movement_count,
                consumed_quantity,
                consumption_value,
            ) in rows
        ]
        
    def get_waste_analytics(
        self,
        branch_id: UUID,
        start_at=None,
        end_at=None,
    ) -> list[tuple[UUID, int, object, object]]:
        """
        Return aggregated waste analytics by ingredient.
        """

        statement = (
            select(
                InventoryItem.ingredient_id,
                func.count(InventoryMovement.id).label(
                    "movement_count"
                ),
                func.sum(
                    InventoryMovement.quantity
                ).label(
                    "wasted_quantity"
                ),
                func.sum(
                    InventoryMovement.quantity
                    * InventoryBatch.cost_per_unit
                ).label(
                    "waste_value"
                ),
            )
            .join(
                InventoryMovement,
                InventoryMovement.inventory_item_id
                == InventoryItem.id,
            )
            .join(
                InventoryBatch,
                InventoryBatch.id
                == InventoryMovement.inventory_batch_id,
            )
            .where(
                InventoryItem.branch_id == branch_id,
                InventoryMovement.movement_type == "WASTE",
            )
            .group_by(
                InventoryItem.ingredient_id,
            )
            .order_by(
                InventoryItem.ingredient_id.asc(),
            )
        )

        if start_at is not None:
            statement = statement.where(
                InventoryMovement.created_at >= start_at,
            )

        if end_at is not None:
            statement = statement.where(
                InventoryMovement.created_at <= end_at,
            )

        rows = self.db.execute(statement).all()

        return [
            (
                ingredient_id,
                int(movement_count),
                wasted_quantity,
                waste_value,
            )
            for (
                ingredient_id,
                movement_count,
                wasted_quantity,
                waste_value,
            ) in rows
        ]