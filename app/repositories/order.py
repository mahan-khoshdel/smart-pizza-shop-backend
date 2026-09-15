from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.order import Order


class OrderRepository:
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
    ) -> list[Order]:
        statement = (
            select(Order)
            .where(Order.tenant_id == tenant_id)
            .order_by(Order.created_at.desc())
        )

        return list(self.db.scalars(statement).all())