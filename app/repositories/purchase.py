from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models.purchase import Purchase
from app.database.models.purchase_item import PurchaseItem


class PurchaseRepository:
    """Provide database access operations for purchases."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(
        self,
        purchase_id: UUID,
        tenant_id: UUID,
    ) -> Purchase | None:
        """Return a tenant-owned purchase by ID."""

        statement = select(Purchase).where(
            Purchase.id == purchase_id,
            Purchase.tenant_id == tenant_id,
        )

        return self.db.scalar(statement)

    def get_items(
        self,
        purchase_id: UUID,
    ) -> list[PurchaseItem]:
        """Return all items belonging to a purchase."""

        statement = (
            select(PurchaseItem)
            .where(PurchaseItem.purchase_id == purchase_id)
            .order_by(PurchaseItem.id)
        )

        return list(self.db.scalars(statement).all())

    def list_purchases(
        self,
        tenant_id: UUID,
        branch_id: UUID | None = None,
        supplier_id: UUID | None = None,
        status: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> tuple[list[Purchase], int]:
        """Return filtered purchases and the total matching count."""

        filters = [
            Purchase.tenant_id == tenant_id,
        ]

        if branch_id is not None:
            filters.append(
                Purchase.branch_id == branch_id,
            )

        if supplier_id is not None:
            filters.append(
                Purchase.supplier_id == supplier_id,
            )

        if status is not None:
            filters.append(
                Purchase.status == status,
            )

        if start_date is not None:
            filters.append(
                Purchase.purchase_date >= start_date,
            )

        if end_date is not None:
            filters.append(
                Purchase.purchase_date <= end_date,
            )

        items_statement = (
            select(Purchase)
            .where(*filters)
            .order_by(
                Purchase.purchase_date.desc(),
                Purchase.created_at.desc(),
            )
        )

        purchases = list(
            self.db.scalars(items_statement).all()
        )

        count_statement = (
            select(func.count(Purchase.id))
            .where(*filters)
        )

        total_count = self.db.scalar(count_statement) or 0

        return purchases, total_count
    
    def get_summary(
        self,
        tenant_id: UUID,
        branch_id: UUID | None = None,
        supplier_id: UUID | None = None,
        status: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict:
        """Return aggregated purchase statistics."""

        filters = [
            Purchase.tenant_id == tenant_id,
        ]

        if branch_id is not None:
            filters.append(
                Purchase.branch_id == branch_id,
            )

        if supplier_id is not None:
            filters.append(
                Purchase.supplier_id == supplier_id,
            )

        if status is not None:
            filters.append(
                Purchase.status == status,
            )

        if start_date is not None:
            filters.append(
                Purchase.purchase_date >= start_date,
            )

        if end_date is not None:
            filters.append(
                Purchase.purchase_date <= end_date,
            )

        summary_statement = (
            select(
                func.count(func.distinct(Purchase.id)),
                func.coalesce(
                    func.sum(PurchaseItem.total_cost),
                    0,
                ),
            )
            .select_from(Purchase)
            .outerjoin(
                PurchaseItem,
                PurchaseItem.purchase_id == Purchase.id,
            )
            .where(*filters)
        )

        total_purchase_count, total_purchase_cost = (
            self.db.execute(summary_statement).one()
        )

        status_statement = (
            select(
                Purchase.status,
                func.count(Purchase.id),
            )
            .where(*filters)
            .group_by(Purchase.status)
        )

        status_rows = self.db.execute(status_statement).all()

        draft_purchase_count = 0
        received_purchase_count = 0
        cancelled_purchase_count = 0

        for purchase_status, count in status_rows:
            status_value = getattr(
                purchase_status,
                "value",
                purchase_status,
            )

            if status_value == "DRAFT":
                draft_purchase_count = count

            elif status_value == "RECEIVED":
                received_purchase_count = count

            elif status_value == "CANCELLED":
                cancelled_purchase_count = count

        return {
            "total_purchase_count": total_purchase_count,
            "total_purchase_cost": total_purchase_cost,
            "draft_purchase_count": draft_purchase_count,
            "received_purchase_count": received_purchase_count,
            "cancelled_purchase_count": cancelled_purchase_count,
        }