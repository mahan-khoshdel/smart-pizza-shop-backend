from sqlalchemy import select

from app.database.connection import SessionLocal
from app.database.models.branch import Branch
from app.database.models.ingredient import Ingredient
from app.database.models.supplier import Supplier
from app.database.models.tenant import Tenant


db = SessionLocal()

try:
    tenant = db.scalar(
        select(Tenant).where(Tenant.slug == "test")
    )

    if tenant is None:
        raise ValueError("Test tenant does not exist.")

    branch = db.scalar(
        select(Branch).where(
            Branch.tenant_id == tenant.id,
            Branch.code == "MAIN",
        )
    )

    if branch is None:
        branch = Branch(
            tenant_id=tenant.id,
            name="Main Branch",
            code="MAIN",
        )
        db.add(branch)

    supplier = db.scalar(
        select(Supplier).where(
            Supplier.tenant_id == tenant.id,
            Supplier.name == "Test Supplier",
        )
    )

    if supplier is None:
        supplier = Supplier(
            tenant_id=tenant.id,
            name="Test Supplier",
        )
        db.add(supplier)

    ingredient = db.scalar(
        select(Ingredient).where(
            Ingredient.tenant_id == tenant.id,
            Ingredient.name == "Cheese",
        )
    )

    if ingredient is None:
        ingredient = Ingredient(
            tenant_id=tenant.id,
            name="Cheese",
            base_unit="GRAM",
        )
        db.add(ingredient)

    db.commit()

    print("Purchase test data is ready.")

finally:
    db.close()