import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def authed_client() -> TestClient:
    session = TestClient(app)
    email = f"crud-{uuid.uuid4().hex[:8]}@example.com"
    session.post("/api/v1/auth/register", json={"email": email, "password": "correcthorsebattery"})
    session.post("/api/v1/auth/login", json={"email": email, "password": "correcthorsebattery"})
    return session


def test_create_and_get_collection(authed_client: TestClient) -> None:
    create = authed_client.post(
        "/api/v1/collections", json={"name": "Research", "description": "Papers"}
    )
    assert create.status_code == 201
    collection_id = create.json()["id"]

    get = authed_client.get(f"/api/v1/collections/{collection_id}")
    assert get.status_code == 200
    assert get.json()["name"] == "Research"
    assert get.json()["description"] == "Papers"


def test_create_collection_requires_name(authed_client: TestClient) -> None:
    response = authed_client.post("/api/v1/collections", json={"name": ""})
    assert response.status_code == 422


def test_patch_updates_only_supplied_fields(authed_client: TestClient) -> None:
    create = authed_client.post(
        "/api/v1/collections", json={"name": "Original", "description": "Keep me"}
    )
    collection_id = create.json()["id"]

    patch = authed_client.patch(f"/api/v1/collections/{collection_id}", json={"name": "Renamed"})
    assert patch.status_code == 200
    assert patch.json()["name"] == "Renamed"
    assert patch.json()["description"] == "Keep me"


def test_delete_removes_collection(authed_client: TestClient) -> None:
    create = authed_client.post("/api/v1/collections", json={"name": "Temporary"})
    collection_id = create.json()["id"]

    delete = authed_client.delete(f"/api/v1/collections/{collection_id}")
    assert delete.status_code == 204

    get_after_delete = authed_client.get(f"/api/v1/collections/{collection_id}")
    assert get_after_delete.status_code == 404


def test_collections_require_authentication() -> None:
    anonymous = TestClient(app)
    assert anonymous.get("/api/v1/collections").status_code == 401
    assert anonymous.post("/api/v1/collections", json={"name": "x"}).status_code == 401
