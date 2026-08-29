from sqlalchemy.orm import Session

from app.models.order import Order


def get_orders_for_user(db: Session, *, user_id: int, skip: int = 0, limit: int = 20) -> list[Order]:
    return (
        db.query(Order)
        .filter(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_order(db: Session, *, order_id: int) -> Order | None:
    return db.query(Order).filter(Order.id == order_id).first()
