"""
Category model -- deliberately self-referential to support a
category tree (e.g. Electronics -> Laptops -> Gaming Laptops)
without needing a separate join table.

`parent_id` pointing back to the same table is called an "adjacency
list" pattern. It's simple and fine for shallow trees (a few levels).
If you ever need deep trees with fast "get all descendants" queries,
look into "materialized path" or "nested set" patterns instead --
but don't reach for that complexity until you actually need it.
"""

from typing import Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True, nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"), nullable=True)

    # `remote_side=[id]` tells SQLAlchemy which side of the self-join
    # is the "one" (parent) vs the "many" (children) -- without it,
    # SQLAlchemy can't disambiguate a self-referential relationship.
    parent: Mapped[Optional["Category"]] = relationship(remote_side=[id], back_populates="children")
    children: Mapped[list["Category"]] = relationship(back_populates="parent")

    products: Mapped[list["Product"]] = relationship(back_populates="category")

    def __repr__(self) -> str:
        return f"<Category id={self.id} name={self.name!r}>"
