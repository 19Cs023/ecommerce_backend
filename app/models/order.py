"""
Order + OrderItem.

THE MOST IMPORTANT DESIGN DECISION IN THIS WHOLE SCHEMA:
OrderItem stores its OWN `unit_price_cents` and `product_name`
snapshot, copied from the Product at the moment of purchase --
it does NOT just reference `product.price_cents` live.

Why: if you change a product's price next week, every past invoice
referencing that product must still show the price the customer
actually paid. Same for the name (products get renamed/rebranded).
This is a general pattern for any "historical record" table: snapshot
the facts that matter at the time of the event, don't rely on a live
join to a mutable row. It's why order totals are correct forever, even
after the product catalog changes underneath them.

WHY ORDERS DON'T CASCADE-DELETE WHEN A USER IS DELETED:
Financial records typically need to be retained for accounting/legal
reasons even after a user closes their account. `user_id` is nullable
here specifically so a user can be deleted (GDPR "right to be
forgotten" style requests) while the order row -- and its revenue
history -- persists with a null owner.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base_class import Base
from app.models.enums import OrderStatus


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False)

    # Snapshot of the order total at creation time (sum of order_items).
    # Denormalized on purpose: computing this via SUM() on every list-
    # orders request is wasteful when it's written once and read often.
    total_cents: Mapped[int] = mapped_column(Integer, nullable=False)

    shipping_address: Mapped[str] = mapped_column(String(500), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped[Optional["User"]] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Order id={self.id} status={self.status} total_cents={self.total_cents}>"


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    product_id: Mapped[Optional[int]] = mapped_column(ForeignKey("products.id"), nullable=True)

    # Snapshots -- see module docstring for why these are copied, not joined live.
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    order: Mapped["Order"] = relationship(back_populates="items")
    product: Mapped[Optional["Product"]] = relationship(back_populates="order_items")

    @property
    def line_total_cents(self) -> int:
        return self.unit_price_cents * self.quantity
