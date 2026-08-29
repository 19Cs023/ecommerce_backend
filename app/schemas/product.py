"""
Product schemas.

NOTE ON price_cents vs price:
The DB and internal logic speak in integer cents (see models/product.py
for why). The API, however, is a public contract -- and forcing every
client to divide by 100 is bad ergonomics and a source of bugs on
their end too. So `ProductRead` exposes a computed `price` (float,
dollars) via a `@field_validator`-free approach: a plain Python
property-like computed field. This is the boundary where the
"internal representation vs external representation" split happens --
a pattern worth reusing anytime your storage format and API format
diverge for good technical reasons.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=280)
    description: Optional[str] = None
    sku: str = Field(min_length=1, max_length=64)
    category_id: Optional[int] = None


class ProductCreate(ProductBase):
    price_cents: int = Field(gt=0, description="Price in cents, e.g. 1999 for $19.99")
    stock_quantity: int = Field(ge=0, default=0)


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    price_cents: Optional[int] = Field(default=None, gt=0)
    stock_quantity: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None
    category_id: Optional[int] = None


class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    price_cents: int
    stock_quantity: int
    is_active: bool
    created_at: datetime

    @computed_field
    @property
    def price(self) -> float:
        return round(self.price_cents / 100, 2)


class ProductListResponse(BaseModel):
    """
    WHY WRAP LISTS IN AN ENVELOPE OBJECT INSTEAD OF RETURNING A BARE
    JSON ARRAY:
    A bare array `[...]` has no room to attach pagination metadata
    later (total count, next-page cursor) without a breaking change to
    the response shape. An envelope `{"items": [...], "total": N}` can
    grow new fields non-destructively. Cheap insurance to take from day one.
    """
    items: list[ProductRead]
    total: int
    page: int
    page_size: int
