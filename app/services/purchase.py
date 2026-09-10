from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.ingredient import Ingredient
from app.database.models.inventory_batch import InventoryBatch
from app.database.models.inventory_item import InventoryItem
from app.database.models.inventory_movement import InventoryMovement
from app.database.models.purchase import Purchase
from app.database.models.purchase_item import PurchaseItem
from app.repositories.branch import BranchRepository
from app.repositories.supplier import SupplierRepository
from app.schemas.purchase import PurchaseItemCreate
from app.utils.units import convert_quantity


def get_purchase(
    db: Session,
    purchase_id: UUID,
    tenant_id: UUID,
) -> Purchase | None:
    """Find a purchase within a tenant."""

    statement = select(Purchase).where(
        Purchase.id == purchase_id,
        Purchase.tenant_id == tenant_id,
    )

    return db.scalar(statement)


def receive_purchase(
    db: Session,
    purchase_id: UUID,
    tenant_id: UUID,
) -> None:
    """Receive a purchase and update inventory."""

    purchase = get_purchase(
        db=db,
        purchase_id=purchase_id,
        tenant_id=tenant_id,
    )

    if purchase is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase not found.",
        )

    if purchase.status != "DRAFT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft purchases can be received.",
        )

    purchase_items = db.scalars(
        select(PurchaseItem).where(
            PurchaseItem.purchase_id == purchase.id,
        )
    ).all()

    if not purchase_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Purchase has no items.",
        )

    try:
        for purchase_item in purchase_items:
            ingredient = db.get(
                Ingredient,
                purchase_item.ingredient_id,
            )

            if ingredient is None:
                raise ValueError("Ingredient not found.")

            inventory_item = db.scalar(
                select(InventoryItem).where(
                    InventoryItem.branch_id == purchase.branch_id,
                    InventoryItem.ingredient_id
                    == purchase_item.ingredient_id,
                )
            )

            if inventory_item is None:
                inventory_item = InventoryItem(
                    branch_id=purchase.branch_id,
                    ingredient_id=purchase_item.ingredient_id,
                    quantity=Decimal("0"),
                    reorder_level=Decimal("0"),
                )
                db.add(inventory_item)
                db.flush()

            base_quantity = convert_quantity(
                quantity=purchase_item.quantity,
                from_unit=purchase_item.unit,
                to_unit=ingredient.base_unit,
            )

            if purchase_item.unit == "KILOGRAM" and ingredient.base_unit == "GRAM":
                base_cost_per_unit = purchase_item.unit_cost / Decimal("1000")
            elif (
                purchase_item.unit == "LITER"
                and ingredient.base_unit == "MILLILITER"
            ):
                base_cost_per_unit = purchase_item.unit_cost / Decimal("1000")
            else:
                base_cost_per_unit = purchase_item.unit_cost

            inventory_item.quantity += base_quantity

            batch = InventoryBatch(
                inventory_item_id=inventory_item.id,
                purchase_item_id=purchase_item.id,
                batch_number=f"PUR-{purchase.purchase_number}-{purchase_item.id}",
                quantity=base_quantity,
                cost_per_unit=base_cost_per_unit,
            )

            db.add(batch)
            
            movement = InventoryMovement(
                inventory_item_id=inventory_item.id,
                movement_type="PURCHASE",
                quantity=base_quantity,
                note=f"Purchase {purchase.purchase_number}",
            )

            db.add(movement)

        purchase.status = "RECEIVED"

        db.commit()

    except Exception:
        db.rollback()
        raise
    
    
def create_purchase(
    db: Session,
    tenant_id: UUID,
    branch_id: UUID,
    supplier_id: UUID,
    purchase_number: str,
    items: list[PurchaseItemCreate],
    note: str | None = None,
) -> Purchase:
    """Create a draft purchase for a tenant."""

    branch_repository = BranchRepository(db)
    supplier_repository = SupplierRepository(db)

    branch = branch_repository.get_by_id(
        branch_id=branch_id,
        tenant_id=tenant_id,
    )

    if branch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found.",
        )

    supplier = supplier_repository.get_by_id(
        supplier_id=supplier_id,
        tenant_id=tenant_id,
    )

    if supplier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found.",
        )

    purchase = Purchase(
        tenant_id=tenant_id,
        branch_id=branch_id,
        supplier_id=supplier_id,
        purchase_number=purchase_number,
        status="DRAFT",
        note=note,
    )

    try:
        db.add(purchase)
        db.flush()

        for item in items:
            purchase_item = PurchaseItem(
                purchase_id=purchase.id,
                ingredient_id=item.ingredient_id,
                quantity=item.quantity,
                unit=item.unit,
                unit_cost=item.unit_cost,
                total_cost=item.quantity * item.unit_cost,
            )

            db.add(purchase_item)

        db.commit()
        db.refresh(purchase)

        return purchase

    except Exception:
        db.rollback()
        raise