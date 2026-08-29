from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_user
from app.crud.category import category as category_crud
from app.db.session import get_db
from app.schemas.category import CategoryCreate, CategoryRead

router = APIRouter()


@router.get("/", response_model=list[CategoryRead])
def list_categories(db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
    return category_crud.get_multi(db, skip=skip, limit=limit)


@router.post("/", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    category_in: CategoryCreate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin_user),  # underscore: we need the auth CHECK, not the value
):
    if category_crud.get_by_slug(db, slug=category_in.slug):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slug already in use")
    return category_crud.create(db, obj_in=category_in)
