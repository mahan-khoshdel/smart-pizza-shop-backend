from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.branch import Branch
from app.database.models.customer import Customer
from app.database.models.order import Order, OrderItem, OrderStatus
from app.database.models.product_variant import ProductVariant
from app.repositories.order import OrderRepository
from app.schemas.order import OrderCreate


def create_order(
    db: Session,
    tenant_id: UUID,
    data: OrderCreate,
) -> Order:
    """
    Create a new order for the current tenant.

    The service validates the branch, optional customer, and all
    product variants before creating the order and its items.
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
    # 4. Order must contain at least one item
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
        # 5. Validate every product variant and calculate prices
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
        # 6. Create order
        # -----------------------------------------------------
        order = Order(
            tenant_id=tenant_id,
            branch_id=data.branch_id,
            customer_id=data.customer_id,
            order_number=data.order_number,
            order_type=data.order_type,
            status=OrderStatus.REGISTERED,
            note=data.note,
            subtotal=subtotal,
            discount_total=0,
            tax_total=0,
            total=subtotal,
        )

        db.add(order)
        db.flush()

        # -----------------------------------------------------
        # 7. Attach order items
        # -----------------------------------------------------
        for order_item in order_items:
            order_item.order_id = order.id
            db.add(order_item)

        db.commit()
        db.refresh(order)

        return order

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise
    
    
def get_orders(
    db: Session,
    tenant_id: UUID,
) -> list[Order]:
    """
    Return all orders belonging to the current tenant.
    """

    repository = OrderRepository(db)

    return repository.get_all(tenant_id=tenant_id)


def get_order(
    db: Session,
    tenant_id: UUID,
    order_id: UUID,
) -> Order:
    """
    Return a single order belonging to the current tenant.
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

    return order


def update_order_status(
    db: Session,
    tenant_id: UUID,
    order_id: UUID,
    new_status: OrderStatus,
) -> Order:
    """
    Update an order status according to the allowed order workflow.
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
        order.status = new_status

        db.commit()
        db.refresh(order)

        return order

    except Exception:
        db.rollback()
        raise