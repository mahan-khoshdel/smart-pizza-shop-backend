from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.services.inventory import consume_inventory

from app.database.models.branch import Branch
from app.database.models.customer import Customer
from app.database.models.customer_address import CustomerAddress
from app.database.models.order import Order, OrderItem, OrderStatus
from app.repositories.order_status_history import OrderStatusHistoryRepository
from app.database.models.product_variant import ProductVariant
from app.repositories.order import OrderRepository
from app.schemas.order import OrderCreate
from app.schemas.kitchen import KitchenPerformancePeriod
from app.database.models.recipe_item import RecipeItem
from app.repositories.recipe import RecipeRepository


def _get_expected_preparation_seconds(
    durations: list[float],
) -> float | None:
    """
    Return a robust preparation-time baseline.

    Uses the discrete 50th percentile (lower median) instead
    of a simple average so that an unusually long preparation
    record does not distort kitchen ETA calculations.
    """

    if not durations:
        return None

    sorted_durations = sorted(durations)

    middle_index = (len(sorted_durations) - 1) // 2

    return round(
        sorted_durations[middle_index],
        2,
    )
    
        
def _get_expected_preparation_seconds(
    durations: list[float],
) -> float | None:
    """
    Return a robust preparation-time baseline.

    Uses the lower median so an unusually long test or outlier
    does not distort the operational ETA baseline.
    """

    if not durations:
        return None

    sorted_durations = sorted(durations)

    middle_index = (len(sorted_durations) - 1) // 2

    return round(
        sorted_durations[middle_index],
        2,
    )


def create_order(
    db: Session,
    tenant_id: UUID,
    data: OrderCreate,
) -> dict:
    """
    Create a new order for the current tenant.

    The service validates the branch, optional customer,
    optional customer address, and all product variants
    before creating the order and its items.
    """

    order_repository = OrderRepository(db)

    # ---------------------------------------------------------
    # 1. Check duplicate order number inside the tenant
    # ---------------------------------------------------------
    existing_order = order_repository.get_by_order_number(
        order_number=data.order_number,
        tenant_id=tenant_id,
    )

    if existing_order is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Order number already exists.",
        )

    # ---------------------------------------------------------
    # 2. Check branch
    # ---------------------------------------------------------
    branch = db.scalar(
        select(Branch).where(
            Branch.id == data.branch_id,
            Branch.tenant_id == tenant_id,
        )
    )

    if branch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found.",
        )

    # ---------------------------------------------------------
    # 3. Check customer if provided
    # ---------------------------------------------------------
    if data.customer_id is not None:
        customer = db.scalar(
            select(Customer).where(
                Customer.id == data.customer_id,
                Customer.tenant_id == tenant_id,
            )
        )

        if customer is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found.",
            )

    # ---------------------------------------------------------
    # 4. Check delivery address
    # ---------------------------------------------------------
    delivery_address = None

    if data.order_type == "DELIVERY":
        if data.customer_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Delivery orders require a customer.",
            )

        if data.customer_address_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Delivery orders require a customer address.",
            )

    if data.customer_address_id is not None:
        if data.customer_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Customer is required when address is provided.",
            )

        delivery_address = db.scalar(
            select(CustomerAddress).where(
                CustomerAddress.id == data.customer_address_id,
                CustomerAddress.customer_id == data.customer_id,
                CustomerAddress.tenant_id == tenant_id,
            )
        )

        if delivery_address is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer address not found.",
            )

    # ---------------------------------------------------------
    # 5. Order must contain at least one item
    # ---------------------------------------------------------
    if not data.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order must contain at least one item.",
        )

    subtotal = 0
    order_items: list[OrderItem] = []

    try:
        # -----------------------------------------------------
        # 6. Validate every product variant and calculate prices
        # -----------------------------------------------------
        for item_data in data.items:

            if item_data.quantity <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Item quantity must be greater than zero.",
                )

            product_variant = db.scalar(
                select(ProductVariant).where(
                    ProductVariant.id == item_data.product_variant_id,
                    ProductVariant.tenant_id == tenant_id,
                )
            )

            if product_variant is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=(
                        "Product variant not found: "
                        f"{item_data.product_variant_id}"
                    ),
                )

            if not product_variant.is_available:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Product variant is not available: "
                        f"{product_variant.id}"
                    ),
                )

            unit_price = product_variant.price
            total_price = unit_price * item_data.quantity

            subtotal += total_price

            order_items.append(
                OrderItem(
                    product_variant_id=product_variant.id,
                    quantity=item_data.quantity,
                    unit_price=unit_price,
                    total_price=total_price,
                )
            )

        # -----------------------------------------------------
        # 7. Create order with delivery address snapshot
        # -----------------------------------------------------
        order = Order(
            tenant_id=tenant_id,
            branch_id=data.branch_id,
            customer_id=data.customer_id,
            order_number=data.order_number,
            order_type=data.order_type,
            status=OrderStatus.REGISTERED,
            note=data.note,
            delivery_recipient_name=(
                delivery_address.recipient_name
                if delivery_address is not None
                else None
            ),
            delivery_phone=(
                delivery_address.phone
                if delivery_address is not None
                else None
            ),
            delivery_address_line=(
                delivery_address.address_line
                if delivery_address is not None
                else None
            ),
            delivery_city=(
                delivery_address.city
                if delivery_address is not None
                else None
            ),
            delivery_postal_code=(
                delivery_address.postal_code
                if delivery_address is not None
                else None
            ),
            subtotal=subtotal,
            discount_total=0,
            tax_total=0,
            total=subtotal,
        )

        db.add(order)
        db.flush()

        # -----------------------------------------------------
        # 8. Attach order items
        # -----------------------------------------------------
        for order_item in order_items:
            order_item.order_id = order.id
            db.add(order_item)
        db.flush()

        history_repository = OrderStatusHistoryRepository(db)

        history_repository.create(
            order_id=order.id,
            from_status=None,
            to_status=OrderStatus.REGISTERED,
        )
        
        db.commit()
        db.refresh(order)

        # -----------------------------------------------------
        # 9. Return order with its items
        # -----------------------------------------------------
        items = order_repository.get_items(
            order_id=order.id,
        )

        return {
            "id": order.id,
            "tenant_id": order.tenant_id,
            "branch_id": order.branch_id,
            "customer_id": order.customer_id,
            "order_number": order.order_number,
            "order_type": order.order_type,
            "status": order.status,
            "note": order.note,
            "delivery_recipient_name": order.delivery_recipient_name,
            "delivery_phone": order.delivery_phone,
            "delivery_address_line": order.delivery_address_line,
            "delivery_city": order.delivery_city,
            "delivery_postal_code": order.delivery_postal_code,
            "subtotal": order.subtotal,
            "discount_total": order.discount_total,
            "tax_total": order.tax_total,
            "total": order.total,
            "inventory_consumed_at": order.inventory_consumed_at,
            "items": items,
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise


def get_orders(
    db: Session,
    tenant_id: UUID,
    status: OrderStatus | None = None,
) -> list[dict]:
    """
    Return orders for the current tenant.

    When status is provided, only orders with that status
    are returned.
    """

    order_repository = OrderRepository(db)

    orders = order_repository.get_all(
        tenant_id=tenant_id,
        status=status.value if status is not None else None,
    )

    result = []

    for order in orders:
        items = order_repository.get_items(
            order_id=order.id,
        )

        result.append(
            {
                "id": order.id,
                "tenant_id": order.tenant_id,
                "branch_id": order.branch_id,
                "customer_id": order.customer_id,
                "order_number": order.order_number,
                "order_type": order.order_type,
                "status": order.status,
                "note": order.note,
                "delivery_recipient_name": order.delivery_recipient_name,
                "delivery_phone": order.delivery_phone,
                "delivery_address_line": order.delivery_address_line,
                "delivery_city": order.delivery_city,
                "delivery_postal_code": order.delivery_postal_code,
                "subtotal": order.subtotal,
                "discount_total": order.discount_total,
                "tax_total": order.tax_total,
                "total": order.total,
                "inventory_consumed_at": order.inventory_consumed_at,
                "items": items,
            }
        )

    return result


def get_order(
    db: Session,
    tenant_id: UUID,
    order_id: UUID,
) -> dict:
    """
    Return a single order with its order items
    for the current tenant.
    """

    repository = OrderRepository(db)

    order = repository.get_by_id(
        order_id=order_id,
        tenant_id=tenant_id,
    )

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )

    items = repository.get_items(
        order_id=order.id,
    )

    return {
        "id": order.id,
        "tenant_id": order.tenant_id,
        "branch_id": order.branch_id,
        "customer_id": order.customer_id,
        "order_number": order.order_number,
        "order_type": order.order_type,
        "status": order.status,
        "note": order.note,
        "delivery_recipient_name": order.delivery_recipient_name,
        "delivery_phone": order.delivery_phone,
        "delivery_address_line": order.delivery_address_line,
        "delivery_city": order.delivery_city,
        "delivery_postal_code": order.delivery_postal_code,
        "subtotal": order.subtotal,
        "discount_total": order.discount_total,
        "tax_total": order.tax_total,
        "total": order.total,
        "inventory_consumed_at": order.inventory_consumed_at,
        "items": items,
    }
    
    
def _promote_waiting_orders(
    db: Session,
    tenant_id: UUID,
    branch_id: UUID,
    repository: OrderRepository,
) -> list[Order]:
    """
    Automatically move the oldest REGISTERED orders into PREPARING
    when kitchen capacity becomes available.

    This function does not commit the transaction.
    """

    branch = db.scalar(
        select(Branch)
        .where(
            Branch.id == branch_id,
            Branch.tenant_id == tenant_id,
        )
        .with_for_update()
    )

    if branch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found.",
        )

    workload = repository.get_kitchen_workload(
        tenant_id=tenant_id,
        branch_id=branch_id,
    )

    capacity_available = max(
        branch.kitchen_capacity
        - workload["preparing_count"],
        0,
    )

    if capacity_available <= 0:
        return []

    waiting_orders = repository.get_waiting_orders_for_promotion(
        tenant_id=tenant_id,
        branch_id=branch_id,
        limit=capacity_available,
    )

    if not waiting_orders:
        return []

    history_repository = OrderStatusHistoryRepository(db)

    preparing_at = datetime.now(timezone.utc)

    for waiting_order in waiting_orders:
        waiting_order.status = OrderStatus.PREPARING
        waiting_order.preparing_at = preparing_at

        history_repository.create(
            order_id=waiting_order.id,
            from_status=OrderStatus.REGISTERED,
            to_status=OrderStatus.PREPARING,
            note="Automatically moved from waiting queue.",
        )

    db.flush()

    return waiting_orders


def update_order_status(
    db: Session,
    tenant_id: UUID,
    order_id: UUID,
    new_status: OrderStatus,
) -> dict:
    """
    Update an order status according to the allowed order workflow.

    When an order moves to PREPARING, the branch kitchen capacity
    is checked before allowing the transition.

    When an order moves to READY, waiting REGISTERED orders are
    automatically promoted to PREPARING when kitchen capacity
    becomes available.

    When an order moves to COMPLETED, the required inventory is
    automatically consumed using FEFO in the same transaction.
    """

    repository = OrderRepository(db)

    order = repository.get_by_id(
        order_id=order_id,
        tenant_id=tenant_id,
    )

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )

    allowed_transitions = {
        OrderStatus.REGISTERED: {
            OrderStatus.PREPARING,
            OrderStatus.CANCELLED,
        },
        OrderStatus.PREPARING: {
            OrderStatus.READY,
            OrderStatus.CANCELLED,
        },
        OrderStatus.READY: {
            OrderStatus.COMPLETED,
            OrderStatus.CANCELLED,
        },
        OrderStatus.COMPLETED: set(),
        OrderStatus.CANCELLED: set(),
    }

    if new_status not in allowed_transitions[order.status]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid status transition: "
                f"{order.status.value} -> {new_status.value}."
            ),
        )

    try:
        # -----------------------------------------------------
        # 1. Check kitchen capacity before PREPARING
        # -----------------------------------------------------
        if new_status == OrderStatus.PREPARING:

            branch = (
                db.scalar(
                    select(Branch)
                    .where(
                        Branch.id == order.branch_id,
                        Branch.tenant_id == tenant_id,
                    )
                    .with_for_update()
                )
            )

            if branch is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Branch not found.",
                )

            workload = repository.get_kitchen_workload(
                tenant_id=tenant_id,
                branch_id=order.branch_id,
            )

            preparing_count = workload["preparing_count"]

            if preparing_count >= branch.kitchen_capacity:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Kitchen capacity reached. "
                        f"Preparing orders: {preparing_count}. "
                        f"Kitchen capacity: {branch.kitchen_capacity}."
                    ),
                )

        # -----------------------------------------------------
        # 2. Complete order and consume inventory atomically
        # -----------------------------------------------------
        if new_status == OrderStatus.COMPLETED:

            if order.inventory_consumed_at is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Inventory has already been consumed "
                        "for this order."
                    ),
                )

            requirements = calculate_order_ingredient_requirements(
                db=db,
                tenant_id=tenant_id,
                order_id=order_id,
            )

            for ingredient_id, quantity in requirements.items():
                consume_inventory(
                    db=db,
                    tenant_id=tenant_id,
                    branch_id=order.branch_id,
                    ingredient_id=ingredient_id,
                    quantity=quantity,
                    commit=False,
                )

            order.inventory_consumed_at = datetime.now(timezone.utc)

        # -----------------------------------------------------
        # 3. Update current order status
        # -----------------------------------------------------
        old_status = order.status

        order.status = new_status

        if new_status == OrderStatus.PREPARING:
            order.preparing_at = datetime.now(timezone.utc)

        elif new_status == OrderStatus.READY:
            order.ready_at = datetime.now(timezone.utc)

        history_repository = OrderStatusHistoryRepository(db)

        history_repository.create(
            order_id=order.id,
            from_status=getattr(old_status, "value", old_status),
            to_status=getattr(new_status, "value", new_status),
        )

        # -----------------------------------------------------
        # 4. Promote waiting orders when a PREPARING slot
        #    becomes available
        # -----------------------------------------------------
        if (
            old_status == OrderStatus.PREPARING
            and new_status == OrderStatus.READY
        ):
            db.flush()

            _promote_waiting_orders(
                db=db,
                tenant_id=tenant_id,
                branch_id=order.branch_id,
                repository=repository,
            )

        # -----------------------------------------------------
        # 5. Commit the whole transaction
        # -----------------------------------------------------
        db.commit()
        db.refresh(order)

        # -----------------------------------------------------
        # 6. Load order items for the response
        # -----------------------------------------------------
        items = repository.get_items(
            order_id=order.id,
        )

        return {
            "id": order.id,
            "tenant_id": order.tenant_id,
            "branch_id": order.branch_id,
            "customer_id": order.customer_id,
            "order_number": order.order_number,
            "order_type": order.order_type,
            "status": order.status,
            "note": order.note,
            "delivery_recipient_name": order.delivery_recipient_name,
            "delivery_phone": order.delivery_phone,
            "delivery_address_line": order.delivery_address_line,
            "delivery_city": order.delivery_city,
            "delivery_postal_code": order.delivery_postal_code,
            "subtotal": order.subtotal,
            "discount_total": order.discount_total,
            "tax_total": order.tax_total,
            "total": order.total,
            "inventory_consumed_at": order.inventory_consumed_at,
            "items": items,
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise
    
    
def cancel_order(
    db: Session,
    tenant_id: UUID,
    order_id: UUID,
) -> dict:
    """
    Cancel an order when its current status allows cancellation.
    """

    repository = OrderRepository(db)

    order = repository.get_by_id(
        order_id=order_id,
        tenant_id=tenant_id,
    )

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )

    cancellable_statuses = {
        OrderStatus.REGISTERED,
        OrderStatus.PREPARING,
        OrderStatus.READY,
    }

    if order.status not in cancellable_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Order cannot be cancelled from status "
                f"{order.status.value}."
            ),
        )

    try:
        old_status = order.status

        order.status = OrderStatus.CANCELLED

        history_repository = OrderStatusHistoryRepository(db)

        history_repository.create(
            order_id=order.id,
            from_status=getattr(old_status, "value", old_status),
            to_status=OrderStatus.CANCELLED.value,
        )

        db.commit()
        db.refresh(order)

        items = repository.get_items(
            order_id=order.id,
        )

        return {
            "id": order.id,
            "tenant_id": order.tenant_id,
            "branch_id": order.branch_id,
            "customer_id": order.customer_id,
            "order_number": order.order_number,
            "order_type": order.order_type,
            "status": order.status,
            "note": order.note,
            "delivery_recipient_name": order.delivery_recipient_name,
            "delivery_phone": order.delivery_phone,
            "delivery_address_line": order.delivery_address_line,
            "delivery_city": order.delivery_city,
            "delivery_postal_code": order.delivery_postal_code,
            "subtotal": order.subtotal,
            "discount_total": order.discount_total,
            "tax_total": order.tax_total,
            "total": order.total,
            "inventory_consumed_at": order.inventory_consumed_at,
            "items": items,
        }

    except Exception:
        db.rollback()
        raise


def calculate_order_ingredient_requirements(
    db: Session,
    tenant_id: UUID,
    order_id: UUID,
) -> dict[UUID, Decimal]:
    """
    Calculate total ingredient requirements for an order
    based on the active recipe of each ordered product variant.
    """

    order_repository = OrderRepository(db)
    recipe_repository = RecipeRepository(db)

    order = order_repository.get_by_id(
        order_id=order_id,
        tenant_id=tenant_id,
    )

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )

    order_items = order_repository.get_items(
        order_id=order.id,
    )

    if not order_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order has no items.",
        )

    ingredient_requirements: dict[UUID, Decimal] = {}

    for order_item in order_items:
        recipe = recipe_repository.get_active_by_product_variant(
            product_variant_id=order_item.product_variant_id,
            tenant_id=tenant_id,
        )

        if recipe is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "No active recipe found for product variant: "
                    f"{order_item.product_variant_id}"
                ),
            )

        recipe_items = recipe_repository.get_items(
            recipe_id=recipe.id,
        )

        if not recipe_items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Recipe has no ingredients: {recipe.id}",
            )

        for recipe_item in recipe_items:
            required_quantity = (
                recipe_item.quantity * order_item.quantity
            )

            ingredient_requirements[recipe_item.ingredient_id] = (
                ingredient_requirements.get(
                    recipe_item.ingredient_id,
                    Decimal("0"),
                )
                + required_quantity
            )

    return ingredient_requirements


def get_order_ingredient_requirements(
    db: Session,
    tenant_id: UUID,
    order_id: UUID,
) -> dict:
    """
    Return calculated ingredient requirements for an order.
    """

    requirements = calculate_order_ingredient_requirements(
        db=db,
        tenant_id=tenant_id,
        order_id=order_id,
    )

    return {
        "order_id": order_id,
        "requirements": [
            {
                "ingredient_id": ingredient_id,
                "quantity": quantity,
            }
            for ingredient_id, quantity in requirements.items()
        ],
    }

    
def consume_order_inventory(
    db: Session,
    tenant_id: UUID,
    order_id: UUID,
) -> dict:
    """
    Consume all inventory required by an order using FEFO.

    Inventory is consumed only once and only for completed orders.
    """

    repository = OrderRepository(db)

    order = repository.get_by_id(
        order_id=order_id,
        tenant_id=tenant_id,
    )

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )

    if order.status != OrderStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inventory can only be consumed for completed orders.",
        )

    if order.inventory_consumed_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Inventory has already been consumed for this order.",
        )

    requirements = calculate_order_ingredient_requirements(
        db=db,
        tenant_id=tenant_id,
        order_id=order_id,
    )

    try:
        for ingredient_id, quantity in requirements.items():
            consume_inventory(
                db=db,
                tenant_id=tenant_id,
                branch_id=order.branch_id,
                ingredient_id=ingredient_id,
                quantity=quantity,
                commit=False,
            )

        order.inventory_consumed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(order)

        items = repository.get_items(
            order_id=order.id,
        )

        return {
            "id": order.id,
            "tenant_id": order.tenant_id,
            "branch_id": order.branch_id,
            "customer_id": order.customer_id,
            "order_number": order.order_number,
            "order_type": order.order_type,
            "status": order.status,
            "note": order.note,
            "delivery_recipient_name": order.delivery_recipient_name,
            "delivery_phone": order.delivery_phone,
            "delivery_address_line": order.delivery_address_line,
            "delivery_city": order.delivery_city,
            "delivery_postal_code": order.delivery_postal_code,
            "subtotal": order.subtotal,
            "discount_total": order.discount_total,
            "tax_total": order.tax_total,
            "total": order.total,
            "inventory_consumed_at": order.inventory_consumed_at,
            "items": items,
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise


def get_order_status_history(
    db: Session,
    order_id: UUID,
    tenant_id: UUID,
):
    """
    Return the complete status history of an order.

    The order is first checked against the tenant to prevent
    cross-tenant access to status history.
    """

    order_repository = OrderRepository(db)

    order = order_repository.get_by_id(
        order_id=order_id,
        tenant_id=tenant_id,
    )

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )

    history_repository = OrderStatusHistoryRepository(db)

    return history_repository.get_by_order_id(
        order_id=order.id,
    )

    
def get_kitchen_orders(
    db: Session,
    tenant_id: UUID,
    branch_id: UUID,
) -> list[dict]:
    """
    Return orders currently relevant to the kitchen.

    Only PREPARING and READY orders belonging to the
    requested branch and current tenant are returned.

    For PREPARING orders, the service compares the current
    preparation time with the historical average preparation
    time of completed kitchen orders for the same branch.
    """

    order_repository = OrderRepository(db)

    orders = order_repository.get_kitchen_orders(
        tenant_id=tenant_id,
        branch_id=branch_id,
    )

    # ---------------------------------------------------------
    # Calculate historical preparation baseline
    # ---------------------------------------------------------
    historical_durations = (
        order_repository.get_kitchen_preparation_durations(
            tenant_id=tenant_id,
            branch_id=branch_id,
        )
    )

    expected_preparation_seconds = (
        _get_expected_preparation_seconds(
            historical_durations
        )
    )

    expected_preparation_minutes = (
        round(
            expected_preparation_seconds / 60,
            2,
        )
        if expected_preparation_seconds is not None
        else None
    )

    result = []

    for order in orders:
        items = order_repository.get_items(
            order_id=order.id,
        )

        preparation_elapsed_seconds = None
        preparation_elapsed_minutes = None

        is_overdue = False
        overdue_seconds = None
        overdue_minutes = None

        # -----------------------------------------------------
        # Calculate current preparation duration
        # -----------------------------------------------------
        if order.preparing_at is not None:
            end_time = (
                order.ready_at
                if order.ready_at is not None
                else datetime.now(timezone.utc)
            )

            preparation_elapsed_seconds = max(
                (
                    end_time - order.preparing_at
                ).total_seconds(),
                0,
            )

            preparation_elapsed_seconds = round(
                preparation_elapsed_seconds,
                2,
            )

            preparation_elapsed_minutes = round(
                preparation_elapsed_seconds / 60,
                2,
            )

        # -----------------------------------------------------
        # Determine whether a PREPARING order is overdue
        # -----------------------------------------------------
        if (
            order.status == OrderStatus.PREPARING
            and preparation_elapsed_seconds is not None
            and expected_preparation_seconds is not None
            and preparation_elapsed_seconds
            > expected_preparation_seconds
        ):
            is_overdue = True

            overdue_seconds = round(
                preparation_elapsed_seconds
                - expected_preparation_seconds,
                2,
            )

            overdue_minutes = round(
                overdue_seconds / 60,
                2,
            )

        result.append(
            {
                "id": order.id,
                "tenant_id": order.tenant_id,
                "branch_id": order.branch_id,
                "customer_id": order.customer_id,
                "order_number": order.order_number,
                "order_type": order.order_type,
                "status": order.status,
                "note": order.note,
                "delivery_recipient_name": (
                    order.delivery_recipient_name
                ),
                "delivery_phone": order.delivery_phone,
                "delivery_address_line": (
                    order.delivery_address_line
                ),
                "delivery_city": order.delivery_city,
                "delivery_postal_code": (
                    order.delivery_postal_code
                ),
                "subtotal": order.subtotal,
                "discount_total": order.discount_total,
                "tax_total": order.tax_total,
                "total": order.total,
                "inventory_consumed_at": (
                    order.inventory_consumed_at
                ),
                "preparation_elapsed_seconds": (
                    preparation_elapsed_seconds
                ),
                "preparation_elapsed_minutes": (
                    preparation_elapsed_minutes
                ),
                "expected_preparation_seconds": (
                    expected_preparation_seconds
                ),
                "expected_preparation_minutes": (
                    expected_preparation_minutes
                ),
                "is_overdue": is_overdue,
                "overdue_seconds": overdue_seconds,
                "overdue_minutes": overdue_minutes,
                "items": items,
            }
        )

    return result


def get_kitchen_workload(
    db: Session,
    tenant_id: UUID,
    branch_id: UUID,
) -> dict:
    """
    Return the current kitchen workload and capacity
    for a specific branch.
    """

    order_repository = OrderRepository(db)

    branch = db.scalar(
        select(Branch).where(
            Branch.id == branch_id,
            Branch.tenant_id == tenant_id,
        )
    )

    if branch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found.",
        )

    workload = order_repository.get_kitchen_workload(
        tenant_id=tenant_id,
        branch_id=branch_id,
    )

    preparing_count = workload["preparing_count"]
    kitchen_capacity = branch.kitchen_capacity

    capacity_available = max(
        kitchen_capacity - preparing_count,
        0,
    )

    is_at_capacity = preparing_count >= kitchen_capacity

    return {
        "branch_id": branch_id,
        "preparing_count": preparing_count,
        "ready_count": workload["ready_count"],
        "active_count": workload["active_count"],
        "kitchen_capacity": kitchen_capacity,
        "capacity_available": capacity_available,
        "is_at_capacity": is_at_capacity,
    }

    
def get_kitchen_queue(
    db: Session,
    tenant_id: UUID,
    branch_id: UUID,
) -> dict:
    """
    Return the current preparing-order queue for a branch.

    Each queue item includes preparation timing, remaining time,
    overdue information, and an estimated ready timestamp based
    on the historical preparation average for the same branch.
    """

    repository = OrderRepository(db)

    branch = db.scalar(
        select(Branch).where(
            Branch.id == branch_id,
            Branch.tenant_id == tenant_id,
        )
    )

    if branch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found.",
        )

    queue_rows = repository.get_kitchen_queue(
        tenant_id=tenant_id,
        branch_id=branch_id,
    )

    # ---------------------------------------------------------
    # Historical preparation baseline
    # ---------------------------------------------------------
    historical_durations = (
        repository.get_kitchen_preparation_durations(
            tenant_id=tenant_id,
            branch_id=branch_id,
        )
    )

    expected_preparation_seconds = (
        _get_expected_preparation_seconds(
            historical_durations
        )
    )

    expected_preparation_minutes = (
        round(
            expected_preparation_seconds / 60,
            2,
        )
        if expected_preparation_seconds is not None
        else None
    )

    queue = []

    for order, queue_position in queue_rows:
        preparation_elapsed_seconds = None
        preparation_elapsed_minutes = None

        remaining_preparation_seconds = None
        remaining_preparation_minutes = None

        estimated_ready_at = None

        is_overdue = False
        overdue_seconds = None
        overdue_minutes = None

        # -----------------------------------------------------
        # Current preparation duration
        # -----------------------------------------------------
        if order.preparing_at is not None:
            current_time = datetime.now(timezone.utc)

            preparation_elapsed_seconds = max(
                (
                    current_time - order.preparing_at
                ).total_seconds(),
                0,
            )

            preparation_elapsed_seconds = round(
                preparation_elapsed_seconds,
                2,
            )

            preparation_elapsed_minutes = round(
                preparation_elapsed_seconds / 60,
                2,
            )

            # -------------------------------------------------
            # Remaining time / overdue time
            # -------------------------------------------------
            if expected_preparation_seconds is not None:
                remaining_seconds = (
                    expected_preparation_seconds
                    - preparation_elapsed_seconds
                )

                if remaining_seconds > 0:
                    remaining_preparation_seconds = round(
                        remaining_seconds,
                        2,
                    )

                    remaining_preparation_minutes = round(
                        remaining_seconds / 60,
                        2,
                    )

                else:
                    remaining_preparation_seconds = 0
                    remaining_preparation_minutes = 0

                    is_overdue = True

                    overdue_seconds = round(
                        abs(remaining_seconds),
                        2,
                    )

                    overdue_minutes = round(
                        overdue_seconds / 60,
                        2,
                    )

                # ---------------------------------------------
                # Estimated ready timestamp
                # ---------------------------------------------
                estimated_ready_at = (
                    current_time
                    + timedelta(
                        seconds=remaining_preparation_seconds,
                    )
                )

    # ---------------------------------------------------------
        queue.append(
            {
                "order_id": order.id,
                "order_number": order.order_number,
                "queue_position": queue_position,
                "status": order.status.value,
                "created_at": order.created_at,
                "preparation_elapsed_seconds": (
                    preparation_elapsed_seconds
                ),
                "preparation_elapsed_minutes": (
                    preparation_elapsed_minutes
                ),
                "expected_preparation_seconds": (
                    expected_preparation_seconds
                ),
                "expected_preparation_minutes": (
                    expected_preparation_minutes
                ),
                "remaining_preparation_seconds": (
                    remaining_preparation_seconds
                ),
                "remaining_preparation_minutes": (
                    remaining_preparation_minutes
                ),
                "estimated_ready_at": estimated_ready_at,
                "is_overdue": is_overdue,
                "overdue_seconds": overdue_seconds,
                "overdue_minutes": overdue_minutes,
            }
        )

    return {
        "branch_id": branch_id,
        "total_preparing": len(queue),
        "queue": queue,
    }
    
def get_kitchen_performance(
    db: Session,
    tenant_id: UUID,
    branch_id: UUID,
) -> dict:
    """
    Return kitchen preparation performance for a branch.
    """

    repository = OrderRepository(db)

    branch = db.scalar(
        select(Branch).where(
            Branch.id == branch_id,
            Branch.tenant_id == tenant_id,
        )
    )

    if branch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found.",
        )

    durations = repository.get_kitchen_preparation_durations(
        tenant_id=tenant_id,
        branch_id=branch_id,
    )

    prepared_order_count = len(durations)

    if prepared_order_count == 0:
        return {
            "branch_id": branch_id,
            "prepared_order_count": 0,
            "average_preparation_seconds": None,
            "average_preparation_minutes": None,
            "fastest_preparation_seconds": None,
            "slowest_preparation_seconds": None,
        }

    average_seconds = (
        sum(durations) / prepared_order_count
    )

    fastest_seconds = min(durations)
    slowest_seconds = max(durations)

    return {
        "branch_id": branch_id,
        "prepared_order_count": prepared_order_count,
        "average_preparation_seconds": round(
            average_seconds,
            2,
        ),
        "average_preparation_minutes": round(
            average_seconds / 60,
            2,
        ),
        "fastest_preparation_seconds": round(
            fastest_seconds,
            2,
        ),
        "slowest_preparation_seconds": round(
            slowest_seconds,
            2,
        ),
    }
    
    
def get_kitchen_waiting_queue(
    db: Session,
    tenant_id: UUID,
    branch_id: UUID,
) -> dict:
    """
    Return orders waiting for available kitchen capacity.

    REGISTERED orders are ordered by creation time.
    """

    repository = OrderRepository(db)

    branch = db.scalar(
        select(Branch).where(
            Branch.id == branch_id,
            Branch.tenant_id == tenant_id,
        )
    )

    if branch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found.",
        )

    workload = repository.get_kitchen_workload(
        tenant_id=tenant_id,
        branch_id=branch_id,
    )

    preparing_count = workload["preparing_count"]

    capacity_available = max(
        branch.kitchen_capacity - preparing_count,
        0,
    )

    waiting_orders = repository.get_kitchen_waiting_orders(
        tenant_id=tenant_id,
        branch_id=branch_id,
    )

    queue = []

    for index, order in enumerate(
        waiting_orders,
        start=1,
    ):
        queue.append(
            {
                "order_id": order.id,
                "order_number": order.order_number,
                "queue_position": index,
                "status": order.status.value,
                "created_at": order.created_at,
                "can_start_now": (
                    index <= capacity_available
                ),
            }
        )

    return {
        "branch_id": branch_id,
        "kitchen_capacity": branch.kitchen_capacity,
        "preparing_count": preparing_count,
        "capacity_available": capacity_available,
        "total_waiting": len(queue),
        "queue": queue,
    }

    
def _resolve_kitchen_performance_range(
    period: KitchenPerformancePeriod,
    start_at: datetime | None,
    end_at: datetime | None,
) -> tuple[datetime | None, datetime | None]:
    """
    Resolve a predefined or custom performance time range.

    Predefined periods use Asia/Tehran local time.
    """

    if period == KitchenPerformancePeriod.CUSTOM:
        if start_at is None or end_at is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "start_at and end_at are required "
                    "for CUSTOM period."
                ),
            )

        if start_at > end_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_at must be earlier than or equal to end_at.",
            )

        return start_at, end_at

    if start_at is not None or end_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "start_at and end_at must not be provided "
                "with a predefined period."
            ),
        )

    local_timezone = ZoneInfo("Asia/Tehran")
    now = datetime.now(local_timezone)

    if period == KitchenPerformancePeriod.TODAY:
        start_local = now.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        return start_local.astimezone(timezone.utc), now.astimezone(
            timezone.utc
        )

    if period == KitchenPerformancePeriod.LAST_7_DAYS:
        start_local = (
            now - timedelta(days=6)
        ).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        return start_local.astimezone(timezone.utc), now.astimezone(
            timezone.utc
        )

    if period == KitchenPerformancePeriod.THIS_MONTH:
        start_local = now.replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        return start_local.astimezone(timezone.utc), now.astimezone(
            timezone.utc
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported performance period.",
    )
    
    
def get_kitchen_performance_summary(
    db: Session,
    tenant_id: UUID,
    branch_id: UUID,
    period: KitchenPerformancePeriod,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
) -> dict:
    """
    Return summarized kitchen performance for a branch
    using a predefined or custom time period.
    """

    repository = OrderRepository(db)

    branch = db.scalar(
        select(Branch).where(
            Branch.id == branch_id,
            Branch.tenant_id == tenant_id,
        )
    )

    if branch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found.",
        )

    resolved_start_at, resolved_end_at = (
        _resolve_kitchen_performance_range(
            period=period,
            start_at=start_at,
            end_at=end_at,
        )
    )

    durations = (
        repository.get_kitchen_preparation_durations_in_range(
            tenant_id=tenant_id,
            branch_id=branch_id,
            start_at=resolved_start_at,
            end_at=resolved_end_at,
        )
    )

    prepared_order_count = len(durations)

    if prepared_order_count == 0:
        return {
            "branch_id": branch_id,
            "prepared_order_count": 0,
            "average_preparation_seconds": None,
            "average_preparation_minutes": None,
            "fastest_preparation_seconds": None,
            "slowest_preparation_seconds": None,
            "expected_preparation_seconds": None,
            "expected_preparation_minutes": None,
            "overdue_order_count": 0,
        }

    average_seconds = (
        sum(durations) / prepared_order_count
    )

    fastest_seconds = min(durations)
    slowest_seconds = max(durations)

    expected_seconds = (
        _get_expected_preparation_seconds(durations)
    )

    expected_minutes = (
        round(expected_seconds / 60, 2)
        if expected_seconds is not None
        else None
    )

    overdue_order_count = sum(
        1
        for duration in durations
        if expected_seconds is not None
        and duration > expected_seconds
    )

    return {
        "branch_id": branch_id,
        "prepared_order_count": prepared_order_count,
        "average_preparation_seconds": round(
            average_seconds,
            2,
        ),
        "average_preparation_minutes": round(
            average_seconds / 60,
            2,
        ),
        "fastest_preparation_seconds": round(
            fastest_seconds,
            2,
        ),
        "slowest_preparation_seconds": round(
            slowest_seconds,
            2,
        ),
        "expected_preparation_seconds": expected_seconds,
        "expected_preparation_minutes": expected_minutes,
        "overdue_order_count": overdue_order_count,
    }
    
    
def get_order_sales_summary(
    db: Session,
    tenant_id: UUID,
    branch_id: UUID | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict:
    """
    Return sales summary for the current tenant.

    Sales are calculated only from completed orders.
    """

    repository = OrderRepository(db)

    summary = repository.get_sales_summary(
        tenant_id=tenant_id,
        branch_id=branch_id,
        start_date=start_date,
        end_date=end_date,
    )

    return {
        "branch_id": branch_id,
        "total_order_count": summary["total_order_count"],
        "completed_order_count": summary["completed_order_count"],
        "cancelled_order_count": summary["cancelled_order_count"],
        "total_sales": summary["total_sales"],
        "average_order_value": summary["average_order_value"],
    }
    
    
def get_order_sales_trends(
    db: Session,
    tenant_id: UUID,
    branch_id: UUID | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[dict]:
    """
    Return daily sales trends for the current tenant.

    Only completed orders are included.
    """

    repository = OrderRepository(db)

    trends = repository.get_sales_trends(
        tenant_id=tenant_id,
        branch_id=branch_id,
        start_date=start_date,
        end_date=end_date,
    )

    return trends


def get_product_sales_performance(
    db: Session,
    tenant_id: UUID,
    branch_id: UUID | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[dict]:
    """
    Return sales performance for each product variant.

    Only completed orders are included.
    """

    repository = OrderRepository(db)

    return repository.get_product_sales_performance(
        tenant_id=tenant_id,
        branch_id=branch_id,
        start_date=start_date,
        end_date=end_date,
    )
    
    
def get_customer_sales_performance(
    db: Session,
    tenant_id: UUID,
    branch_id: UUID | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[dict]:
    """
    Return sales performance for each customer.

    Only completed orders with a customer are included.
    """

    repository = OrderRepository(db)

    return repository.get_customer_sales_performance(
        tenant_id=tenant_id,
        branch_id=branch_id,
        start_date=start_date,
        end_date=end_date,
    )
    
    
def get_order_type_performance(
    db: Session,
    tenant_id: UUID,
    branch_id: UUID | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[dict]:
    """
    Return sales performance grouped by order type.

    Only completed orders are included.
    """

    repository = OrderRepository(db)

    return repository.get_order_type_performance(
        tenant_id=tenant_id,
        branch_id=branch_id,
        start_date=start_date,
        end_date=end_date,
    )
    
    
def get_sales_by_hour(
    db: Session,
    tenant_id: UUID,
    branch_id: UUID | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[dict]:
    """
    Return completed sales grouped by order creation hour.
    """

    repository = OrderRepository(db)

    return repository.get_sales_by_hour(
        tenant_id=tenant_id,
        branch_id=branch_id,
        start_date=start_date,
        end_date=end_date,
    )
    
    
def get_sales_by_weekday(
    db: Session,
    tenant_id: UUID,
    branch_id: UUID | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[dict]:
    """
    Return completed sales grouped by weekday.
    """

    repository = OrderRepository(db)

    return repository.get_sales_by_weekday(
        tenant_id=tenant_id,
        branch_id=branch_id,
        start_date=start_date,
        end_date=end_date,
    )
    
    
def get_busy_hours(
    db: Session,
    tenant_id: UUID,
    branch_id: UUID | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = 3,
) -> dict:
    """
    Analyze completed sales by hour.

    Busiest hours are determined by completed order count.
    Top sales hours are determined by total sales.
    """

    repository = OrderRepository(db)

    hourly_rows = repository.get_sales_by_hour(
        tenant_id=tenant_id,
        branch_id=branch_id,
        start_date=start_date,
        end_date=end_date,
    )

    total_completed_order_count = sum(
        row["completed_order_count"]
        for row in hourly_rows
    )

    total_sales = sum(
        (
            row["total_sales"]
            for row in hourly_rows
        ),
        Decimal("0"),
    )

    active_hour_count = len(hourly_rows)

    average_orders_per_active_hour = (
        round(
            total_completed_order_count
            / active_hour_count,
            2,
        )
        if active_hour_count > 0
        else 0.0
    )

    busiest_hours = sorted(
        hourly_rows,
        key=lambda row: (
            -row["completed_order_count"],
            -row["total_sales"],
            row["hour"],
        ),
    )[:limit]

    top_sales_hours = sorted(
        hourly_rows,
        key=lambda row: (
            -row["total_sales"],
            -row["completed_order_count"],
            row["hour"],
        ),
    )[:limit]

    return {
        "total_completed_order_count": (
            total_completed_order_count
        ),
        "total_sales": total_sales,
        "active_hour_count": active_hour_count,
        "average_orders_per_active_hour": (
            average_orders_per_active_hour
        ),
        "busiest_hours": busiest_hours,
        "top_sales_hours": top_sales_hours,
    }
    
    
def get_sales_by_weekday_hour(
    db: Session,
    tenant_id: UUID,
    branch_id: UUID | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[dict]:
    """
    Return completed sales grouped by weekday and hour.
    """

    repository = OrderRepository(db)

    return repository.get_sales_by_weekday_hour(
        tenant_id=tenant_id,
        branch_id=branch_id,
        start_date=start_date,
        end_date=end_date,
    )
    
    
def get_daily_business_summary(
    db: Session,
    tenant_id: UUID,
    target_date: date,
    branch_id: UUID | None = None,
) -> dict:
    """
    Return the main business KPIs for a specific day.

    The current implementation interprets the day in UTC.
    Tenant-specific timezone support will be introduced later.
    """

    start_at = datetime.combine(
        target_date,
        time.min,
        tzinfo=timezone.utc,
    )

    end_at = start_at + timedelta(days=1)

    repository = OrderRepository(db)

    summary = repository.get_daily_business_summary(
        tenant_id=tenant_id,
        start_at=start_at,
        end_at=end_at,
        branch_id=branch_id,
    )

    hourly_rows = repository.get_sales_by_hour(
        tenant_id=tenant_id,
        branch_id=branch_id,
        start_date=start_at,
        end_date=end_at,
    )

    busiest_hour = None
    busiest_hour_order_count = 0

    top_sales_hour = None
    top_sales_hour_total_sales = Decimal("0")

    if hourly_rows:
        busiest = sorted(
            hourly_rows,
            key=lambda row: (
                -row["completed_order_count"],
                -row["total_sales"],
                row["hour"],
            ),
        )[0]

        busiest_hour = busiest["hour"]
        busiest_hour_order_count = (
            busiest["completed_order_count"]
        )

        top_sales = sorted(
            hourly_rows,
            key=lambda row: (
                -row["total_sales"],
                -row["completed_order_count"],
                row["hour"],
            ),
        )[0]

        top_sales_hour = top_sales["hour"]
        top_sales_hour_total_sales = (
            top_sales["total_sales"]
        )

    return {
        "date": target_date,
        "branch_id": branch_id,
        "total_order_count": (
            summary["total_order_count"]
        ),
        "completed_order_count": (
            summary["completed_order_count"]
        ),
        "cancelled_order_count": (
            summary["cancelled_order_count"]
        ),
        "total_sales": summary["total_sales"],
        "average_order_value": (
            summary["average_order_value"]
        ),
        "busiest_hour": busiest_hour,
        "busiest_hour_order_count": (
            busiest_hour_order_count
        ),
        "top_sales_hour": top_sales_hour,
        "top_sales_hour_total_sales": (
            top_sales_hour_total_sales
        ),
    }