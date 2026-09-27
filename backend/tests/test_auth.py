from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _unique_email(tag: str) -> str:
    import uuid

    return f"{tag}-{uuid.uuid4().hex[:8]}@example.com"


def test_register_creates_user() -> None:
    email = _unique_email("register")
    response = client.post(
        "/api/v1/auth/register", json={"email": email, "password": "correcthorsebattery"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == email
    assert "id" in body
    assert "password" not in body
    assert "password_hash" not in body


def test_register_duplicate_email_rejected() -> None:
    email = _unique_email("dup")
    payload = {"email": email, "password": "correcthorsebattery"}
    first = client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201

    second = client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 409


def test_register_rejects_short_password() -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": _unique_email("short"), "password": "short"},
    )
    assert response.status_code == 422


def test_login_succeeds_with_correct_credentials() -> None:
    email = _unique_email("login")
    password = "correcthorsebattery"
    client.post("/api/v1/auth/register", json={"email": email, "password": password})

    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    assert response.json()["email"] == email
    assert "access_token" in response.cookies


def test_login_wrong_password_and_unknown_email_are_indistinguishable() -> None:
    """
    The core anti-enumeration property: an attacker must not be able to
    tell "wrong password" apart from "no such account" via status code
    or response body.
    """
    email = _unique_email("wrongpw")
    password = "correcthorsebattery"
    client.post("/api/v1/auth/register", json={"email": email, "password": password})

    wrong_password = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "definitely-wrong"}
    )
    unknown_email = client.post(
        "/api/v1/auth/login",
        json={"email": _unique_email("nobody"), "password": "whatever123"},
    )

    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_me_requires_authentication() -> None:
    anonymous_client = TestClient(app)
    response = anonymous_client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_returns_current_user_when_authenticated() -> None:
    email = _unique_email("me")
    password = "correcthorsebattery"
    authed_client = TestClient(app)
    authed_client.post("/api/v1/auth/register", json={"email": email, "password": password})
    authed_client.post("/api/v1/auth/login", json={"email": email, "password": password})

    response = authed_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == email


def test_logout_clears_auth_cookie() -> None:
    """
    Logout clears the browser's authentication cookie — it does not
    revoke the underlying JWT. A previously issued access token remains
    cryptographically valid until it expires; if it had been captured
    elsewhere (e.g. copied out of the cookie jar) before logout, it
    would still work until expiry. v0.2 has no revocation mechanism
    (no token blocklist, no server-side session store) by deliberate
    design — see docs/architecture.md. What this test actually proves:
    the client that called /logout can no longer authenticate using its
    (now-cleared) cookie.
    """
    email = _unique_email("logout")
    password = "correcthorsebattery"
    authed_client = TestClient(app)
    authed_client.post("/api/v1/auth/register", json={"email": email, "password": password})
    authed_client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert authed_client.get("/api/v1/auth/me").status_code == 200

    logout_response = authed_client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 204

    assert authed_client.get("/api/v1/auth/me").status_code == 401
