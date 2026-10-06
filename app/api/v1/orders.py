from uuid import UUID

from datetime import date, datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_data
from app.database.connection import get_db
from app.database.models.order import OrderStatus
from app.schemas.kitchen import KitchenPerformanceSummaryResponse
from app.schemas.kitchen import KitchenQueueResponse
from app.schemas.kitchen import KitchenWaitingQueueResponse
from app.schemas.kitchen import (
    KitchenPerformancePeriod,
    KitchenPerformanceSummaryResponse,
)
from app.schemas.order import (
    BusinessDashboardSummaryResponse,
    BusinessRiskMetricsResponse,
    BusyHoursAnalysisResponse,
    DailyBusinessSummaryResponse,
    KitchenPerformanceResponse,
    KitchenWorkloadResponse,
    OrderCreate,
    OrderCustomerSalesPerformanceResponse,
    OrderIngredientRequirementsResponse,
    OrderPaginationResponse,
    OrderProductSalesPerformanceResponse,
    OrderResponse,
    OrderSalesSummaryResponse,
    OrderSalesTrendResponse,
    OrderStatusHistoryResponse,
    OrderStatusUpdate,
    OrderTypePerformanceResponse,
    SalesByHourResponse,
    SalesByWeekdayResponse,
    SalesByWeekdayHourResponse,
)
from app.services.order import (
    cancel_order,
    consume_order_inventory,
    create_order,
    get_business_dashboard_summary,
    get_business_risk_metrics,
    get_busy_hours,
    get_customer_sales_performance,
    get_daily_business_summary,
    get_kitchen_orders,
    get_kitchen_performance,
    get_kitchen_performance_summary,
    get_kitchen_queue,
    get_kitchen_waiting_queue,
    get_kitchen_workload,
    get_order,
    get_orders,
    get_orders_page,
    get_order_ingredient_requirements,
    get_order_sales_summary,
    get_order_sales_trends,
    get_order_status_history,
    get_order_type_performance,
    get_product_sales_performance,
    get_sales_by_hour,
    get_sales_by_weekday,
    get_sales_by_weekday_hour,
    update_order_status,
)


router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
)


@router.post(
    "",
    response_model=OrderResponse,
    status_code=201,
)
def create_order_endpoint(
    order_data: OrderCreate,
    current_user=Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Create a new order for the current tenant.
    """

    return create_order(
        db=db,
        tenant_id=current_user["tenant_id"],
        data=order_data,
    )


@router.get(
    "",
    response_model=OrderPaginationResponse,
    summary="List orders",
)
def get_orders_endpoint(
    status: OrderStatus | None = Query(
        default=None,
        description="Filter orders by status.",
    ),
    customer_id: UUID | None = Query(
        default=None,
        description="Filter orders by customer.",
    ),
    branch_id: UUID | None = Query(
        default=None,
        description="Filter orders by branch.",
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Number of orders to return. Maximum is 100.",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of matching orders to skip.",
    ),
    current_user_data: dict = Depends(
        get_current_user_data
    ),
    db: Session = Depends(get_db),
):
    """
    Return a paginated list of orders for the current tenant.

    Orders can be filtered by status, customer, or branch.
    Pagination is controlled using limit and offset.
    """

    return get_orders_page(
        db=db,
        tenant_id=current_user_data["tenant_id"],
        status=status,
        customer_id=customer_id,
        branch_id=branch_id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{order_id}/ingredient-requirements",
    response_model=OrderIngredientRequirementsResponse,
)
def get_order_ingredient_requirements_endpoint(
    order_id: UUID,
    current_user=Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Calculate ingredient requirements for an order from its recipes.
    """

    return get_order_ingredient_requirements(
        db=db,
        tenant_id=current_user["tenant_id"],
        order_id=order_id,
    )

    
@router.get(
    "/{order_id}/status-history",
    response_model=list[OrderStatusHistoryResponse],
)
def get_order_status_history_endpoint(
    order_id: UUID,
    current_user_data: dict = Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Return the complete status history of an order.
    """
    return get_order_status_history(
        db=db,
        order_id=order_id,
        tenant_id=current_user_data["tenant_id"],
    )


@router.patch(
    "/{order_id}/status",
    response_model=OrderResponse,
)
def update_order_status_endpoint(
    order_id: UUID,
    status_data: OrderStatusUpdate,
    current_user=Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Update an order status according to the allowed order workflow.
    """

    return update_order_status(
        db=db,
        tenant_id=current_user["tenant_id"],
        order_id=order_id,
        new_status=status_data.status,
    )


@router.post(
    "/{order_id}/cancel",
    response_model=OrderResponse,
)
def cancel_order_endpoint(
    order_id: UUID,
    current_user=Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Cancel an order when its current status allows cancellation.
    """

    return cancel_order(
        db=db,
        tenant_id=current_user["tenant_id"],
        order_id=order_id,
    )

    
@router.post(
    "/{order_id}/consume-inventory",
    response_model=OrderResponse,
)
def consume_order_inventory_endpoint(
    order_id: UUID,
    current_user=Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Consume inventory required by a completed order using FEFO.
    """

    return consume_order_inventory(
        db=db,
        tenant_id=current_user["tenant_id"],
        order_id=order_id,
    )

    
@router.get(
    "/kitchen",
    response_model=list[OrderResponse],
)
def get_kitchen_orders_endpoint(
    branch_id: UUID,
    current_user_data: dict = Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Return PREPARING and READY orders for a specific branch.
    """
    return get_kitchen_orders(
        db=db,
        tenant_id=current_user_data["tenant_id"],
        branch_id=branch_id,
    )

    
@router.get(
    "/kitchen/workload",
    response_model=KitchenWorkloadResponse,
)
def get_kitchen_workload_endpoint(
    branch_id: UUID,
    current_user_data: dict = Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Return the current kitchen workload for a specific branch.
    """
    return get_kitchen_workload(
        db=db,
        tenant_id=current_user_data["tenant_id"],
        branch_id=branch_id,
    )


@router.get(
    "/kitchen/queue",
    response_model=KitchenQueueResponse,
)
def get_kitchen_queue_endpoint(
    branch_id: UUID,
    current_user_data: dict = Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Return the current preparing-order queue for a branch.
    """
    return get_kitchen_queue(
        db=db,
        tenant_id=current_user_data["tenant_id"],
        branch_id=branch_id,
    )

    
@router.get(
    "/kitchen/waiting",
    response_model=KitchenWaitingQueueResponse,
)
def get_kitchen_waiting_queue_endpoint(
    branch_id: UUID,
    current_user_data: dict = Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Return orders waiting for available kitchen capacity.
    """
    return get_kitchen_waiting_queue(
        db=db,
        tenant_id=current_user_data["tenant_id"],
        branch_id=branch_id,
    )

    
@router.get(
    "/kitchen/performance",
    response_model=KitchenPerformanceResponse,
)
def get_kitchen_performance_endpoint(
    branch_id: UUID,
    current_user_data: dict = Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Return kitchen preparation performance for a branch.
    """
    return get_kitchen_performance(
        db=db,
        tenant_id=current_user_data["tenant_id"],
        branch_id=branch_id,
    )

    
@router.get(
    "/kitchen/performance/summary",
    response_model=KitchenPerformanceSummaryResponse,
)
def get_kitchen_performance_summary_endpoint(
    branch_id: UUID,
    period: KitchenPerformancePeriod = KitchenPerformancePeriod.CUSTOM,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    current_user_data: dict = Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Return summarized kitchen performance for a branch.
    """
    return get_kitchen_performance_summary(
        db=db,
        tenant_id=current_user_data["tenant_id"],
        branch_id=branch_id,
        period=period,
        start_at=start_at,
        end_at=end_at,
    )
    
    
@router.get(
    "/sales-summary",
    response_model=OrderSalesSummaryResponse,
)
def order_sales_summary_endpoint(
    branch_id: UUID | None = Query(default=None),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    current_user: dict[str, UUID] = Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Return sales summary for the current tenant.
    """

    return get_order_sales_summary(
        db=db,
        tenant_id=current_user["tenant_id"],
        branch_id=branch_id,
        start_date=start_date,
        end_date=end_date,
    )
    
    
@router.get(
    "/sales-trends",
    response_model=list[OrderSalesTrendResponse],
)
def order_sales_trends_endpoint(
    branch_id: UUID | None = Query(default=None),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    current_user: dict[str, UUID] = Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Return daily sales trends for the current tenant.
    """

    return get_order_sales_trends(
        db=db,
        tenant_id=current_user["tenant_id"],
        branch_id=branch_id,
        start_date=start_date,
        end_date=end_date,
    )
    
    
@router.get(
    "/product-sales-performance",
    response_model=list[OrderProductSalesPerformanceResponse],
)
def product_sales_performance_endpoint(
    branch_id: UUID | None = Query(default=None),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    current_user: dict[str, UUID] = Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Return sales performance for each product variant.
    """

    return get_product_sales_performance(
        db=db,
        tenant_id=current_user["tenant_id"],
        branch_id=branch_id,
        start_date=start_date,
        end_date=end_date,
    )
    
    
@router.get(
    "/customer-sales-performance",
    response_model=list[OrderCustomerSalesPerformanceResponse],
)
def customer_sales_performance_endpoint(
    branch_id: UUID | None = Query(default=None),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    current_user: dict[str, UUID] = Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Return sales performance for each customer.
    """

    return get_customer_sales_performance(
        db=db,
        tenant_id=current_user["tenant_id"],
        branch_id=branch_id,
        start_date=start_date,
        end_date=end_date,
    )
    
    
@router.get(
    "/order-type-performance",
    response_model=list[OrderTypePerformanceResponse],
)
def order_type_performance_endpoint(
    branch_id: UUID | None = Query(default=None),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    current_user: dict[str, UUID] = Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Return sales performance grouped by order type.
    """

    return get_order_type_performance(
        db=db,
        tenant_id=current_user["tenant_id"],
        branch_id=branch_id,
        start_date=start_date,
        end_date=end_date,
    )
    
    
@router.get(
    "/sales-by-hour",
    response_model=list[SalesByHourResponse],
)
def sales_by_hour_endpoint(
    branch_id: UUID | None = Query(default=None),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    current_user: dict[str, UUID] = Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Return completed sales performance grouped by hour.
    """

    return get_sales_by_hour(
        db=db,
        tenant_id=current_user["tenant_id"],
        branch_id=branch_id,
        start_date=start_date,
        end_date=end_date,
    )
    
    
@router.get(
    "/sales-by-weekday",
    response_model=list[SalesByWeekdayResponse],
)
def sales_by_weekday_endpoint(
    branch_id: UUID | None = Query(default=None),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    current_user: dict[str, UUID] = Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Return completed sales performance grouped by weekday.
    """

    return get_sales_by_weekday(
        db=db,
        tenant_id=current_user["tenant_id"],
        branch_id=branch_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/busy-hours",
    response_model=BusyHoursAnalysisResponse,
)
def busy_hours_endpoint(
    branch_id: UUID | None = Query(default=None),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    limit: int = Query(
        default=3,
        ge=1,
        le=24,
    ),
    current_user: dict[str, UUID] = Depends(
        get_current_user_data
    ),
    db: Session = Depends(get_db),
):
    """
    Return busy-hour and top-sales-hour analysis.
    """

    return get_busy_hours(
        db=db,
        tenant_id=current_user["tenant_id"],
        branch_id=branch_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    
    
@router.get(
    "/sales-by-weekday-hour",
    response_model=list[SalesByWeekdayHourResponse],
)
def sales_by_weekday_hour_endpoint(
    branch_id: UUID | None = Query(default=None),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    current_user: dict[str, UUID] = Depends(
        get_current_user_data
    ),
    db: Session = Depends(get_db),
):
    """
    Return completed sales grouped by weekday and hour.
    """

    return get_sales_by_weekday_hour(
        db=db,
        tenant_id=current_user["tenant_id"],
        branch_id=branch_id,
        start_date=start_date,
        end_date=end_date,
    )
    
    
@router.get(
    "/daily-business-summary",
    response_model=DailyBusinessSummaryResponse,
)
def daily_business_summary_endpoint(
    target_date: date = Query(...),
    branch_id: UUID | None = Query(default=None),
    current_user: dict[str, UUID] = Depends(
        get_current_user_data
    ),
    db: Session = Depends(get_db),
):
    """
    Return the main business KPIs for a specific day.
    """

    return get_daily_business_summary(
        db=db,
        tenant_id=current_user["tenant_id"],
        target_date=target_date,
        branch_id=branch_id,
    )
    
    
@router.get(
    "/business-dashboard-summary",
    response_model=BusinessDashboardSummaryResponse,
)
def business_dashboard_summary_endpoint(
    target_date: date = Query(...),
    branch_id: UUID = Query(...),
    current_user: dict[str, UUID] = Depends(
        get_current_user_data
    ),
    db: Session = Depends(get_db),
):
    """
    Return the combined business dashboard summary
    for a specific branch and day.
    """

    return get_business_dashboard_summary(
        db=db,
        tenant_id=current_user["tenant_id"],
        target_date=target_date,
        branch_id=branch_id,
    )
    
    
@router.get(
    "/business-risk-metrics",
    response_model=BusinessRiskMetricsResponse,
)
def business_risk_metrics_endpoint(
    target_date: date = Query(...),
    branch_id: UUID = Query(...),
    current_user: dict[str, UUID] = Depends(
        get_current_user_data
    ),
    db: Session = Depends(get_db),
):
    """
    Return operational risk metrics for a branch and day.
    """

    return get_business_risk_metrics(
        db=db,
        tenant_id=current_user["tenant_id"],
        target_date=target_date,
        branch_id=branch_id,
    )
    

@router.get(
    "/{order_id}",
    response_model=OrderResponse,
)
def get_order_endpoint(
    order_id: UUID,
    current_user=Depends(get_current_user_data),
    db: Session = Depends(get_db),
):
    """
    Return a single order for the current tenant.
    """

    return get_order(
        db=db,
        tenant_id=current_user["tenant_id"],
        order_id=order_id,
    )