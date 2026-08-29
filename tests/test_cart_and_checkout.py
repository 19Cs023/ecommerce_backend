from app.crud.category import category as category_crud
from app.crud.product import product as product_crud
from app.crud.user import user as user_crud
from app.schemas.category import CategoryCreate
from app.schemas.product import ProductCreate
from app.schemas.user import UserCreate


def _register_and_login(client, email="shopper@example.com", password="password123"):
    client.post("/api/v1/auth/register", json={"email": email, "full_name": "Shopper", "password": password})
    login = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _make_product(db_session, stock=5, price_cents=1500):
    cat = category_crud.create(db_session, obj_in=CategoryCreate(name="Books", slug="books"))
    return product_crud.create(
        db_session,
        obj_in=ProductCreate(
            name="Test Widget",
            slug="test-widget",
            sku="SKU-001",
            price_cents=price_cents,
            stock_quantity=stock,
            category_id=cat.id,
        ),
    )


def test_add_to_cart_and_checkout(client, db_session):
    headers = _register_and_login(client)
    product = _make_product(db_session, stock=10, price_cents=2000)

    add_resp = client.post(
        "/api/v1/cart/items", json={"product_id": product.id, "quantity": 3}, headers=headers
    )
    assert add_resp.status_code == 201
    cart = add_resp.json()
    assert len(cart["items"]) == 1
    assert cart["items"][0]["quantity"] == 3

    checkout_resp = client.post(
        "/api/v1/orders/checkout", json={"shipping_address": "123 Main St"}, headers=headers
    )
    assert checkout_resp.status_code == 201
    order = checkout_resp.json()
    assert order["status"] == "paid"
    assert order["total_cents"] == 3 * 2000
    assert order["items"][0]["product_name"] == "Test Widget"

    # Stock must have been decremented by exactly the quantity purchased.
    db_session.refresh(product)
    assert product.stock_quantity == 7

    # Cart must be emptied after a successful checkout.
    cart_after = client.get("/api/v1/cart/", headers=headers).json()
    assert cart_after["items"] == []


def test_checkout_fails_with_insufficient_stock(client, db_session):
    headers = _register_and_login(client)
    product = _make_product(db_session, stock=2)

    client.post("/api/v1/cart/items", json={"product_id": product.id, "quantity": 2}, headers=headers)

    # Simulate someone else buying stock out from under this cart between
    # "add to cart" and "checkout" -- exactly the race the row lock in
    # crud/product.py's decrement_stock guards against in a real concurrent
    # scenario. Here we just mutate directly to prove checkout re-validates
    # stock at commit time instead of trusting the cart's earlier snapshot.
    product.stock_quantity = 0
    db_session.add(product)
    db_session.commit()

    resp = client.post("/api/v1/orders/checkout", json={"shipping_address": "1 Elm St"}, headers=headers)
    assert resp.status_code == 409


def test_checkout_empty_cart_rejected(client):
    headers = _register_and_login(client)
    resp = client.post("/api/v1/orders/checkout", json={"shipping_address": "1 Elm St"}, headers=headers)
    assert resp.status_code == 400


def test_cannot_view_another_users_order(client, db_session):
    headers_a = _register_and_login(client, email="userA@example.com")
    product = _make_product(db_session, stock=5)
    client.post("/api/v1/cart/items", json={"product_id": product.id, "quantity": 1}, headers=headers_a)
    order = client.post(
        "/api/v1/orders/checkout", json={"shipping_address": "A's house"}, headers=headers_a
    ).json()

    headers_b = _register_and_login(client, email="userB@example.com")
    resp = client.get(f"/api/v1/orders/{order['id']}", headers=headers_b)
    assert resp.status_code == 404  # not 403 -- see endpoint comment on why
