"""
Tenant-isolation tests for collections — the single most important
test group in v0.2.

The invariant under test: knowing another user's collection id must
never be sufficient to read, modify, or delete it. Every cross-tenant
attempt below must return 404 (not 403 — a 403 would itself leak that
the id is valid; see app/collections/router.py).
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


def _register_and_login(email: str, password: str = "correcthorsebattery") -> TestClient:
    """
    Each caller gets its own TestClient instance so its cookie jar
    (and therefore its session) is completely independent — this is
    what lets the same test process represent two different users at
    once without their sessions bleeding into each other.
    """
    session = TestClient(app)
    register = session.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert register.status_code == 201, register.text
    login = session.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return session


@pytest.fixture
def user_a() -> TestClient:
    return _register_and_login(f"tenant-a-{uuid.uuid4().hex[:8]}@example.com")


@pytest.fixture
def user_b() -> TestClient:
    return _register_and_login(f"tenant-b-{uuid.uuid4().hex[:8]}@example.com")


def _create_collection(session: TestClient, name: str) -> str:
    response = session.post("/api/v1/collections", json={"name": name})
    assert response.status_code == 201, response.text
    id_: str = response.json()["id"]
    return id_


def test_owner_can_read_own_collection(user_a: TestClient) -> None:
    collection_id = _create_collection(user_a, "A's collection")
    response = user_a.get(f"/api/v1/collections/{collection_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "A's collection"


def test_user_a_cannot_read_user_b_collection(user_a: TestClient, user_b: TestClient) -> None:
    collection_b_id = _create_collection(user_b, "B's private collection")
    response = user_a.get(f"/api/v1/collections/{collection_b_id}")
    assert response.status_code == 404


def test_user_b_cannot_read_user_a_collection(user_a: TestClient, user_b: TestClient) -> None:
    collection_a_id = _create_collection(user_a, "A's private collection")
    response = user_b.get(f"/api/v1/collections/{collection_a_id}")
    assert response.status_code == 404


def test_anonymous_cannot_read_any_collection(user_a: TestClient) -> None:
    collection_id = _create_collection(user_a, "A's collection")
    anonymous = TestClient(app)
    response = anonymous.get(f"/api/v1/collections/{collection_id}")
    assert response.status_code == 401


def test_user_a_cannot_update_user_b_collection(user_a: TestClient, user_b: TestClient) -> None:
    collection_b_id = _create_collection(user_b, "B's collection")
    response = user_a.patch(
        f"/api/v1/collections/{collection_b_id}", json={"name": "hijacked"}
    )
    assert response.status_code == 404

    # And B's collection must be genuinely untouched, not just "the
    # write returned an error" — verify from B's own session.
    still_intact = user_b.get(f"/api/v1/collections/{collection_b_id}")
    assert still_intact.json()["name"] == "B's collection"


def test_user_a_cannot_delete_user_b_collection(user_a: TestClient, user_b: TestClient) -> None:
    collection_b_id = _create_collection(user_b, "B's collection")
    response = user_a.delete(f"/api/v1/collections/{collection_b_id}")
    assert response.status_code == 404

    still_exists = user_b.get(f"/api/v1/collections/{collection_b_id}")
    assert still_exists.status_code == 200


def test_list_collections_only_returns_own(user_a: TestClient, user_b: TestClient) -> None:
    _create_collection(user_a, "A1")
    _create_collection(user_a, "A2")
    _create_collection(user_b, "B1")

    a_listing = user_a.get("/api/v1/collections").json()
    b_listing = user_b.get("/api/v1/collections").json()

    assert {c["name"] for c in a_listing} == {"A1", "A2"}
    assert {c["name"] for c in b_listing} == {"B1"}


def test_cross_tenant_and_ownership_404_not_403(user_a: TestClient, user_b: TestClient) -> None:
    """
    Explicitly pins the 404-not-403 decision: a real resource owned by
    someone else and a nonexistent id must be indistinguishable to the
    caller, so ids can't be enumerated by probing for 403 vs 404.
    """
    collection_b_id = _create_collection(user_b, "B's collection")
    nonexistent_id = str(uuid.uuid4())

    real_but_not_mine = user_a.get(f"/api/v1/collections/{collection_b_id}")
    truly_nonexistent = user_a.get(f"/api/v1/collections/{nonexistent_id}")

    assert real_but_not_mine.status_code == truly_nonexistent.status_code == 404
    assert real_but_not_mine.json() == truly_nonexistent.json()
