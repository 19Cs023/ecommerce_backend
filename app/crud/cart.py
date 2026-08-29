from typing import Optional

from sqlalchemy.orm import Session

from app.models.cart import Cart, CartItem


def get_cart_for_user(db: Session, *, user_id: int) -> Optional[Cart]:
    return db.query(Cart).filter(Cart.user_id == user_id).first()


def get_cart_item(db: Session, *, cart_id: int, product_id: int) -> Optional[CartItem]:
    return (
        db.query(CartItem)
        .filter(CartItem.cart_id == cart_id, CartItem.product_id == product_id)
        .first()
    )


def add_item(db: Session, *, cart_id: int, product_id: int, quantity: int) -> CartItem:
    """
    Upsert semantics: adding a product already in the cart increments
    its quantity instead of creating a duplicate row. This is what the
    `UniqueConstraint("cart_id", "product_id")` on CartItem (see
    models/cart.py) exists to guarantee at the DB level even if this
    application-level check were ever bypassed.
    """
    existing = get_cart_item(db, cart_id=cart_id, product_id=product_id)
    if existing:
        existing.quantity += quantity
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    item = CartItem(cart_id=cart_id, product_id=product_id, quantity=quantity)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_item_quantity(db: Session, *, item: CartItem, quantity: int) -> CartItem:
    item.quantity = quantity
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def remove_item(db: Session, *, item: CartItem) -> None:
    db.delete(item)
    db.commit()


def clear_cart(db: Session, *, cart: Cart) -> None:
    for item in list(cart.items):
        db.delete(item)
    db.commit()
