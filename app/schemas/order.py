from uuid import UUID

from datetime import date
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict

from app.database.models.order import OrderStatus, OrderType


class OrderItemCreate(BaseModel):
    product_variant_id: UUID
    quantity: int


class OrderCreate(BaseModel):
    branch_id: UUID
    customer_id: UUID | None = None
    customer_address_id: UUID | None = None
    order_number: str
    order_type: OrderType
    note: str | None = None
    items: list[OrderItemCreate]


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_variant_id: UUID
    quantity: int
    unit_price: int
    total_price: int


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    branch_id: UUID
    customer_id: UUID | None

    order_number: str
    order_type: OrderType
    status: OrderStatus
    note: str | None

    delivery_recipient_name: str | None
    delivery_phone: str | None
    delivery_address_line: str | None
    delivery_city: str | None
    delivery_postal_code: str | None

    subtotal: int
    discount_total: int
    tax_total: int
    total: int
    
    inventory_consumed_at: datetime | None
    
    preparation_elapsed_seconds: float | None = None
    preparation_elapsed_minutes: float | None = None
    
    expected_preparation_seconds: float | None = None
    expected_preparation_minutes: float | None = None

    is_overdue: bool = False
    overdue_seconds: float | None = None
    overdue_minutes: float | None = None

    items: list[OrderItemResponse]
    

class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderIngredientRequirementResponse(BaseModel):
    ingredient_id: UUID
    quantity: Decimal


class OrderIngredientRequirementsResponse(BaseModel):
    order_id: UUID
    requirements: list[OrderIngredientRequirementResponse]

    
class OrderStatusHistoryResponse(BaseModel):
    """
    Represents one order status transition.
    """

    id: UUID
    order_id: UUID
    from_status: OrderStatus | None
    to_status: OrderStatus
    changed_at: datetime
    note: str | None


class KitchenWorkloadResponse(BaseModel):
    """
    Represents the current kitchen workload for a branch.
    """

    branch_id: UUID
    preparing_count: int
    ready_count: int
    active_count: int
    kitchen_capacity: int
    capacity_available: int
    is_at_capacity: bool

    
class KitchenPerformanceResponse(BaseModel):
    """
    Represents kitchen preparation performance for a branch.
    """

    branch_id: UUID
    prepared_order_count: int

    average_preparation_seconds: float | None
    average_preparation_minutes: float | None

    fastest_preparation_seconds: float | None
    slowest_preparation_seconds: float | None
    
    
class OrderSalesSummaryResponse(BaseModel):
    """
    Sales summary for a tenant or branch.
    """

    branch_id: UUID | None
    total_order_count: int
    completed_order_count: int
    cancelled_order_count: int
    total_sales: Decimal
    average_order_value: Decimal
    
class OrderSalesTrendResponse(BaseModel):
    """
    Daily sales trend for a tenant or branch.
    """

    date: date
    completed_order_count: int
    total_sales: Decimal
    average_order_value: Decimal
    
    
class OrderProductSalesPerformanceResponse(BaseModel):
    """
    Sales performance for a product variant.
    """

    product_variant_id: UUID
    sku: str
    sold_quantity: int
    order_count: int
    total_sales: Decimal
    
    
class OrderCustomerSalesPerformanceResponse(BaseModel):
    """
    Sales performance for a customer.
    """

    customer_id: UUID
    order_count: int
    total_sales: Decimal
    average_order_value: Decimal
    
    
class OrderTypePerformanceResponse(BaseModel):
    """
    Sales performance grouped by order type.
    """

    order_type: OrderType
    order_count: int
    total_sales: Decimal
    average_order_value: Decimal
    
    
class SalesByHourResponse(BaseModel):
    """
    Completed sales performance grouped by hour.
    """

    hour: int
    completed_order_count: int
    total_sales: Decimal
    average_order_value: Decimal
    
    
class SalesByWeekdayResponse(BaseModel):
    """
    Completed sales performance grouped by weekday.
    """

    weekday: int
    completed_order_count: int
    total_sales: Decimal
    average_order_value: Decimal
    
    
class BusyHourResponse(BaseModel):
    """
    Sales performance for a single busy hour.
    """

    hour: int
    completed_order_count: int
    total_sales: Decimal
    average_order_value: Decimal


class BusyHoursAnalysisResponse(BaseModel):
    """
    Summary of busy hours and top sales hours.
    """

    total_completed_order_count: int
    total_sales: Decimal
    active_hour_count: int
    average_orders_per_active_hour: float
    busiest_hours: list[BusyHourResponse]
    top_sales_hours: list[BusyHourResponse]
    
    
class SalesByWeekdayHourResponse(BaseModel):
    """
    Completed sales performance grouped by weekday and hour.
    """

    weekday: int
    hour: int
    completed_order_count: int
    total_sales: Decimal
    average_order_value: Decimal
    
    
class DailyBusinessSummaryResponse(BaseModel):
    """
    Main business KPIs for a specific day.
    """

    date: date
    branch_id: UUID | None
    total_order_count: int
    completed_order_count: int
    cancelled_order_count: int
    total_sales: Decimal
    average_order_value: Decimal
    busiest_hour: int | None
    busiest_hour_order_count: int
    top_sales_hour: int | None
    top_sales_hour_total_sales: Decimal
    
    
class DashboardKitchenSummaryResponse(BaseModel):
    """
    Current kitchen workload summary for a branch.
    """

    preparing_count: int
    ready_count: int
    active_count: int
    kitchen_capacity: int
    capacity_available: int
    is_at_capacity: bool


class BusinessDashboardSummaryResponse(BaseModel):
    """
    Combined business and kitchen dashboard summary.
    """

    date: date
    branch_id: UUID

    total_order_count: int
    completed_order_count: int
    cancelled_order_count: int

    total_sales: Decimal
    average_order_value: Decimal

    busiest_hour: int | None
    busiest_hour_order_count: int

    top_sales_hour: int | None
    top_sales_hour_total_sales: Decimal

    kitchen: DashboardKitchenSummaryResponse
    
    
class BusinessRiskMetricsResponse(BaseModel):
    """
    Operational risk metrics for a specific branch and day.
    """

    date: date
    branch_id: UUID

    total_order_count: int
    completed_order_count: int
    cancelled_order_count: int
    open_order_count: int

    cancellation_rate_percent: float

    preparing_count: int
    ready_count: int
    active_count: int

    kitchen_capacity: int
    capacity_available: int
    capacity_utilization_percent: float
    is_at_capacity: bool