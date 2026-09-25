from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class OrderType(str, Enum):
    """
    Defines how a customer receives an order.
    """

    DINE_IN = "DINE_IN"
    TAKEAWAY = "TAKEAWAY"
    DELIVERY = "DELIVERY"


class OrderStatus(str, Enum):
    """
    Defines the lifecycle state of an order.
    """

    REGISTERED = "REGISTERED"
    PREPARING = "PREPARING"
    READY = "READY"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Order(Base):
    """
    Represents a customer order.
    """

    __tablename__ = "orders"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    branch_id: Mapped[UUID] = mapped_column(
        ForeignKey("branches.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    customer_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    delivery_recipient_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    delivery_phone: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    delivery_address_line: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    delivery_city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    delivery_postal_code: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    order_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    order_type: Mapped[OrderType] = mapped_column(
        SQLEnum(
            OrderType,
            name="order_type_enum",
        ),
        nullable=False,
    )

    status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(
            OrderStatus,
            name="order_status_enum",
        ),
        nullable=False,
        default=OrderStatus.REGISTERED,
    )

    note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    subtotal: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
    )

    discount_total: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
    )

    tax_total: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
    )

    total: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    
    preparing_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    ready_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    inventory_consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class OrderItem(Base):
    """
    Represents one product variant inside an order.
    """

    __tablename__ = "order_items"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    product_variant_id: Mapped[UUID] = mapped_column(
        ForeignKey("product_variants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    unit_price: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    total_price: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )