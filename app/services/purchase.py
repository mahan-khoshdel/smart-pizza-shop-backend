from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.expense import Expense, ExpenseCategory
from app.database.models.ingredient import Ingredient
from app.database.models.inventory_batch import InventoryBatch
from app.database.models.inventory_item import InventoryItem
from app.database.models.inventory_movement import InventoryMovement
from app.database.models.purchase import Purchase
from app.database.models.purchase_item import PurchaseItem
from app.repositories.branch import BranchRepository
from app.repositories.purchase import PurchaseRepository
from app.repositories.supplier import SupplierRepository
from app.schemas.purchase import PurchaseItemCreate
from app.schemas.purchase_receive import PurchaseReceiveItem
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


def list_purchases(
    db: Session,
    tenant_id: UUID,
    branch_id: UUID | None = None,
    supplier_id: UUID | None = None,
    purchase_status: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> tuple[list[Purchase], int]:
    """Return purchases filtered within the current tenant."""

    repository = PurchaseRepository(db)

    return repository.list_purchases(
        tenant_id=tenant_id,
        branch_id=branch_id,
        supplier_id=supplier_id,
        status=purchase_status,
        start_date=start_date,
        end_date=end_date,
    )
    
    
def get_purchase_summary(
    db: Session,
    tenant_id: UUID,
    branch_id: UUID | None = None,
    supplier_id: UUID | None = None,
    purchase_status: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict:
    """Return aggregated purchase statistics for the current tenant."""

    repository = PurchaseRepository(db)

    summary = repository.get_summary(
        tenant_id=tenant_id,
        branch_id=branch_id,
        supplier_id=supplier_id,
        status=purchase_status,
        start_date=start_date,
        end_date=end_date,
    )

    return {
        "branch_id": branch_id,
        "supplier_id": supplier_id,
        **summary,
    }


def get_purchase_detail(
    db: Session,
    purchase_id: UUID,
    tenant_id: UUID,
) -> dict:
    """Return a purchase with all of its items."""

    repository = PurchaseRepository(db)

    purchase = repository.get_by_id(
        purchase_id=purchase_id,
        tenant_id=tenant_id,
    )

    if purchase is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase not found.",
        )

    items = repository.get_items(
        purchase_id=purchase.id,
    )

    return {
        "id": purchase.id,
        "tenant_id": purchase.tenant_id,
        "branch_id": purchase.branch_id,
        "supplier_id": purchase.supplier_id,
        "purchase_number": purchase.purchase_number,
        "purchase_date": purchase.purchase_date,
        "status": getattr(
            purchase.status,
            "value",
            purchase.status,
        ),
        "note": purchase.note,
        "created_at": purchase.created_at,
        "updated_at": purchase.updated_at,
        "items": [
            {
                "id": item.id,
                "purchase_id": item.purchase_id,
                "ingredient_id": item.ingredient_id,
                "quantity": item.quantity,
                "unit": getattr(
                    item.unit,
                    "value",
                    item.unit,
                ),
                "unit_cost": item.unit_cost,
                "total_cost": item.total_cost,
            }
            for item in items
        ],
    }
    

def get_supplier_performance(
    db: Session,
    tenant_id: UUID,
    branch_id: UUID | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[dict]:
    """Return purchasing performance grouped by supplier."""

    repository = PurchaseRepository(db)

    return repository.get_supplier_performance(
        tenant_id=tenant_id,
        branch_id=branch_id,
        start_date=start_date,
        end_date=end_date,
    )
    
    
def get_supplier_price_analysis(
    db: Session,
    tenant_id: UUID,
    branch_id: UUID | None = None,
    supplier_id: UUID | None = None,
    ingredient_id: UUID | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[dict]:
    """Analyze ingredient purchase prices by supplier."""

    repository = PurchaseRepository(db)

    rows = repository.get_supplier_price_analysis(
        tenant_id=tenant_id,
        branch_id=branch_id,
        supplier_id=supplier_id,
        ingredient_id=ingredient_id,
        start_date=start_date,
        end_date=end_date,
    )

    grouped: dict[tuple[UUID, UUID], dict] = {}

    for row in rows:
        unit = row["unit"]
        unit_cost = Decimal(row["unit_cost"])

        # Normalize purchase price to the ingredient base unit.
        if unit == "KILOGRAM" and row["base_unit"] == "GRAM":
            normalized_unit_cost = unit_cost / Decimal("1000")

        elif (
            unit == "LITER"
            and row["base_unit"] == "MILLILITER"
        ):
            normalized_unit_cost = unit_cost / Decimal("1000")

        else:
            normalized_unit_cost = unit_cost

        key = (
            row["supplier_id"],
            row["ingredient_id"],
        )

        if key not in grouped:
            grouped[key] = {
                "supplier_id": row["supplier_id"],
                "supplier_name": row["supplier_name"],
                "ingredient_id": row["ingredient_id"],
                "ingredient_name": row["ingredient_name"],
                "base_unit": row["base_unit"],
                "purchase_count": 0,
                "prices": [],
                "first_purchase_date": row["purchase_date"],
                "latest_purchase_date": row["purchase_date"],
            }

        group = grouped[key]

        group["purchase_count"] += 1
        group["prices"].append(normalized_unit_cost)

        if row["purchase_date"] < group["first_purchase_date"]:
            group["first_purchase_date"] = row["purchase_date"]

        if row["purchase_date"] > group["latest_purchase_date"]:
            group["latest_purchase_date"] = row["purchase_date"]

    result = []

    for group in grouped.values():
        prices = group["prices"]

        first_unit_cost = prices[0]
        latest_unit_cost = prices[-1]

        average_unit_cost = (
            sum(prices, Decimal("0"))
            / Decimal(str(len(prices)))
        )

        minimum_unit_cost = min(prices)
        maximum_unit_cost = max(prices)

        if first_unit_cost > 0:
            price_change_percent = (
                (
                    latest_unit_cost - first_unit_cost
                )
                / first_unit_cost
            ) * Decimal("100")
        else:
            price_change_percent = Decimal("0")

        result.append(
            {
                "supplier_id": group["supplier_id"],
                "supplier_name": group["supplier_name"],
                "ingredient_id": group["ingredient_id"],
                "ingredient_name": group["ingredient_name"],
                "base_unit": group["base_unit"],
                "purchase_count": group["purchase_count"],
                "first_unit_cost": first_unit_cost.quantize(
                    Decimal("0.01")
                ),
                "latest_unit_cost": latest_unit_cost.quantize(
                    Decimal("0.01")
                ),
                "average_unit_cost": average_unit_cost.quantize(
                    Decimal("0.01")
                ),
                "minimum_unit_cost": minimum_unit_cost.quantize(
                    Decimal("0.01")
                ),
                "maximum_unit_cost": maximum_unit_cost.quantize(
                    Decimal("0.01")
                ),
                "price_change_percent": price_change_percent.quantize(
                    Decimal("0.01")
                ),
                "first_purchase_date": group["first_purchase_date"],
                "latest_purchase_date": group["latest_purchase_date"],
            }
        )

    result.sort(
        key=lambda item: (
            item["ingredient_name"],
            item["supplier_name"],
        )
    )

    return result


def get_purchase_cost_by_ingredient(
    db: Session,
    tenant_id: UUID,
    branch_id: UUID | None = None,
    supplier_id: UUID | None = None,
    ingredient_id: UUID | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[dict]:
    """Analyze received purchase costs grouped by ingredient."""

    repository = PurchaseRepository(db)

    rows = repository.get_cost_by_ingredient(
        tenant_id=tenant_id,
        branch_id=branch_id,
        supplier_id=supplier_id,
        ingredient_id=ingredient_id,
        start_date=start_date,
        end_date=end_date,
    )

    grouped: dict[UUID, dict] = {}

    for row in rows:
        quantity = Decimal(row["quantity"])
        unit = row["unit"]
        base_unit = row["base_unit"]

        base_quantity = convert_quantity(
            quantity=quantity,
            from_unit=unit,
            to_unit=base_unit,
        )

        purchase_id = row["purchase_id"]
        total_cost = Decimal(row["total_cost"])

        ingredient_id_value = row["ingredient_id"]

        if ingredient_id_value not in grouped:
            grouped[ingredient_id_value] = {
                "ingredient_id": ingredient_id_value,
                "ingredient_name": row["ingredient_name"],
                "base_unit": base_unit,
                "purchase_ids": set(),
                "total_quantity": Decimal("0"),
                "total_purchase_cost": Decimal("0"),
                "latest_purchase_date": row["purchase_date"],
                "latest_purchase_cost": total_cost,
            }

        group = grouped[ingredient_id_value]

        group["purchase_ids"].add(purchase_id)

        group["total_quantity"] += base_quantity
        group["total_purchase_cost"] += total_cost

        if row["purchase_date"] >= group["latest_purchase_date"]:
            group["latest_purchase_date"] = row["purchase_date"]
            group["latest_purchase_cost"] = total_cost

    result = []

    for group in grouped.values():
        purchase_count = len(group["purchase_ids"])
        total_purchase_cost = group["total_purchase_cost"]

        average_purchase_cost = (
            total_purchase_cost / purchase_count
            if purchase_count > 0
            else Decimal("0")
        )

        result.append(
            {
                "ingredient_id": group["ingredient_id"],
                "ingredient_name": group["ingredient_name"],
                "base_unit": group["base_unit"],
                "purchase_count": purchase_count,
                "total_quantity": group["total_quantity"].quantize(
                    Decimal("0.001")
                ),
                "total_purchase_cost": total_purchase_cost.quantize(
                    Decimal("0.01")
                ),
                "average_purchase_cost": average_purchase_cost.quantize(
                    Decimal("0.01")
                ),
                "latest_purchase_cost": (
                    group["latest_purchase_cost"].quantize(
                        Decimal("0.01")
                    )
                ),
            }
        )

    result.sort(
        key=lambda item: item["total_purchase_cost"],
        reverse=True,
    )

    return result


def receive_purchase(
    db: Session,
    purchase_id: UUID,
    tenant_id: UUID,
    receive_items: list[PurchaseReceiveItem],
) -> None:
    """Receive a purchase, update inventory, and create its expense."""

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

    receive_items_by_id = {
        item.purchase_item_id: item
        for item in receive_items
    }

    purchase_item_ids = {item.id for item in purchase_items}

    if set(receive_items_by_id.keys()) != purchase_item_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Receive data must contain exactly one batch "
                "for each purchase item."
            ),
        )

    total_purchase_cost = Decimal("0")

    try:
        for purchase_item in purchase_items:
            receive_item = receive_items_by_id[purchase_item.id]

            if receive_item.expires_at is not None:
                expires_at = receive_item.expires_at

                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(
                        tzinfo=timezone.utc,
                    )

                now = datetime.now(timezone.utc)

                if expires_at <= now:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Expiry date for batch "
                            f"'{receive_item.batch_number}' "
                            f"must be in the future."
                        ),
                    )

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

            if (
                purchase_item.unit == "KILOGRAM"
                and ingredient.base_unit == "GRAM"
            ):
                base_cost_per_unit = (
                    purchase_item.unit_cost
                    / Decimal("1000")
                )

            elif (
                purchase_item.unit == "LITER"
                and ingredient.base_unit == "MILLILITER"
            ):
                base_cost_per_unit = (
                    purchase_item.unit_cost
                    / Decimal("1000")
                )

            else:
                base_cost_per_unit = purchase_item.unit_cost

            inventory_item.quantity += base_quantity

            batch = InventoryBatch(
                inventory_item_id=inventory_item.id,
                purchase_item_id=purchase_item.id,
                batch_number=receive_item.batch_number,
                quantity=base_quantity,
                cost_per_unit=base_cost_per_unit,
                expires_at=receive_item.expires_at,
            )

            db.add(batch)
            db.flush()

            movement = InventoryMovement(
                inventory_item_id=inventory_item.id,
                inventory_batch_id=batch.id,
                purchase_item_id=purchase_item.id,
                movement_type="PURCHASE",
                quantity=base_quantity,
                note=f"Purchase {purchase.purchase_number}",
            )

            db.add(movement)

            total_purchase_cost += purchase_item.total_cost

        # -----------------------------------------------------
        # Create the financial expense for this purchase
        # -----------------------------------------------------
        expense = Expense(
            tenant_id=tenant_id,
            branch_id=purchase.branch_id,
            purchase_id=purchase.id,
            category=ExpenseCategory.PURCHASE,
            amount=total_purchase_cost,
            expense_date=purchase.purchase_date,
            description=(
                f"Purchase {purchase.purchase_number}"
            ),
        )

        db.add(expense)

        # -----------------------------------------------------
        # Mark purchase as received
        # -----------------------------------------------------
        purchase.status = "RECEIVED"

        db.commit()

    except HTTPException:
        db.rollback()
        raise

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