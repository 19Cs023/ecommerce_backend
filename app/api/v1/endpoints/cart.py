from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.crud import cart as cart_crud
from app.crud.product import product as product_crud
from app.db.session import get_db
from app.models.user import User
from app.schemas.cart import CartItemCreate, CartItemUpdate, CartRead

router = APIRouter()


@router.get("/", response_model=CartRead)
def get_my_cart(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    # `current_user.cart` is guaranteed to exist -- see crud/user.py's
    # `create()`, which creates the Cart row in the same transaction as
    # the User row. No None-check needed here.
    return current_user.cart


@router.post("/items", response_model=CartRead, status_code=status.HTTP_201_CREATED)
def add_to_cart(
    item_in: CartItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    product = product_crud.get(db, id=item_in.product_id)
    if product is None or not product.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if product.stock_quantity < item_in.quantity:
        # Checked here for a fast, friendly error -- but this is NOT the
        # authoritative check. Stock can change between "add to cart"
        # and "checkout", so the real guard (with a row lock) lives in
        # services/order_service.py. Never trust a check this far from
        # the actual write.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not enough stock available")

    cart_crud.add_item(db, cart_id=current_user.cart.id, product_id=product.id, quantity=item_in.quantity)
    db.refresh(current_user.cart)
    return current_user.cart


@router.patch("/items/{product_id}", response_model=CartRead)
def update_cart_item(
    product_id: int,
    item_in: CartItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    item = cart_crud.get_cart_item(db, cart_id=current_user.cart.id, product_id=product_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not in cart")
    cart_crud.update_item_quantity(db, item=item, quantity=item_in.quantity)
    db.refresh(current_user.cart)
    return current_user.cart


@router.delete("/items/{product_id}", response_model=CartRead)
def remove_from_cart(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    item = cart_crud.get_cart_item(db, cart_id=current_user.cart.id, product_id=product_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not in cart")
    cart_crud.remove_item(db, item=item)
    db.refresh(current_user.cart)
    return current_user.cart
