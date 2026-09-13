from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class CustomerAddress(Base):
    """Represent an address belonging to a customer."""

    __tablename__ = "customer_addresses"

    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "customer_id"],
            ["customers.tenant_id", "customers.id"],
            name="fk_customer_addresses_customer_tenant",
            ondelete="RESTRICT",
        ),
        Index(
            "ix_customer_addresses_customer_default",
            "customer_id",
            unique=True,
            postgresql_where=text("is_default = true"),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "tenants.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    customer_id: Mapped[UUID] = mapped_column(
        nullable=False,
        index=True,
    )

    label: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    recipient_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    phone: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    address_line: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    city: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    postal_code: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    is_default: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )