"""
Generic CRUD base class -- the "repository pattern".

WHY THIS EXISTS:
Every model needs get/get_multi/create/update/delete. Writing that
boilerplate five times (once per model) means five places to fix a
bug and five places that can subtly drift apart. Instead, we write it
ONCE as a generic class parameterized over the model type, and each
concrete CRUD class (see crud/product.py etc.) inherits it and adds
only the queries that are actually specific to that model (e.g.
"get_by_sku", "search_by_name").

This is also the layer that keeps SQLAlchemy Session/Query objects OUT
of your route handlers and service layer. Route handlers call
`crud.product.get(db, id)`; they never write raw `db.query(...)`
themselves. That indirection is what lets you swap SQLAlchemy for a
different ORM later by rewriting this layer only, or write endpoint
tests that mock the CRUD layer without touching a real database.

Generic[ModelType, CreateSchemaType, UpdateSchemaType] is Python's way
of writing "this class works for any model as long as you tell it
which one" -- mypy/IDEs will correctly infer `CRUDProduct.get()` returns
`Optional[Product]`, not `Optional[Base]`.
"""

from typing import Any, Generic, Optional, Type, TypeVar

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.base_class import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        return db.query(self.model).filter(self.model.id == id).first()

    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> list[ModelType]:
        return db.query(self.model).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        obj_data = obj_in.model_dump()
        db_obj = self.model(**obj_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)  # pulls back DB-generated fields: id, server_default timestamps, etc.
        return db_obj

    def update(self, db: Session, *, db_obj: ModelType, obj_in: UpdateSchemaType) -> ModelType:
        # exclude_unset=True is the key to correct PATCH semantics:
        # a field the client didn't send should not overwrite existing
        # data with None. Only fields explicitly present in the request
        # body get applied.
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: Any) -> Optional[ModelType]:
        obj = self.get(db, id)
        if obj is not None:
            db.delete(obj)
            db.commit()
        return obj
