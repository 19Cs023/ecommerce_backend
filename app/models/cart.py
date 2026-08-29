"""
Cart + CartItem.

WHY A PERSISTENT CART TABLE (INSTEAD OF SESSION/COOKIE STORAGE):
Storing the cart in the DB, tied to the user, means it survives
across devices and browser sessions -- add an item on your phone,
check out on your laptop. The trade-off is a couple of extra queries
per cart operation, which is negligible compared to the UX win.

WHY CartItem IS ITS OWN TABLE (NOT A JSON COLUMN ON Cart):
A JSON blob of `{product_id: quantity}` is tempting for "simplicity",
but then you lose: foreign-key integrity (nothing stops you from
referencing a deleted product), the ability to efficiently query
"how many carts contain product X", and clean field-level updates
(you'd have to read-modify-write the whole blob to change one
quantity). A proper join table costs one extra model but pays for
itself the moment you need any of the above.

`unique constraint` on (cart_id, product_id) prevents the same
product from silently existing as two separate rows in one cart --
adding an already-present product should increment quantity, not
duplicate the row (enforced in the CRUD layer, backed by this
DB-level constraint as a safety net).
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)

    owner: Mapped["User"] = relationship(back_populates="cart")
    items: Mapped[list["CartItem"]] = relationship(
        back_populates="cart", cascade="all, delete-orphan"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CartItem(Base):
    __tablename__ = "cart_items"
    __table_args__ = (UniqueConstraint("cart_id", "product_id", name="uq_cart_product"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    cart: Mapped["Cart"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship(back_populates="cart_items")
