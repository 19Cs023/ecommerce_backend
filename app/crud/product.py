from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate


class CRUDProduct(CRUDBase[Product, ProductCreate, ProductUpdate]):
    def get_by_sku(self, db: Session, *, sku: str) -> Optional[Product]:
        return db.query(Product).filter(Product.sku == sku).first()

    def search(
        self,
        db: Session,
        *,
        q: Optional[str] = None,
        category_id: Optional[int] = None,
        min_price_cents: Optional[int] = None,
        max_price_cents: Optional[int] = None,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Product], int]:
        """
        Builds the WHERE clause incrementally based on which filters were
        actually provided, rather than writing a separate query for every
        combination of filters. Returns (rows, total_count) as a pair
        because paginated endpoints need both -- the page of results,
        and the total count for the client to compute "page 3 of 12".

        Note: the count query re-runs the same filters but WITHOUT
        offset/limit. This is two round-trips to the DB where one clever
        window-function query could do it in one -- a deliberate
        readability-over-cleverness trade-off. Optimize only if this
        endpoint's query volume actually makes it a bottleneck.
        """
        stmt = select(Product)
        if active_only:
            stmt = stmt.where(Product.is_active.is_(True))
        if q:
            like_pattern = f"%{q}%"
            stmt = stmt.where(or_(Product.name.ilike(like_pattern), Product.description.ilike(like_pattern)))
        if category_id is not None:
            stmt = stmt.where(Product.category_id == category_id)
        if min_price_cents is not None:
            stmt = stmt.where(Product.price_cents >= min_price_cents)
        if max_price_cents is not None:
            stmt = stmt.where(Product.price_cents <= max_price_cents)

        total = len(db.execute(stmt).all())
        rows = db.execute(stmt.offset(skip).limit(limit)).scalars().all()
        return list(rows), total

    def decrement_stock(self, db: Session, *, product_id: int, quantity: int) -> Optional[Product]:
        """
        Used exclusively by the checkout flow. See services/order_service.py
        for why this uses `with_for_update()` (SELECT ... FOR UPDATE) --
        the short version: without a row lock, two concurrent checkouts
        for the last item in stock can both read stock_quantity=1, both
        decide "there's enough", and both succeed -- overselling by one
        unit. The lock forces the second transaction to wait until the
        first commits, so it re-reads the now-correct (lower) quantity.
        """
        product = (
            db.query(Product)
            .filter(Product.id == product_id)
            .with_for_update()
            .first()
        )
        if product is None or product.stock_quantity < quantity:
            return None
        product.stock_quantity -= quantity
        db.add(product)
        return product


product = CRUDProduct(Product)
