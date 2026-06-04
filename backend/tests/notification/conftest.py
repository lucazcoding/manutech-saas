import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from shared.shared.auth.dependencies import UserClaims, get_current_user
from shared.shared.config import SharedSettings, get_shared_settings
from shared.shared.db.session import get_db

from services.notification.config import NotificationSettings, get_notification_settings
from services.notification.main import create_app


def make_settings(rsa_keys: dict) -> NotificationSettings:
    return NotificationSettings(
        jwt_public_key=rsa_keys["public"],
        database_url="postgresql+psycopg://x:x@localhost/x",
        redis_url="redis://localhost:6379/0",
    )


def make_client(
    rsa_keys: dict,
    current_user: UserClaims | None = None,
    mock_db: AsyncMock | None = None,
) -> TestClient:
    app = create_app()
    settings = make_settings(rsa_keys)
    app.dependency_overrides[get_shared_settings] = lambda: settings
    app.dependency_overrides[get_notification_settings] = lambda: settings

    if mock_db is not None:
        app.dependency_overrides[get_db] = lambda: mock_db

    if current_user is not None:
        app.dependency_overrides[get_current_user] = lambda: current_user

    return TestClient(app, raise_server_exceptions=False)


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
