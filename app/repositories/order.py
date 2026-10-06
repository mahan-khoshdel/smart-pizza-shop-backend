from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.database.models.order import Order, OrderItem
from app.database.models.product_variant import ProductVariant


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
        customer_id: UUID | None = None,
        branch_id: UUID | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Order]:
        statement = select(Order).where(
            Order.tenant_id == tenant_id
        )

        if status is not None:
            statement = statement.where(
                Order.status == status
            )

        if customer_id is not None:
            statement = statement.where(
                Order.customer_id == customer_id
            )

        if branch_id is not None:
            statement = statement.where(
                Order.branch_id == branch_id
            )

        statement = statement.order_by(
            Order.created_at.desc(),
            Order.id.desc(),
        )

        if offset > 0:
            statement = statement.offset(offset)

        if limit is not None:
            statement = statement.limit(limit)

        return list(
            self.db.scalars(statement).all()
        )
 
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
        
    def get_kitchen_preparation_durations(
        self,
        tenant_id: UUID,
        branch_id: UUID,
    ) -> list[float]:
        statement = (
            select(
                Order.preparing_at,
                Order.ready_at,
            )
            .where(
                Order.tenant_id == tenant_id,
                Order.branch_id == branch_id,
                Order.preparing_at.is_not(None),
                Order.ready_at.is_not(None),
            )
        )

        rows = self.db.execute(statement).all()

        durations = []

        for preparing_at, ready_at in rows:
            duration = (
                ready_at - preparing_at
            ).total_seconds()

            durations.append(duration)

        return durations
    
    def get_kitchen_waiting_orders(
        self,
        tenant_id: UUID,
        branch_id: UUID,
    ) -> list[Order]:
        statement = (
            select(Order)
            .where(
                Order.tenant_id == tenant_id,
                Order.branch_id == branch_id,
                Order.status == "REGISTERED",
            )
            .order_by(
                Order.created_at.asc(),
                Order.id.asc(),
            )
        )

        return list(self.db.scalars(statement).all())
    
    def get_waiting_orders_for_promotion(
        self,
        tenant_id: UUID,
        branch_id: UUID,
        limit: int,
    ) -> list[Order]:
        """
        Return the oldest registered orders waiting for kitchen capacity.
        """

        if limit <= 0:
            return []

        statement = (
            select(Order)
            .where(
                Order.tenant_id == tenant_id,
                Order.branch_id == branch_id,
                Order.status == "REGISTERED",
            )
            .order_by(
                Order.created_at.asc(),
                Order.id.asc(),
            )
            .limit(limit)
            .with_for_update(
                skip_locked=True,
            )
        )

        return list(self.db.scalars(statement).all())
    
    def get_kitchen_preparation_durations_in_range(
        self,
        tenant_id: UUID,
        branch_id: UUID,
        start_at=None,
        end_at=None,
    ) -> list[float]:
        """
        Return kitchen preparation durations optionally limited
        by the order ready timestamp.
        """

        statement = (
            select(
                Order.preparing_at,
                Order.ready_at,
            )
            .where(
                Order.tenant_id == tenant_id,
                Order.branch_id == branch_id,
                Order.preparing_at.is_not(None),
                Order.ready_at.is_not(None),
            )
        )

        if start_at is not None:
            statement = statement.where(
                Order.ready_at >= start_at,
            )

        if end_at is not None:
            statement = statement.where(
                Order.ready_at <= end_at,
            )

        rows = self.db.execute(statement).all()

        durations = []

        for preparing_at, ready_at in rows:
            duration = (
                ready_at - preparing_at
            ).total_seconds()

            if duration >= 0:
                durations.append(duration)

        return durations
    
    def get_sales_summary(
        self,
        tenant_id: UUID,
        branch_id: UUID | None = None,
        start_date=None,
        end_date=None,
    ) -> dict:
        """
        Return sales summary for the current tenant.

        Total sales and average order value are calculated only
        from completed orders.
        """

        statement = select(
            func.count(Order.id).label("total_order_count"),
            func.count(Order.id)
            .filter(Order.status == "COMPLETED")
            .label("completed_order_count"),
            func.count(Order.id)
            .filter(Order.status == "CANCELLED")
            .label("cancelled_order_count"),
            func.coalesce(
                func.sum(Order.total)
                .filter(Order.status == "COMPLETED"),
                0,
            ).label("total_sales"),
            func.coalesce(
                func.avg(Order.total)
                .filter(Order.status == "COMPLETED"),
                0,
            ).label("average_order_value"),
        ).where(
            Order.tenant_id == tenant_id,
        )

        if branch_id is not None:
            statement = statement.where(
                Order.branch_id == branch_id,
            )

        if start_date is not None:
            statement = statement.where(
                Order.created_at >= start_date,
            )

        if end_date is not None:
            statement = statement.where(
                Order.created_at <= end_date,
            )

        result = self.db.execute(statement).one()

        return {
            "total_order_count": int(
                result.total_order_count or 0
            ),
            "completed_order_count": int(
                result.completed_order_count or 0
            ),
            "cancelled_order_count": int(
                result.cancelled_order_count or 0
            ),
            "total_sales": result.total_sales or 0,
            "average_order_value": result.average_order_value or 0,
        }
        
    def get_sales_trends(
        self,
        tenant_id: UUID,
        branch_id: UUID | None = None,
        start_date=None,
        end_date=None,
    ) -> list[dict]:
        """
        Return daily sales trends for the current tenant.

        Only completed orders are included in sales calculations.
        """

        trend_date = func.date(Order.created_at).label("date")

        statement = (
            select(
                trend_date,
                func.count(Order.id).label(
                    "completed_order_count"
                ),
                func.coalesce(
                    func.sum(Order.total),
                    0,
                ).label("total_sales"),
                func.coalesce(
                    func.avg(Order.total),
                    0,
                ).label("average_order_value"),
            )
            .where(
                Order.tenant_id == tenant_id,
                Order.status == "COMPLETED",
            )
            .group_by(trend_date)
            .order_by(trend_date.asc())
        )

        if branch_id is not None:
            statement = statement.where(
                Order.branch_id == branch_id,
            )

        if start_date is not None:
            statement = statement.where(
                Order.created_at >= start_date,
            )

        if end_date is not None:
            statement = statement.where(
                Order.created_at <= end_date,
            )

        rows = self.db.execute(statement).all()

        return [
            {
                "date": row.date,
                "completed_order_count": int(
                    row.completed_order_count or 0
                ),
                "total_sales": row.total_sales or 0,
                "average_order_value": (
                    row.average_order_value or 0
                ),
            }
            for row in rows
        ]
        
    def get_product_sales_performance(
        self,
        tenant_id: UUID,
        branch_id: UUID | None = None,
        start_date=None,
        end_date=None,
    ) -> list[dict]:
        """
        Return sales performance for each product variant.

        Only completed orders are included in the analysis.
        """

        statement = (
            select(
                ProductVariant.id.label("product_variant_id"),
                ProductVariant.sku.label("sku"),
                func.coalesce(
                    func.sum(OrderItem.quantity),
                    0,
                ).label("sold_quantity"),
                func.count(
                    func.distinct(Order.id)
                ).label("order_count"),
                func.coalesce(
                    func.sum(OrderItem.total_price),
                    0,
                ).label("total_sales"),
            )
            .join(
                ProductVariant,
                ProductVariant.id == OrderItem.product_variant_id,
            )
            .join(
                Order,
                Order.id == OrderItem.order_id,
            )
            .where(
                Order.tenant_id == tenant_id,
                Order.status == "COMPLETED",
                ProductVariant.tenant_id == tenant_id,
            )
            .group_by(
                ProductVariant.id,
                ProductVariant.sku,
            )
            .order_by(
                func.sum(OrderItem.total_price).desc(),
                ProductVariant.id.asc(),
            )
        )

        if branch_id is not None:
            statement = statement.where(
                Order.branch_id == branch_id,
            )

        if start_date is not None:
            statement = statement.where(
                Order.created_at >= start_date,
            )

        if end_date is not None:
            statement = statement.where(
                Order.created_at <= end_date,
            )

        rows = self.db.execute(statement).all()

        return [
            {
                "product_variant_id": row.product_variant_id,
                "sku": row.sku,
                "sold_quantity": int(
                    row.sold_quantity or 0
                ),
                "order_count": int(
                    row.order_count or 0
                ),
                "total_sales": row.total_sales or 0,
            }
            for row in rows
        ]
        
    def get_customer_sales_performance(
        self,
        tenant_id: UUID,
        branch_id: UUID | None = None,
        start_date=None,
        end_date=None,
    ) -> list[dict]:
        """
        Return sales performance for each customer.

        Only completed orders with a customer are included.
        """

        statement = (
            select(
                Order.customer_id.label("customer_id"),
                func.count(Order.id).label("order_count"),
                func.coalesce(
                    func.sum(Order.total),
                    0,
                ).label("total_sales"),
                func.coalesce(
                    func.avg(Order.total),
                    0,
                ).label("average_order_value"),
            )
            .where(
                Order.tenant_id == tenant_id,
                Order.status == "COMPLETED",
                Order.customer_id.is_not(None),
            )
            .group_by(
                Order.customer_id,
            )
            .order_by(
                func.sum(Order.total).desc(),
                Order.customer_id.asc(),
            )
        )

        if branch_id is not None:
            statement = statement.where(
                Order.branch_id == branch_id,
            )

        if start_date is not None:
            statement = statement.where(
                Order.created_at >= start_date,
            )

        if end_date is not None:
            statement = statement.where(
                Order.created_at <= end_date,
            )

        rows = self.db.execute(statement).all()

        return [
            {
                "customer_id": row.customer_id,
                "order_count": int(
                    row.order_count or 0
                ),
                "total_sales": row.total_sales or 0,
                "average_order_value": (
                    row.average_order_value or 0
                ),
            }
            for row in rows
        ]
           
    def get_order_type_performance(
        self,
        tenant_id: UUID,
        branch_id: UUID | None = None,
        start_date=None,
        end_date=None,
    ) -> list[dict]:
        """
        Return sales performance grouped by order type.

        Only completed orders are included.
        """

        statement = (
            select(
                Order.order_type.label("order_type"),
                func.count(Order.id).label("order_count"),
                func.coalesce(
                    func.sum(Order.total),
                    0,
                ).label("total_sales"),
                func.coalesce(
                    func.avg(Order.total),
                    0,
                ).label("average_order_value"),
            )
            .where(
                Order.tenant_id == tenant_id,
                Order.status == "COMPLETED",
            )
            .group_by(
                Order.order_type,
            )
            .order_by(
                func.sum(Order.total).desc(),
                Order.order_type.asc(),
            )
        )

        if branch_id is not None:
            statement = statement.where(
                Order.branch_id == branch_id,
            )

        if start_date is not None:
            statement = statement.where(
                Order.created_at >= start_date,
            )

        if end_date is not None:
            statement = statement.where(
                Order.created_at <= end_date,
            )

        rows = self.db.execute(statement).all()

        return [
            {
                "order_type": row.order_type,
                "order_count": int(
                    row.order_count or 0
                ),
                "total_sales": row.total_sales or 0,
                "average_order_value": (
                    row.average_order_value or 0
                ),
            }
            for row in rows
        ]
        
    def get_sales_by_hour(
        self,
        tenant_id: UUID,
        branch_id: UUID | None = None,
        start_date=None,
        end_date=None,
    ) -> list[dict]:
        """
        Return completed sales grouped by order creation hour.

        Only completed orders are included.
        """

        hour_expression = func.extract(
            "hour",
            Order.created_at,
        ).label("hour")

        statement = (
            select(
                hour_expression,
                func.count(Order.id).label(
                    "completed_order_count"
                ),
                func.coalesce(
                    func.sum(Order.total),
                    0,
                ).label("total_sales"),
                func.coalesce(
                    func.avg(Order.total),
                    0,
                ).label("average_order_value"),
            )
            .where(
                Order.tenant_id == tenant_id,
                Order.status == "COMPLETED",
            )
            .group_by(
                hour_expression,
            )
            .order_by(
                hour_expression.asc(),
            )
        )

        if branch_id is not None:
            statement = statement.where(
                Order.branch_id == branch_id,
            )

        if start_date is not None:
            statement = statement.where(
                Order.created_at >= start_date,
            )

        if end_date is not None:
            statement = statement.where(
                Order.created_at <= end_date,
            )

        rows = self.db.execute(statement).all()

        return [
            {
                "hour": int(row.hour or 0),
                "completed_order_count": int(
                    row.completed_order_count or 0
                ),
                "total_sales": row.total_sales or 0,
                "average_order_value": (
                    row.average_order_value or 0
                ),
            }
            for row in rows
        ]
        
    def get_sales_by_weekday(
        self,
        tenant_id: UUID,
        branch_id: UUID | None = None,
        start_date=None,
        end_date=None,
    ) -> list[dict]:
        """
        Return completed sales grouped by weekday.

        Weekday values follow PostgreSQL DOW:
        0 = Sunday, 1 = Monday, ..., 6 = Saturday.

        Only completed orders are included.
        """

        weekday_expression = func.extract(
            "dow",
            Order.created_at,
        ).label("weekday")

        statement = (
            select(
                weekday_expression,
                func.count(Order.id).label(
                    "completed_order_count"
                ),
                func.coalesce(
                    func.sum(Order.total),
                    0,
                ).label("total_sales"),
                func.coalesce(
                    func.avg(Order.total),
                    0,
                ).label("average_order_value"),
            )
            .where(
                Order.tenant_id == tenant_id,
                Order.status == "COMPLETED",
            )
            .group_by(
                weekday_expression,
            )
            .order_by(
                weekday_expression.asc(),
            )
        )

        if branch_id is not None:
            statement = statement.where(
                Order.branch_id == branch_id,
            )

        if start_date is not None:
            statement = statement.where(
                Order.created_at >= start_date,
            )

        if end_date is not None:
            statement = statement.where(
                Order.created_at <= end_date,
            )

        rows = self.db.execute(statement).all()

        return [
            {
                "weekday": int(row.weekday or 0),
                "completed_order_count": int(
                    row.completed_order_count or 0
                ),
                "total_sales": row.total_sales or 0,
                "average_order_value": (
                    row.average_order_value or 0
                ),
            }
            for row in rows
        ]
        
    def get_sales_by_weekday_hour(
        self,
        tenant_id: UUID,
        branch_id: UUID | None = None,
        start_date=None,
        end_date=None,
    ) -> list[dict]:
        """
        Return completed sales grouped by weekday and hour.

        Weekday values follow PostgreSQL DOW:
        0 = Sunday, 1 = Monday, ..., 6 = Saturday.

        Only completed orders are included.
        """

        weekday_expression = func.extract(
            "dow",
            Order.created_at,
        ).label("weekday")

        hour_expression = func.extract(
            "hour",
            Order.created_at,
        ).label("hour")

        statement = (
            select(
                weekday_expression,
                hour_expression,
                func.count(Order.id).label(
                    "completed_order_count"
                ),
                func.coalesce(
                    func.sum(Order.total),
                    0,
                ).label("total_sales"),
                func.coalesce(
                    func.avg(Order.total),
                    0,
                ).label("average_order_value"),
            )
            .where(
                Order.tenant_id == tenant_id,
                Order.status == "COMPLETED",
            )
            .group_by(
                weekday_expression,
                hour_expression,
            )
            .order_by(
                weekday_expression.asc(),
                hour_expression.asc(),
            )
        )

        if branch_id is not None:
            statement = statement.where(
                Order.branch_id == branch_id,
            )

        if start_date is not None:
            statement = statement.where(
                Order.created_at >= start_date,
            )

        if end_date is not None:
            statement = statement.where(
                Order.created_at <= end_date,
            )

        rows = self.db.execute(statement).all()

        return [
            {
                "weekday": int(row.weekday or 0),
                "hour": int(row.hour or 0),
                "completed_order_count": int(
                    row.completed_order_count or 0
                ),
                "total_sales": row.total_sales or 0,
                "average_order_value": (
                    row.average_order_value or 0
                ),
            }
            for row in rows
        ]
        
    def get_daily_business_summary(
        self,
        tenant_id: UUID,
        start_at,
        end_at,
        branch_id: UUID | None = None,
    ) -> dict:
        """
        Return the main business KPIs for a specific day.

        Orders are filtered by creation timestamp.

        The summary includes:
        - total order count
        - completed order count
        - cancelled order count
        - total sales from completed orders
        - average order value from completed orders
        """

        completed_total = case(
            (
                Order.status == "COMPLETED",
                Order.total,
            ),
            else_=0,
        )

        completed_count = case(
            (
                Order.status == "COMPLETED",
                1,
            ),
            else_=0,
        )

        cancelled_count = case(
            (
                Order.status == "CANCELLED",
                1,
            ),
            else_=0,
        )

        statement = select(
            func.count(Order.id).label(
                "total_order_count"
            ),
            func.coalesce(
                func.sum(completed_count),
                0,
            ).label(
                "completed_order_count"
            ),
            func.coalesce(
                func.sum(cancelled_count),
                0,
            ).label(
                "cancelled_order_count"
            ),
            func.coalesce(
                func.sum(completed_total),
                0,
            ).label(
                "total_sales"
            ),
            func.coalesce(
                func.avg(
                    case(
                        (
                            Order.status == "COMPLETED",
                            Order.total,
                        ),
                        else_=None,
                    )
                ),
                0,
            ).label(
                "average_order_value"
            ),
        ).where(
            Order.tenant_id == tenant_id,
            Order.created_at >= start_at,
            Order.created_at < end_at,
        )

        if branch_id is not None:
            statement = statement.where(
                Order.branch_id == branch_id,
            )

        row = self.db.execute(statement).one()

        return {
            "total_order_count": int(
                row.total_order_count or 0
            ),
            "completed_order_count": int(
                row.completed_order_count or 0
            ),
            "cancelled_order_count": int(
                row.cancelled_order_count or 0
            ),
            "total_sales": row.total_sales or 0,
            "average_order_value": (
                row.average_order_value or 0
            ),
        }
           
    def get_business_risk_metrics(
        self,
        tenant_id: UUID,
        start_at,
        end_at,
        branch_id: UUID | None = None,
    ) -> dict:
        """
        Return operational risk metrics for a specific time range.

        Order metrics are calculated from orders created in the
        requested period.
        """

        cancelled_count = func.count(Order.id).filter(
            Order.status == "CANCELLED"
        )

        completed_count = func.count(Order.id).filter(
            Order.status == "COMPLETED"
        )

        open_count = func.count(Order.id).filter(
            ~Order.status.in_(
                {
                    "COMPLETED",
                    "CANCELLED",
                }
            )
        )

        statement = select(
            func.count(Order.id).label(
                "total_order_count"
            ),
            completed_count.label(
                "completed_order_count"
            ),
            cancelled_count.label(
                "cancelled_order_count"
            ),
            open_count.label(
                "open_order_count"
            ),
        ).where(
            Order.tenant_id == tenant_id,
            Order.created_at >= start_at,
            Order.created_at < end_at,
        )

        if branch_id is not None:
            statement = statement.where(
                Order.branch_id == branch_id,
            )

        row = self.db.execute(statement).one()

        return {
            "total_order_count": int(
                row.total_order_count or 0
            ),
            "completed_order_count": int(
                row.completed_order_count or 0
            ),
            "cancelled_order_count": int(
                row.cancelled_order_count or 0
            ),
            "open_order_count": int(
                row.open_order_count or 0
            ),
        }