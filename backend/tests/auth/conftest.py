"""
Fixtures para testes do Auth Service.
Usa TestClient síncrono (sem banco real) para testes unitários com mocks.
"""

import pytest
import fakeredis.aioredis as aioredis
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from shared.shared.auth.dependencies import UserClaims, get_current_user
from shared.shared.config import SharedSettings, get_shared_settings
from shared.shared.db.session import get_db
from shared.shared.redis.client import get_redis

from services.auth.config import AuthSettings, get_auth_settings
from services.auth.main import create_app


def make_auth_settings(rsa_keys: dict) -> AuthSettings:
    return AuthSettings(
        jwt_public_key=rsa_keys["public"],
        jwt_private_key=rsa_keys["private"],
        database_url="postgresql+asyncpg://x:x@localhost/x",
    )


def make_client(
    rsa_keys: dict,
    current_user: UserClaims | None = None,
    mock_db: AsyncMock | None = None,
    mock_redis=None,
) -> TestClient:
    app = create_app()
    settings = make_auth_settings(rsa_keys)
    app.dependency_overrides[get_shared_settings] = lambda: settings
    app.dependency_overrides[get_auth_settings] = lambda: settings

    if mock_db is not None:
        app.dependency_overrides[get_db] = lambda: mock_db

    if mock_redis is not None:
        app.dependency_overrides[get_redis] = lambda: mock_redis

    if current_user is not None:
        app.dependency_overrides[get_current_user] = lambda: current_user

    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def fake_redis_async():
    return aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    db.close = AsyncMock()
    return db


@pytest.fixture
def admin_claims() -> UserClaims:
    return UserClaims(id=1, role="admin", name="Admin Test")


@pytest.fixture
def supervisor_claims() -> UserClaims:
    return UserClaims(id=2, role="supervisor", name="Supervisor Test")


@pytest.fixture
def technician_claims() -> UserClaims:
    return UserClaims(id=3, role="technician", name="Tech Test")


@pytest.fixture
def attendant_claims() -> UserClaims:
    return UserClaims(id=4, role="attendant", name="Attendant Test")
