"""
Aggregates every endpoint router under one `api_router`.

WHY THIS INDIRECTION LAYER EXISTS:
`main.py` includes exactly ONE router (`api_router`) at the versioned
prefix `/api/v1`. If you need a `/api/v2` someday with different
behavior for some resources, you build a parallel `app/api/v2/` package
and mount both -- old clients keep working against v1 unmodified while
new clients opt into v2. That's only possible because `main.py` never
hardcoded knowledge of individual endpoint modules; it only knows
about "the v1 router" as a black box.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, cart, categories, orders, products, users

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(categories.router, prefix="/categories", tags=["categories"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(cart.router, prefix="/cart", tags=["cart"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
