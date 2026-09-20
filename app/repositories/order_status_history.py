from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.order_status_history import OrderStatusHistory


class OrderStatusHistoryRepository:
    """
    Handles database access for order status history records.
    """

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        order_id: UUID,
        from_status: str | None,
        to_status: str,
        note: str | None = None,
    ) -> OrderStatusHistory:
        history = OrderStatusHistory(
            order_id=order_id,
            from_status=from_status,
            to_status=to_status,
            note=note,
        )

        self.db.add(history)

        return history

    def get_by_order_id(
        self,
        order_id: UUID,
    ) -> list[OrderStatusHistory]:
        statement = (
            select(OrderStatusHistory)
            .where(
                OrderStatusHistory.order_id == order_id,
            )
            .order_by(
                OrderStatusHistory.changed_at.asc(),
                OrderStatusHistory.id.asc(),
            )
        )

        return list(self.db.scalars(statement).all())