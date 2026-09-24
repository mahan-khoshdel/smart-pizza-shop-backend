from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models.order import Order, OrderItem


class OrderRepository:
    """
    Handles database access for orders.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(
        self,
        order_id: UUID,
        tenant_id: UUID,
    ) -> Order | None:
        statement = select(Order).where(
            Order.id == order_id,
            Order.tenant_id == tenant_id,
        )

        return self.db.scalar(statement)

    def get_items(
        self,
        order_id: UUID,
    ) -> list[OrderItem]:
        statement = (
            select(OrderItem)
            .where(OrderItem.order_id == order_id)
            .order_by(OrderItem.created_at.asc())
        )

        return list(self.db.scalars(statement).all())

    def get_by_order_number(
        self,
        order_number: str,
        tenant_id: UUID,
    ) -> Order | None:
        statement = select(Order).where(
            Order.order_number == order_number,
            Order.tenant_id == tenant_id,
        )

        return self.db.scalar(statement)

    def get_all(
        self,
        tenant_id: UUID,
        status: str | None = None,
    ) -> list[Order]:
        statement = select(Order).where(
            Order.tenant_id == tenant_id,
        )

        if status is not None:
            statement = statement.where(
                Order.status == status,
            )

        statement = statement.order_by(
            Order.created_at.desc(),
        )

        return list(self.db.scalars(statement).all())
 
    def get_kitchen_orders(
        self,
        tenant_id: UUID,
        branch_id: UUID,
    ) -> list[Order]:
        statement = (
            select(Order)
            .where(
                Order.tenant_id == tenant_id,
                Order.branch_id == branch_id,
                Order.status.in_(
                    (
                        "PREPARING",
                        "READY",
                    )
                ),
            )
            .order_by(
                Order.created_at.asc(),
            )
        )

        return list(self.db.scalars(statement).all())
    
    def get_kitchen_workload(
        self,
        tenant_id: UUID,
        branch_id: UUID,
    ) -> dict[str, int]:
        statement = select(
            Order.status,
        ).where(
            Order.tenant_id == tenant_id,
            Order.branch_id == branch_id,
            Order.status.in_(
                (
                    "PREPARING",
                    "READY",
                )
            ),
        )

        statuses = list(self.db.scalars(statement).all())

        preparing_count = sum(
            1
            for order_status in statuses
            if getattr(order_status, "value", order_status) == "PREPARING"
        )

        ready_count = sum(
            1
            for order_status in statuses
            if getattr(order_status, "value", order_status) == "READY"
        )

        return {
            "preparing_count": preparing_count,
            "ready_count": ready_count,
            "active_count": len(statuses),
        }
        
    def get_kitchen_queue(
        self,
        tenant_id: UUID,
        branch_id: UUID,
    ) -> list[tuple[Order, int]]:
        queue_position = func.row_number().over(
            order_by=(
                Order.created_at.asc(),
                Order.id.asc(),
            )
        ).label("queue_position")

        statement = (
            select(
                Order,
                queue_position,
            )
            .where(
                Order.tenant_id == tenant_id,
                Order.branch_id == branch_id,
                Order.status == "PREPARING",
            )
            .order_by(
                Order.created_at.asc(),
                Order.id.asc(),
            )
        )

        rows = self.db.execute(statement).all()

        return [
            (order, int(queue_position))
            for order, queue_position in rows
        ]