from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.permission import Permission


PERMISSIONS = [
    {
        "code": "orders.read",
        "name": "Read orders",
        "description": "View orders.",
    },
    {
        "code": "orders.create",
        "name": "Create orders",
        "description": "Create new orders.",
    },
    {
        "code": "orders.update",
        "name": "Update orders",
        "description": "Update existing orders.",
    },
    {
        "code": "orders.cancel",
        "name": "Cancel orders",
        "description": "Cancel orders.",
    },
    {
        "code": "inventory.read",
        "name": "Read inventory",
        "description": "View inventory information.",
    },
    {
        "code": "inventory.update",
        "name": "Update inventory",
        "description": "Update inventory information.",
    },
    {
        "code": "products.read",
        "name": "Read products",
        "description": "View products.",
    },
    {
        "code": "products.create",
        "name": "Create products",
        "description": "Create products.",
    },
    {
        "code": "products.update",
        "name": "Update products",
        "description": "Update products.",
    },
    {
        "code": "users.read",
        "name": "Read users",
        "description": "View users.",
    },
    {
        "code": "users.manage",
        "name": "Manage users",
        "description": "Create, update and deactivate users.",
    },
    {
        "code": "reports.read",
        "name": "Read reports",
        "description": "View business reports.",
    },
]


def seed_permissions(db: Session) -> None:
    """Create missing system permissions."""
    for permission_data in PERMISSIONS:
        existing_permission = db.scalar(
            select(Permission).where(
                Permission.code == permission_data["code"]
            )
        )

        if existing_permission is None:
            db.add(Permission(**permission_data))

    db.commit()