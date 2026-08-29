def test_register_and_login(client):
    register_resp = client.post(
        "/api/v1/auth/register",
        json={"email": "alice@example.com", "full_name": "Alice", "password": "supersecret123"},
    )
    assert register_resp.status_code == 201
    body = register_resp.json()
    # The critical negative assertion: the password hash must NEVER
    # appear in an API response, under any field name.
    assert "password" not in body
    assert "hashed_password" not in body

    login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": "alice@example.com", "password": "supersecret123"},
    )
    assert login_resp.status_code == 200
    tokens = login_resp.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens


def test_login_wrong_password_fails(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "bob@example.com", "full_name": "Bob", "password": "correcthorse123"},
    )
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "bob@example.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


def test_duplicate_email_registration_rejected(client):
    payload = {"email": "carol@example.com", "full_name": "Carol", "password": "password123"}
    first = client.post("/api/v1/auth/register", json=payload)
    second = client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201
    assert second.status_code == 400


def test_protected_route_requires_token(client):
    resp = client.get("/api/v1/users/me")
    assert resp.status_code == 401
