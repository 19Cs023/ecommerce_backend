"""
Product endpoints.

NOTE ON ROUTE ORDERING:
`/products/search` must be declared BEFORE `/products/{product_id}` in
this file. FastAPI (like most routers) matches routes in registration
order, and `{product_id}` would otherwise greedily match the literal
string "search" as if it were an ID, returning a confusing 422 instead
of ever reaching the search handler. This is a common gotcha worth
remembering for any path-based router, not just FastAPI.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_user
from app.crud.product import product as product_crud
from app.db.session import get_db
from app.schemas.product import ProductCreate, ProductListResponse, ProductRead, ProductUpdate

router = APIRouter()


@router.get("/search", response_model=ProductListResponse)
def search_products(
    db: Session = Depends(get_db),
    q: Optional[str] = None,
    category_id: Optional[int] = None,
    min_price_cents: Optional[int] = None,
    max_price_cents: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
):
    skip = (page - 1) * page_size
    rows, total = product_crud.search(
        db,
        q=q,
        category_id=category_id,
        min_price_cents=min_price_cents,
        max_price_cents=max_price_cents,
        skip=skip,
        limit=page_size,
    )
    return ProductListResponse(items=rows, total=total, page=page, page_size=page_size)


@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = product_crud.get(db, id=product_id)
    if product is None or not product.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@router.post("/", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(
    product_in: ProductCreate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin_user),
):
    if product_crud.get_by_sku(db, sku=product_in.sku):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SKU already exists")
    return product_crud.create(db, obj_in=product_in)


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int,
    product_in: ProductUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin_user),
):
    product = product_crud.get(db, id=product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product_crud.update(db, db_obj=product, obj_in=product_in)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin_user),
):
    """
    A 'delete' here really means `is_active = False` via the update
    path would be the safer real-world choice (soft delete, so past
    OrderItems referencing this product via FK don't break) -- but to
    show the pattern plainly, this uses a hard delete. In production,
    prefer: `product_crud.update(db, db_obj=product, obj_in=ProductUpdate(is_active=False))`.
    """
    product = product_crud.remove(db, id=product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
