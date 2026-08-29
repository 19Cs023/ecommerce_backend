from typing import Optional

from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.crud.base import CRUDBase
from app.models.cart import Cart
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        """
        Overrides the generic `create` because we must NEVER pass the
        plaintext password straight into `User(**obj_in.model_dump())`
        -- that would try to set a nonexistent `password` attribute AND
        (if it worked) store plaintext. We hash first, then construct
        the ORM object with the hash under its correct field name.

        Also eagerly creates the user's Cart in the same transaction:
        every user needs exactly one cart, and creating it lazily on
        first "add to cart" call would mean every other endpoint that
        expects `user.cart` to exist has to handle the "no cart yet"
        case defensively. Guaranteeing it here removes that whole class
        of null-check from the rest of the codebase.
        """
        db_obj = User(
            email=obj_in.email,
            full_name=obj_in.full_name,
            hashed_password=hash_password(obj_in.password),
        )
        db.add(db_obj)
        db.flush()  # assigns db_obj.id without committing yet, so we can attach the cart to it
        db.add(Cart(user_id=db_obj.id))
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: User, obj_in: UserUpdate) -> User:
        update_data = obj_in.model_dump(exclude_unset=True)
        if "password" in update_data:
            update_data["hashed_password"] = hash_password(update_data.pop("password"))
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def authenticate(self, db: Session, *, email: str, password: str) -> Optional[User]:
        user = self.get_by_email(db, email=email)
        if user is None or not verify_password(password, user.hashed_password):
            return None
        return user


user = CRUDUser(User)
