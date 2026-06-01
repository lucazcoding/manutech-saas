"""Fixtures para testes E2E do Auth Service."""

import bcrypt as _bcrypt
import pytest_asyncio
from httpx2 import ASGITransport, AsyncClient
from sqlalchemy import text

from services.auth.config import AuthSettings, get_auth_settings
from services.auth.main import create_app
from shared.shared.config import get_shared_settings
from shared.shared.db.session import get_db
from shared.shared.redis.client import get_redis
from tests.e2e.conftest import TEST_DATABASE_URL, make_get_db_override

def _hash(password: str) -> str:
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt(rounds=4)).decode()


def _make_settings(rsa_keys: dict) -> AuthSettings:
    return AuthSettings(
        jwt_public_key=rsa_keys["public"],
        jwt_private_key=rsa_keys["private"],
        database_url=TEST_DATABASE_URL,
        login_max_attempts=5,
        login_window_seconds=900,
    )


@pytest_asyncio.fixture
async def auth_client(db_session, redis_client, rsa_keys):
    # Limpa contadores de rate limit residuais de testes anteriores
    await redis_client.delete("login_attempts:testclient", "login_attempts:unknown")
    app = create_app()
    settings = _make_settings(rsa_keys)
    app.dependency_overrides[get_shared_settings] = lambda: settings
    app.dependency_overrides[get_auth_settings] = lambda: settings
    app.dependency_overrides[get_db] = make_get_db_override(db_session)
    app.dependency_overrides[get_redis] = lambda: redis_client
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
    await redis_client.delete("login_attempts:testclient", "login_attempts:unknown")


@pytest_asyncio.fixture
async def auth_client_admin(db_session, redis_client, rsa_keys, admin_token):
    app = create_app()
    settings = _make_settings(rsa_keys)
    app.dependency_overrides[get_shared_settings] = lambda: settings
    app.dependency_overrides[get_auth_settings] = lambda: settings
    app.dependency_overrides[get_db] = make_get_db_override(db_session)
    app.dependency_overrides[get_redis] = lambda: redis_client
    headers = {"Authorization": f"Bearer {admin_token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_client_supervisor(db_session, redis_client, rsa_keys, supervisor_token):
    app = create_app()
    settings = _make_settings(rsa_keys)
    app.dependency_overrides[get_shared_settings] = lambda: settings
    app.dependency_overrides[get_auth_settings] = lambda: settings
    app.dependency_overrides[get_db] = make_get_db_override(db_session)
    app.dependency_overrides[get_redis] = lambda: redis_client
    headers = {"Authorization": f"Bearer {supervisor_token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seeded_user(db_session):
    pwd_hash = _hash("senha_valida_123")
    result = await db_session.execute(
        text(
            "INSERT INTO users (name, login, email, password_hash, role, status) "
            "VALUES ('Admin E2E', 'admin.e2e', 'admin.e2e@test.com', :pwd, 'admin', 'active') "
            "RETURNING id"
        ),
        {"pwd": pwd_hash},
    )
    await db_session.commit()
    user_id = result.scalar_one()
    return {"id": user_id, "login": "admin.e2e", "password": "senha_valida_123", "role": "admin"}


@pytest_asyncio.fixture
async def seeded_inactive_user(db_session):
    pwd_hash = _hash("senha_valida_123")
    result = await db_session.execute(
        text(
            "INSERT INTO users (name, login, email, password_hash, role, status) "
            "VALUES ('Inativo E2E', 'inativo.e2e', 'inativo.e2e@test.com', :pwd, 'technician', 'inactive') "
            "RETURNING id"
        ),
        {"pwd": pwd_hash},
    )
    await db_session.commit()
    user_id = result.scalar_one()
    return {"id": user_id, "login": "inativo.e2e", "password": "senha_valida_123"}
