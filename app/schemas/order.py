from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import OrderStatus


class OrderCreate(BaseModel):
    """
    Deliberately does NOT accept a list of items from the client.
    Orders are created FROM the user's current cart server-side (see
    services/order_service.py) -- trusting a client-supplied list of
    "product_id + price" for a financial transaction is a classic way
    to let someone check out a $999 item for $1 by editing a request
    payload. Only the shipping address is client input here; prices
    and quantities are derived from server-side state.
    """
    shipping_address: str = Field(min_length=1, max_length=500)


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_name: str
    unit_price_cents: int
    quantity: int

    @property
    def line_total_cents(self) -> int:
        return self.unit_price_cents * self.quantity


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: OrderStatus
    total_cents: int
    shipping_address: str
    created_at: datetime
    items: list[OrderItemRead]


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
