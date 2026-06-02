"""Fixtures para testes E2E do Finance Service."""

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from services.finance.main import create_app
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
async def finance_client_admin(db_session, redis_client, rsa_keys, admin_token):
    app = _make_app(db_session, redis_client, rsa_keys)
    headers = {"Authorization": f"Bearer {admin_token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def finance_client_supervisor(db_session, redis_client, rsa_keys, supervisor_token):
    app = _make_app(db_session, redis_client, rsa_keys)
    headers = {"Authorization": f"Bearer {supervisor_token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def finance_client_technician(db_session, redis_client, rsa_keys, technician_token):
    app = _make_app(db_session, redis_client, rsa_keys)
    headers = {"Authorization": f"Bearer {technician_token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def finance_client_attendant(db_session, redis_client, rsa_keys, attendant_token):
    app = _make_app(db_session, redis_client, rsa_keys)
    headers = {"Authorization": f"Bearer {attendant_token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seeded_order(db_session):
    """OS para referenciar nos custos e orçamentos."""
    result = await db_session.execute(
        text(
            "INSERT INTO service_orders (client_name, location, status, priority) "
            "VALUES ('Cliente Fin', 'Rua Fin, 1', 'open', 'medium') "
            "RETURNING id"
        )
    )
    await db_session.commit()
    order_id = result.scalar_one()
    return {"id": order_id}


@pytest_asyncio.fixture
async def seeded_cost(db_session, seeded_order):
    """Custo de mão-de-obra para testes de leitura/update."""
    result = await db_session.execute(
        text(
            "INSERT INTO service_costs (service_order_id, description, amount, cost_type) "
            "VALUES (:oid, 'Mão de obra E2E', 150.00, 'labor') "
            "RETURNING id"
        ),
        {"oid": seeded_order["id"]},
    )
    await db_session.commit()
    cost_id = result.scalar_one()
    return {"id": cost_id, "service_order_id": seeded_order["id"]}


@pytest_asyncio.fixture
async def seeded_budget_draft(db_session, seeded_order):
    """Orçamento em status draft."""
    result = await db_session.execute(
        text(
            "INSERT INTO budgets (service_order_id, client_name, status, valid_until) "
            "VALUES (:oid, 'Cliente Budget E2E', 'draft', CURRENT_DATE + INTERVAL '30 days') "
            "RETURNING id"
        ),
        {"oid": seeded_order["id"]},
    )
    await db_session.commit()
    budget_id = result.scalar_one()
    return {"id": budget_id, "service_order_id": seeded_order["id"], "status": "draft"}


@pytest_asyncio.fixture
async def seeded_budget_sent(db_session, seeded_order):
    """Orçamento já enviado (não editável)."""
    result = await db_session.execute(
        text(
            "INSERT INTO budgets (service_order_id, client_name, status, valid_until) "
            "VALUES (:oid, 'Cliente Budget Enviado', 'sent', CURRENT_DATE + INTERVAL '30 days') "
            "RETURNING id"
        ),
        {"oid": seeded_order["id"]},
    )
    await db_session.commit()
    budget_id = result.scalar_one()
    return {"id": budget_id, "service_order_id": seeded_order["id"], "status": "sent"}
