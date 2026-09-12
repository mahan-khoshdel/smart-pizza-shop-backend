from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.inventory_batch import InventoryBatch
from app.database.models.inventory_item import InventoryItem
from app.database.models.inventory_movement import InventoryMovement
from app.repositories.branch import BranchRepository


def consume_inventory(
    db: Session,
    tenant_id: UUID,
    branch_id: UUID,
    ingredient_id: UUID,
    quantity: Decimal,
) -> None:
    """Consume ingredient quantity using FEFO."""

    branch_repository = BranchRepository(db)

    branch = branch_repository.get_by_id(
        branch_id=branch_id,
        tenant_id=tenant_id,
    )

    if branch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found.",
        )

    if quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity must be greater than zero.",
        )

    inventory_item = db.scalar(
        select(InventoryItem).where(
            InventoryItem.branch_id == branch_id,
            InventoryItem.ingredient_id == ingredient_id,
        )
    )

    if inventory_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found.",
        )

    if inventory_item.quantity < quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient inventory.",
        )

    batches = db.scalars(
        select(InventoryBatch)
        .where(
            InventoryBatch.inventory_item_id == inventory_item.id,
            InventoryBatch.is_active.is_(True),
            InventoryBatch.quantity > 0,
        )
        .order_by(
            InventoryBatch.expires_at.asc().nulls_last(),
            InventoryBatch.received_at.asc(),
        )
    ).all()

    remaining_quantity = quantity

    try:
        for batch in batches:
            if remaining_quantity <= 0:
                break

            consumed_quantity = min(
                batch.quantity,
                remaining_quantity,
            )

            batch.quantity -= consumed_quantity
            remaining_quantity -= consumed_quantity

            movement = InventoryMovement(
                inventory_item_id=inventory_item.id,
                inventory_batch_id=batch.id,
                purchase_item_id=None,
                movement_type="SALE_CONSUMPTION",
                quantity=consumed_quantity,
            )

            db.add(movement)

            if batch.quantity == 0:
                batch.is_active = False

        if remaining_quantity > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient active inventory batches.",
            )

        inventory_item.quantity -= quantity

        db.commit()

    except Exception:
        db.rollback()
        raise