"""
Shared enums.

WHY PYTHON ENUMS INSTEAD OF RAW STRINGS:
`order.status = "pendign"` (typo) is a silent bug that only surfaces
when some later filter `WHERE status = 'pending'` mysteriously misses
rows. `order.status = OrderStatus.PENDING` is a typo that fails at
import time or with IDE autocomplete catching it before you even run
the code. SQLAlchemy stores these as their string `.value` in the DB,
so the schema stays human-readable in a DB browser.
"""

import enum


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class UserRole(str, enum.Enum):
    CUSTOMER = "customer"
    ADMIN = "admin"
