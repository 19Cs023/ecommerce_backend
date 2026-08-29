from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_current_admin_user
from app.crud import order as order_crud
from app.db.session import get_db
from app.models.user import User
from app.schemas.order import OrderCreate, OrderRead, OrderStatusUpdate
from app.services.order_service import EmptyCartError, InsufficientStockError, checkout

router = APIRouter()


@router.post("/checkout", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def checkout_cart(
    order_in: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Thin route handler: all the actual logic lives in
    `services/order_service.checkout`. The handler's only job is to
    translate domain exceptions into the right HTTP status codes --
    that translation is an HTTP concern, so it belongs here, not in the
    service (which should stay framework-agnostic and just as callable
    from a CLI script or background job as from a route).
    """
    try:
        return checkout(db, user_id=current_user.id, shipping_address=order_in.shipping_address)
    except EmptyCartError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except InsufficientStockError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/", response_model=list[OrderRead])
def list_my_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = 0,
    limit: int = 20,
):
    return order_crud.get_orders_for_user(db, user_id=current_user.id, skip=skip, limit=limit)


@router.get("/{order_id}", response_model=OrderRead)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order = order_crud.get_order(db, order_id=order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    # Ownership check: this is what stops user A from reading user B's
    # order just by incrementing the `order_id` in the URL (a classic
    # "Insecure Direct Object Reference" / IDOR vulnerability). Admins
    # bypass it via the separate endpoint below instead of a role check
    # bolted onto every read.
    if order.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


@router.patch("/{order_id}/status", response_model=OrderRead)
def update_order_status(
    order_id: int,
    status_in: OrderStatusUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin_user),
):
    order = order_crud.get_order(db, order_id=order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    order.status = status_in.status
    db.add(order)
    db.commit()
    db.refresh(order)
    return order
