from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.branch import Branch
from app.database.models.inventory_batch import InventoryBatch
from app.database.models.inventory_item import InventoryItem
from app.database.models.inventory_movement import InventoryMovement
from app.repositories.branch import BranchRepository
from app.repositories.inventory import InventoryItemRepository


def consume_inventory(
    db: Session,
    tenant_id: UUID,
    branch_id: UUID,
    ingredient_id: UUID,
    quantity: Decimal,
    *,
    commit: bool = True,
) -> None:
    """
    Consume inventory for an ingredient using FEFO.

    When commit=False, the changes remain inside the current
    database transaction so multiple consumptions can be
    committed atomically by the caller.
    """

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

    # ---------------------------------------------------------
    # 1. Find the inventory item for this branch and ingredient
    # ---------------------------------------------------------
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

    # ---------------------------------------------------------
    # 2. Find active batches belonging to this inventory item
    # ---------------------------------------------------------
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

    remaining = quantity

    try:
        # -----------------------------------------------------
        # 3. Consume batches using FEFO
        # -----------------------------------------------------
        for batch in batches:
            if remaining <= 0:
                break

            consumed_quantity = min(
                batch.quantity,
                remaining,
            )

            batch.quantity -= consumed_quantity
            remaining -= consumed_quantity

            movement = InventoryMovement(
                inventory_item_id=inventory_item.id,
                inventory_batch_id=batch.id,
                purchase_item_id=None,
                movement_type="SALE_CONSUMPTION",
                quantity=consumed_quantity,
                note=None,
            )

            db.add(movement)

            if batch.quantity == 0:
                batch.is_active = False

        # -----------------------------------------------------
        # 4. Make sure enough active batches existed
        # -----------------------------------------------------
        if remaining > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient active inventory batches.",
            )

        # -----------------------------------------------------
        # 5. Update total inventory quantity
        # -----------------------------------------------------
        inventory_item.quantity -= quantity

        # -----------------------------------------------------
        # 6. Commit only when requested
        # -----------------------------------------------------
        if commit:
            db.commit()

    except Exception:
        db.rollback()
        raise
    
    
def get_low_stock_items(
    db: Session,
    tenant_id: UUID,
    branch_id: UUID,
) -> list[dict]:
    """
    Return active inventory items that are at or below reorder level.
    """

    branch = db.scalar(
        select(Branch).where(
            Branch.id == branch_id,
            Branch.tenant_id == tenant_id,
        )
    )

    if branch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found.",
        )

    repository = InventoryItemRepository(db)

    items = repository.get_low_stock_items(
        branch_id=branch_id,
    )

    return [
        {
            "inventory_item_id": item.id,
            "branch_id": item.branch_id,
            "ingredient_id": item.ingredient_id,
            "quantity": item.quantity,
            "reorder_level": item.reorder_level,
            "shortage_quantity": max(
                item.reorder_level - item.quantity,
                Decimal("0"),
            ),
        }
        for item in items
    ]


def get_expiry_summary(
    db: Session,
    tenant_id: UUID,
    branch_id: UUID,
    expiring_soon_days: int = 7,
) -> dict:
    """
    Return expired and soon-to-expire inventory batches.
    """

    branch = db.scalar(
        select(Branch).where(
            Branch.id == branch_id,
            Branch.tenant_id == tenant_id,
        )
    )

    if branch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found.",
        )

    if expiring_soon_days < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="expiring_soon_days must be zero or greater.",
        )

    repository = InventoryItemRepository(db)

    batch_rows = repository.get_expiring_batches(
        branch_id=branch_id,
    )

    now = datetime.now(timezone.utc)

    batches = []
    expired_count = 0
    expiring_soon_count = 0

    for batch, inventory_item in batch_rows:
        expires_at = batch.expires_at

        if expires_at is None:
            continue

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(
                tzinfo=timezone.utc,
            )

        remaining_seconds = (
            expires_at - now
        ).total_seconds()

        days_until_expiry = int(
            remaining_seconds // 86400
        )

        is_expired = remaining_seconds < 0

        is_expiring_soon = (
            not is_expired
            and remaining_seconds
            <= expiring_soon_days * 86400
        )

        if is_expired:
            expired_count += 1

        elif is_expiring_soon:
            expiring_soon_count += 1

        batches.append(
            {
                "inventory_batch_id": batch.id,
                "inventory_item_id": batch.inventory_item_id,
                "branch_id": inventory_item.branch_id,
                "ingredient_id": inventory_item.ingredient_id,
                "batch_number": batch.batch_number,
                "quantity": batch.quantity,
                "expires_at": expires_at,
                "days_until_expiry": days_until_expiry,
                "is_expired": is_expired,
                "is_expiring_soon": is_expiring_soon,
            }
        )

    return {
        "branch_id": branch_id,
        "expiring_soon_days": expiring_soon_days,
        "expired_count": expired_count,
        "expiring_soon_count": expiring_soon_count,
        "batches": batches,
    }
    
    
def get_inventory_summary(
    db: Session,
    tenant_id: UUID,
    branch_id: UUID,
    expiring_soon_days: int = 7,
) -> dict:
    """
    Return a summarized inventory status for a branch.
    """

    branch = db.scalar(
        select(Branch).where(
            Branch.id == branch_id,
            Branch.tenant_id == tenant_id,
        )
    )

    if branch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found.",
        )

    if expiring_soon_days < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="expiring_soon_days must be zero or greater.",
        )

    repository = InventoryItemRepository(db)

    active_inventory_item_count = (
        repository.get_active_item_count(
            branch_id=branch_id,
        )
    )

    low_stock_items = repository.get_low_stock_items(
        branch_id=branch_id,
    )

    expiry_summary = get_expiry_summary(
        db=db,
        tenant_id=tenant_id,
        branch_id=branch_id,
        expiring_soon_days=expiring_soon_days,
    )

    return {
        "branch_id": branch_id,
        "active_inventory_item_count": (
            active_inventory_item_count
        ),
        "low_stock_count": len(low_stock_items),
        "expired_batch_count": (
            expiry_summary["expired_count"]
        ),
        "expiring_soon_batch_count": (
            expiry_summary["expiring_soon_count"]
        ),
        "expiring_soon_days": expiring_soon_days,
    }
    
    
def get_inventory_valuation(
    db: Session,
    tenant_id: UUID,
    branch_id: UUID,
    expiring_soon_days: int = 7,
) -> dict:
    """
    Return monetary inventory valuation for a branch.
    """

    branch = db.scalar(
        select(Branch).where(
            Branch.id == branch_id,
            Branch.tenant_id == tenant_id,
        )
    )

    if branch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found.",
        )

    if expiring_soon_days < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="expiring_soon_days must be zero or greater.",
        )

    repository = InventoryItemRepository(db)

    batch_rows = repository.get_active_batches_for_valuation(
        branch_id=branch_id,
    )

    now = datetime.now(timezone.utc)

    total_inventory_value = Decimal("0")
    low_stock_inventory_value = Decimal("0")
    expired_inventory_value = Decimal("0")
    expiring_soon_inventory_value = Decimal("0")

    low_stock_items = {
        item.id
        for item in repository.get_low_stock_items(
            branch_id=branch_id,
        )
    }

    for batch, inventory_item in batch_rows:
        batch_value = (
            batch.quantity * batch.cost_per_unit
        )

        total_inventory_value += batch_value

        if inventory_item.id in low_stock_items:
            low_stock_inventory_value += batch_value

        if batch.expires_at is not None:
            expires_at = batch.expires_at

            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(
                    tzinfo=timezone.utc,
                )

            remaining_seconds = (
                expires_at - now
            ).total_seconds()

            if remaining_seconds < 0:
                expired_inventory_value += batch_value

            elif (
                remaining_seconds
                <= expiring_soon_days * 86400
            ):
                expiring_soon_inventory_value += batch_value

    return {
        "branch_id": branch_id,
        "total_inventory_value": total_inventory_value,
        "low_stock_inventory_value": low_stock_inventory_value,
        "expired_inventory_value": expired_inventory_value,
        "expiring_soon_inventory_value": (
            expiring_soon_inventory_value
        ),
        "expiring_soon_days": expiring_soon_days,
    }
    
    
def get_inventory_consumption_analytics(
    db: Session,
    tenant_id: UUID,
    branch_id: UUID,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
) -> dict:
    """
    Return inventory consumption analytics for a branch.

    Only SALE_CONSUMPTION movements are included.
    """

    branch = db.scalar(
        select(Branch).where(
            Branch.id == branch_id,
            Branch.tenant_id == tenant_id,
        )
    )

    if branch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found.",
        )

    if (
        start_at is not None
        and end_at is not None
        and start_at > end_at
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "start_at must be earlier than or equal to end_at."
            ),
        )

    repository = InventoryItemRepository(db)

    rows = repository.get_consumption_analytics(
        branch_id=branch_id,
        start_at=start_at,
        end_at=end_at,
    )

    ingredients = []

    total_movement_count = 0
    total_consumption_value = Decimal("0")

    for (
        ingredient_id,
        movement_count,
        consumed_quantity,
        consumption_value,
    ) in rows:
        consumed_quantity = (
            consumed_quantity or Decimal("0")
        )

        consumption_value = (
            consumption_value or Decimal("0")
        )

        total_movement_count += movement_count
        total_consumption_value += consumption_value

        ingredients.append(
            {
                "ingredient_id": ingredient_id,
                "movement_count": movement_count,
                "consumed_quantity": consumed_quantity,
                "consumption_value": consumption_value,
            }
        )

    return {
        "branch_id": branch_id,
        "total_movement_count": total_movement_count,
        "ingredient_count": len(ingredients),
        "total_consumption_value": total_consumption_value,
        "ingredients": ingredients,
    }
    

def record_inventory_waste(
    db: Session,
    tenant_id: UUID,
    branch_id: UUID,
    ingredient_id: UUID,
    quantity: Decimal,
    note: str | None = None,
) -> dict:
    """
    Record inventory waste using FEFO and reduce current stock.

    Each consumed batch creates a WASTE inventory movement.
    """

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

    remaining = quantity
    total_waste_value = Decimal("0")
    movement_count = 0

    try:
        for batch in batches:
            if remaining <= 0:
                break

            wasted_quantity = min(
                batch.quantity,
                remaining,
            )

            batch.quantity -= wasted_quantity
            remaining -= wasted_quantity

            total_waste_value += (
                wasted_quantity * batch.cost_per_unit
            )

            movement = InventoryMovement(
                inventory_item_id=inventory_item.id,
                inventory_batch_id=batch.id,
                purchase_item_id=None,
                movement_type="WASTE",
                quantity=wasted_quantity,
                note=note,
            )

            db.add(movement)

            movement_count += 1

            if batch.quantity == 0:
                batch.is_active = False

        if remaining > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient active inventory batches.",
            )

        inventory_item.quantity -= quantity

        db.commit()

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise

    return {
        "branch_id": branch_id,
        "ingredient_id": ingredient_id,
        "quantity": quantity,
        "waste_value": total_waste_value,
        "movement_count": movement_count,
    }
    
    
def get_inventory_waste_analytics(
    db: Session,
    tenant_id: UUID,
    branch_id: UUID,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
) -> dict:
    """
    Return inventory waste analytics for a branch.
    """

    branch = db.scalar(
        select(Branch).where(
            Branch.id == branch_id,
            Branch.tenant_id == tenant_id,
        )
    )

    if branch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found.",
        )

    if (
        start_at is not None
        and end_at is not None
        and start_at > end_at
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "start_at must be earlier than or equal to end_at."
            ),
        )

    repository = InventoryItemRepository(db)

    rows = repository.get_waste_analytics(
        branch_id=branch_id,
        start_at=start_at,
        end_at=end_at,
    )

    ingredients = []

    total_movement_count = 0
    total_wasted_quantity = Decimal("0")
    total_waste_value = Decimal("0")

    for (
        ingredient_id,
        movement_count,
        wasted_quantity,
        waste_value,
    ) in rows:
        wasted_quantity = (
            wasted_quantity or Decimal("0")
        )

        waste_value = (
            waste_value or Decimal("0")
        )

        total_movement_count += movement_count
        total_wasted_quantity += wasted_quantity
        total_waste_value += waste_value

        ingredients.append(
            {
                "ingredient_id": ingredient_id,
                "movement_count": movement_count,
                "wasted_quantity": wasted_quantity,
                "waste_value": waste_value,
            }
        )

    return {
        "branch_id": branch_id,
        "total_movement_count": total_movement_count,
        "ingredient_count": len(ingredients),
        "total_wasted_quantity": total_wasted_quantity,
        "total_waste_value": total_waste_value,
        "ingredients": ingredients,
    }