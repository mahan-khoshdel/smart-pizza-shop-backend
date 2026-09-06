from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.role import Role
from app.services.role import add_permission_to_role


DEFAULT_ROLES = {
    "Owner": [
        "orders.read",
        "orders.create",
        "orders.update",
        "orders.cancel",
        "inventory.read",
        "inventory.update",
        "products.read",
        "products.create",
        "products.update",
        "users.read",
        "users.manage",
        "reports.read",
    ],
    "Manager": [
        "orders.read",
        "orders.create",
        "orders.update",
        "inventory.read",
        "inventory.update",
        "products.read",
        "products.update",
        "users.read",
        "reports.read",
    ],
    "Cashier": [
        "orders.read",
        "orders.create",
        "orders.update",
    ],
    "Kitchen": [
        "orders.read",
        "orders.update",
    ],
    "Inventory Manager": [
        "inventory.read",
        "inventory.update",
        "products.read",
    ],
}


def seed_default_roles(
    db: Session,
    tenant_id,
) -> None:
    """Create default roles for a tenant."""

    for role_name, permission_codes in DEFAULT_ROLES.items():
        role = db.scalar(
            select(Role).where(
                Role.tenant_id == tenant_id,
                Role.name == role_name,
            )
        )

        if role is None:
            role = Role(
                tenant_id=tenant_id,
                name=role_name,
            )
            db.add(role)
            db.flush()

        for permission_code in permission_codes:
            add_permission_to_role(
                db=db,
                role_id=role.id,
                permission_code=permission_code,
            )

    db.commit()