"""Fixtures para testes E2E do Asset Service."""

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from services.asset.main import create_app
from shared.shared.config import SharedSettings, get_shared_settings
from shared.shared.db.session import get_db
from shared.shared.redis.client import get_redis
from tests.e2e.conftest import TEST_DATABASE_URL, make_get_db_override


def _make_settings(rsa_keys: dict) -> SharedSettings:
    return SharedSettings(jwt_public_key=rsa_keys["public"], database_url=TEST_DATABASE_URL)


def _make_app(db_session, redis_client, rsa_keys):
    app = create_app()
    settings = _make_settings(rsa_keys)
    app.dependency_overrides[get_shared_settings] = lambda: settings
    app.dependency_overrides[get_db] = make_get_db_override(db_session)
    app.dependency_overrides[get_redis] = lambda: redis_client
    return app


@pytest_asyncio.fixture
async def asset_client_admin(db_session, redis_client, rsa_keys, admin_token):
    app = _make_app(db_session, redis_client, rsa_keys)
    headers = {"Authorization": f"Bearer {admin_token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def asset_client_supervisor(db_session, redis_client, rsa_keys, supervisor_token):
    app = _make_app(db_session, redis_client, rsa_keys)
    headers = {"Authorization": f"Bearer {supervisor_token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def asset_client_technician(db_session, redis_client, rsa_keys, technician_token):
    app = _make_app(db_session, redis_client, rsa_keys)
    headers = {"Authorization": f"Bearer {technician_token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def asset_client_attendant(db_session, redis_client, rsa_keys, attendant_token):
    app = _make_app(db_session, redis_client, rsa_keys)
    headers = {"Authorization": f"Bearer {attendant_token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seeded_asset(db_session):
    """Insere um ativo ativo para uso nos testes."""
    result = await db_session.execute(
        text(
            "INSERT INTO assets (name, serial_number, status) "
            "VALUES ('Compressor E2E', 'SN-E2E-001', 'active') "
            "RETURNING id"
        )
    )
    await db_session.commit()
    asset_id = result.scalar_one()
    return {"id": asset_id, "name": "Compressor E2E", "serial_number": "SN-E2E-001"}
