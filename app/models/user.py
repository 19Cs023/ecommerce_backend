"""
User model.

DESIGN NOTES:
- `hashed_password` is named explicitly (not `password`) so nobody
  ever accidentally assigns a plaintext value to it and ships it.
- `is_active` is a soft-disable flag: banning a user means flipping
  this to False, not deleting their row (which would orphan their
  order history via FK constraints, or silently cascade-delete it).
- One user -> many orders, one user -> one cart. Both relationships
  are defined here AND mirrored via `back_populates` on the other side
  so you can traverse the relationship from either direction in code
  (`user.orders` or `order.owner`).
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base_class import Base
from app.models.enums import UserRole


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.CUSTOMER, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # `cascade="all, delete-orphan"` on the cart: if a user is deleted,
    # their cart (and its items) go with them -- a cart has no meaning
    # without its owner. Orders deliberately do NOT cascade-delete
    # (see Order model) since financial records should outlive account
    # deletion for audit purposes.
    cart: Mapped["Cart"] = relationship(back_populates="owner", uselist=False, cascade="all, delete-orphan")
    orders: Mapped[list["Order"]] = relationship(back_populates="owner")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"
