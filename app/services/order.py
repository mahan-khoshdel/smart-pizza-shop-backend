from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import datetime, timezone

from app.services.inventory import consume_inventory

from app.database.models.branch import Branch
from app.database.models.customer import Customer
from app.database.models.customer_address import CustomerAddress
from app.database.models.order import Order, OrderItem, OrderStatus
from app.database.models.product_variant import ProductVariant
from app.repositories.order import OrderRepository
from app.schemas.order import OrderCreate
from app.database.models.recipe_item import RecipeItem
from app.repositories.recipe import RecipeRepository


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
) -> list[dict]:
    """
    Return all orders with their order items
    for the current tenant.
    """

    repository = OrderRepository(db)

    orders = repository.get_all(
        tenant_id=tenant_id,
    )

    result = []

    for order in orders:
        items = repository.get_items(
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


def update_order_status(
    db: Session,
    tenant_id: UUID,
    order_id: UUID,
    new_status: OrderStatus,
) -> dict:
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
        order.status = OrderStatus.CANCELLED

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