"""
Product model.

WHY PRICE IS AN INTEGER (CENTS), NOT A FLOAT:
Floats cannot represent most decimal fractions exactly (0.1 + 0.2 !=
0.3 in binary floating point). For money, that rounding error
compounds across millions of transactions into real accounting
discrepancies. Storing `price_cents = 1999` for $19.99 and converting
to dollars only at the presentation layer (schemas) sidesteps the
entire class of bug. (The other common fix is a fixed-point `Decimal`
column -- also fine, but integer cents is simpler and index-friendly.)

WHY `stock_quantity` LIVES ON THE PRODUCT, NOT COMPUTED FROM ORDERS:
Computing "available stock" by summing all past order line items on
every request would get slower as the order history grows, and is
prone to race conditions under concurrent checkouts. Instead we keep
a running `stock_quantity` counter that's decremented atomically at
checkout time (see `services/order_service.py` for the row-locking
pattern that keeps this safe under concurrency).
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(280), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"), nullable=True)
    category: Mapped[Optional["Category"]] = relationship(back_populates="products")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    cart_items: Mapped[list["CartItem"]] = relationship(back_populates="product")
    order_items: Mapped[list["OrderItem"]] = relationship(back_populates="product")

    @property
    def price_display(self) -> str:
        """Convenience for logging/debugging -- API responses format this in the schema layer instead."""
        return f"${self.price_cents / 100:.2f}"

    def __repr__(self) -> str:
        return f"<Product id={self.id} sku={self.sku!r} stock={self.stock_quantity}>"
