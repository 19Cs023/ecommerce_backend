from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.crud.user import user as user_crud
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserRead, UserUpdate

router = APIRouter()


@router.get("/me", response_model=UserRead)
def read_own_profile(current_user: User = Depends(get_current_active_user)):
    # No `id` path parameter here on purpose -- "/users/me" reads from
    # the JWT via the dependency, so there's no way to accidentally (or
    # maliciously) request `/users/42` and see someone else's profile.
    return current_user


@router.patch("/me", response_model=UserRead)
def update_own_profile(
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return user_crud.update(db, db_obj=current_user, obj_in=user_in)
