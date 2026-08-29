from pydantic import BaseModel, ConfigDict, Field

from app.schemas.product import ProductRead


class CartItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0, default=1)


class CartItemUpdate(BaseModel):
    quantity: int = Field(gt=0)


class CartItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quantity: int
    product: ProductRead

    @property
    def line_total_cents(self) -> int:
        return self.product.price_cents * self.quantity


class CartRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    items: list[CartItemRead]

    @property
    def total_cents(self) -> int:
        return sum(item.product.price_cents * item.quantity for item in self.items)
