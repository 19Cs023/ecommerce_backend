"""
Order/checkout service -- the "business logic" layer.

WHY A SEPARATE SERVICE LAYER (instead of putting this in the route
handler, or in CRUD):
Checkout isn't a single-table operation -- it touches Cart, CartItem,
Product (stock), Order, and OrderItem, and it has rules that don't
belong in any one model's CRUD class ("fail the whole checkout if any
item is out of stock", "snapshot prices", "empty the cart on success").
Putting this logic in the route handler works until you need to
trigger the same checkout from two places (a web route AND a
scheduled "retry failed payment" job, say) -- then you're copy-pasting
business rules. A service function is callable from anywhere and is
independently unit-testable without spinning up FastAPI.

WHY THE WHOLE THING RUNS IN ONE DB TRANSACTION:
If stock decremented successfully for item 1 but then item 2 turns out
to be out of stock, the entire order must fail -- including undoing
item 1's stock decrement. This function does exactly one `db.commit()`
at the very end; every failure path raises before that point, and
FastAPI's session-per-request `get_db` dependency will have opened the
session with `autocommit=False`, so an uncommitted session is simply
discarded (rolled back) when the request ends in an exception. This
is the classic "all or nothing" transaction guarantee.
"""

from sqlalchemy.orm import Session

from app.crud import cart as cart_crud
from app.crud import product as product_crud
from app.models.enums import OrderStatus
from app.models.order import Order, OrderItem


class InsufficientStockError(Exception):
    def __init__(self, product_name: str, requested: int, available: int):
        self.product_name = product_name
        self.requested = requested
        self.available = available
        super().__init__(f"Insufficient stock for '{product_name}': requested {requested}, have {available}")


class EmptyCartError(Exception):
    pass


def checkout(db: Session, *, user_id: int, shipping_address: str) -> Order:
    cart = cart_crud.get_cart_for_user(db, user_id=user_id)
    if cart is None or not cart.items:
        raise EmptyCartError("Cannot check out an empty cart.")

    order = Order(user_id=user_id, status=OrderStatus.PENDING, total_cents=0, shipping_address=shipping_address)
    db.add(order)
    db.flush()  # gets order.id assigned without committing, so OrderItems can reference it

    total_cents = 0
    for cart_item in cart.items:
        # `decrement_stock` takes a row lock (SELECT ... FOR UPDATE) on
        # the product row -- see crud/product.py for why this matters
        # under concurrent checkouts.
        product = product_crud.decrement_stock(
            db, product_id=cart_item.product_id, quantity=cart_item.quantity
        )
        if product is None:
            # Raising here aborts the whole function before db.commit()
            # is ever called, so any stock already decremented in this
            # loop for earlier items gets rolled back too (see module
            # docstring). The caller's exception handler is responsible
            # for actually calling db.rollback() -- see the API endpoint.
            original_product = cart_item.product
            raise InsufficientStockError(
                product_name=original_product.name,
                requested=cart_item.quantity,
                available=original_product.stock_quantity,
            )

        # Snapshot name + price NOW, at purchase time -- see
        # models/order.py docstring for why this must never be a live
        # reference to product.price_cents.
        order_item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            product_name=product.name,
            unit_price_cents=product.price_cents,
            quantity=cart_item.quantity,
        )
        db.add(order_item)
        total_cents += product.price_cents * cart_item.quantity

    order.total_cents = total_cents
    order.status = OrderStatus.PAID  # simplified: real systems set PENDING until a payment webhook confirms

    cart_crud.clear_cart(db, cart=cart)

    db.commit()
    db.refresh(order)
    return order
