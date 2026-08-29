from typing import Optional

from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.category import Category
from app.schemas.category import CategoryCreate


class CRUDCategory(CRUDBase[Category, CategoryCreate, CategoryCreate]):
    def get_by_slug(self, db: Session, *, slug: str) -> Optional[Category]:
        return db.query(Category).filter(Category.slug == slug).first()


category = CRUDCategory(Category)
