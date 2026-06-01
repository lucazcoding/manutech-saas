"""Fixtures para testes E2E do Inventory Service."""

import pytest_asyncio
from httpx2 import ASGITransport, AsyncClient
from sqlalchemy import text

from services.inventory.main import create_app
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
async def inv_client_admin(db_session, redis_client, rsa_keys, admin_token):
    app = _make_app(db_session, redis_client, rsa_keys)
    headers = {"Authorization": f"Bearer {admin_token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def inv_client_supervisor(db_session, redis_client, rsa_keys, supervisor_token):
    app = _make_app(db_session, redis_client, rsa_keys)
    headers = {"Authorization": f"Bearer {supervisor_token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def inv_client_technician(db_session, redis_client, rsa_keys, technician_token):
    app = _make_app(db_session, redis_client, rsa_keys)
    headers = {"Authorization": f"Bearer {technician_token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def inv_client_attendant(db_session, redis_client, rsa_keys, attendant_token):
    app = _make_app(db_session, redis_client, rsa_keys)
    headers = {"Authorization": f"Bearer {attendant_token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seeded_material(db_session):
    """Material ativo com estoque inicial suficiente."""
    result = await db_session.execute(
        text(
            "INSERT INTO materials (name, sku, unit_price, quantity_in_stock, min_quantity, status) "
            "VALUES ('Parafuso E2E', 'SKU-E2E-001', 2.50, 100.000, 5.000, 'active') "
            "RETURNING id"
        )
    )
    await db_session.commit()
    mat_id = result.scalar_one()
    return {"id": mat_id, "name": "Parafuso E2E", "sku": "SKU-E2E-001", "quantity_in_stock": 100.0}


@pytest_asyncio.fixture
async def seeded_order_for_movement(db_session):
    """OS para referenciar nos movimentos de estoque."""
    result = await db_session.execute(
        text(
            "INSERT INTO service_orders (client_name, location, status, priority) "
            "VALUES ('Cliente Inv', 'Rua Inv, 1', 'open', 'low') "
            "RETURNING id"
        )
    )
    await db_session.commit()
    order_id = result.scalar_one()
    return {"id": order_id}
