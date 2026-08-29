"""
The declarative Base every model inherits from.

WHY A SEPARATE FILE:
Alembic (migrations) needs to import `Base.metadata` to autogenerate
migrations by diffing your models against the DB schema. If Base lived
inside a file that also imported the DB engine/session (circular-import
risk) or pulled in unrelated app code, Alembic's env.py would end up
importing far more than it needs. Keeping Base isolated avoids that.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """All ORM models inherit from this. Gives them `.metadata`,
    `.__tablename__` conventions, and SQLAlchemy 2.0's typed Mapped[] support."""
    pass
