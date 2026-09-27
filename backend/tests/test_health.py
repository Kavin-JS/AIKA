from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db
from app.main import app

client = TestClient(app)


def test_liveness_ok() -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


class _FakeHealthySession:
    def execute(self, *args: object, **kwargs: object) -> None:
        return None


class _FakeUnhealthySession:
    def execute(self, *args: object, **kwargs: object) -> None:
        raise SQLAlchemyError("simulated connection failure")


def _yield_healthy_session() -> Generator[_FakeHealthySession, None, None]:
    yield _FakeHealthySession()


def _yield_unhealthy_session() -> Generator[_FakeUnhealthySession, None, None]:
    yield _FakeUnhealthySession()


@pytest.fixture
def override_db_healthy() -> Generator[None, None, None]:
    # Must be an actual generator function (not a lambda returning an
    # iterator): FastAPI's dependency system special-cases
    # `inspect.isgeneratorfunction` to run yield-based dependencies as
    # context managers. A lambda wrapping `iter(...)` would not be
    # recognized as such and would inject the iterator itself as `db`
    # instead of the yielded session.
    app.dependency_overrides[get_db] = _yield_healthy_session
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def override_db_unhealthy() -> Generator[None, None, None]:
    app.dependency_overrides[get_db] = _yield_unhealthy_session
    yield
    app.dependency_overrides.pop(get_db, None)


def test_readiness_reports_ok_when_database_is_reachable(
    override_db_healthy: None,
) -> None:
    """
    Deterministic, DB-independent unit test: replaces `get_db` with a
    fake session that succeeds, and asserts the endpoint reports 200.
    This can fail if the readiness logic regresses (e.g. always
    returning 503) regardless of whether a real Postgres happens to be
    reachable in the environment the test runs in.
    """
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "reachable"}


def test_readiness_reports_unavailable_when_database_is_unreachable(
    override_db_unhealthy: None,
) -> None:
    """
    Mirror of the test above: replaces `get_db` with a fake session that
    raises `SQLAlchemyError`, and asserts the endpoint reports 503. This
    can fail if the endpoint stops correctly catching/reporting DB
    failures, regardless of the real database's actual state.
    """
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "unreachable"}
