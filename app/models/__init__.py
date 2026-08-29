"""
WHY THIS FILE IMPORTS EVERYTHING:
SQLAlchemy's declarative Base only knows about a model class once
Python has actually executed that class's module (that's when
`Base.metadata` gets populated with its table). If you only import
`Base` and call `Base.metadata.create_all()` without ever importing
`Product`, `Order`, etc., SQLAlchemy will silently create a database
missing those tables -- no error, just a quietly incomplete schema.

Importing every model here, and importing `app.models` (not the
individual model files) from `main.py` and Alembic's `env.py`,
guarantees the full metadata is always registered before it's used.
It also lets other modules do `from app.models import User, Product`
instead of tracking which submodule each class lives in.
"""

from app.db.base_class import Base
from app.models.cart import Cart, CartItem
from app.models.category import Category
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.user import User

__all__ = ["Base", "User", "Category", "Product", "Cart", "CartItem", "Order", "OrderItem"]
