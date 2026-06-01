"""
IMPORTANTE: O Notification Service tem subscriber Redis na lifespan.
Para testes, patchamos start_subscriber para evitar conexão real.
"""
import asyncio
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy import text
from httpx2 import ASGITransport, AsyncClient

from shared.shared.config import SharedSettings, get_shared_settings
from shared.shared.db.session import get_db
from services.notification.main import create_app
from tests.e2e.conftest import TEST_DATABASE_URL, make_get_db_override


async def _noop_subscriber(*args, **kwargs):
    await asyncio.sleep(0)


def make_notification_settings(rsa_keys):
    return SharedSettings(jwt_public_key=rsa_keys["public"], database_url=TEST_DATABASE_URL)


def _build_notification_app(db_session, rsa_keys):
    app = create_app()
    settings = make_notification_settings(rsa_keys)
    app.dependency_overrides[get_shared_settings] = lambda: settings
    app.dependency_overrides[get_db] = make_get_db_override(db_session)
    return app


@pytest_asyncio.fixture
async def notification_client_admin(db_session, rsa_keys, admin_token):
    app = _build_notification_app(db_session, rsa_keys)
    headers = {"Authorization": f"Bearer {admin_token}"}
    with patch("services.notification.main.start_subscriber", side_effect=_noop_subscriber):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", headers=headers
        ) as client:
            yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def notification_client_supervisor(db_session, rsa_keys, supervisor_token):
    app = _build_notification_app(db_session, rsa_keys)
    headers = {"Authorization": f"Bearer {supervisor_token}"}
    with patch("services.notification.main.start_subscriber", side_effect=_noop_subscriber):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", headers=headers
        ) as client:
            yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def notification_client_technician(db_session, rsa_keys, technician_token):
    app = _build_notification_app(db_session, rsa_keys)
    headers = {"Authorization": f"Bearer {technician_token}"}
    with patch("services.notification.main.start_subscriber", side_effect=_noop_subscriber):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", headers=headers
        ) as client:
            yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def notification_client_attendant(db_session, rsa_keys, attendant_token):
    app = _build_notification_app(db_session, rsa_keys)
    headers = {"Authorization": f"Bearer {attendant_token}"}
    with patch("services.notification.main.start_subscriber", side_effect=_noop_subscriber):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", headers=headers
        ) as client:
            yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def notification_client_no_auth(db_session, rsa_keys):
    """Client sem autenticação para o Notification Service."""
    app = _build_notification_app(db_session, rsa_keys)
    with patch("services.notification.main.start_subscriber", side_effect=_noop_subscriber):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client
    app.dependency_overrides.clear()


async def _seed_user(db_session, user_id: int, role: str) -> None:
    """Insere usuário mínimo para satisfazer FK de notifications."""
    await db_session.execute(
        text(
            "INSERT INTO users (id, name, login, email, password_hash, role, status) "
            "VALUES (:uid, :name, :login, :email, 'x', :role, 'active') "
            "ON CONFLICT (id) DO NOTHING"
        ),
        {
            "uid": user_id,
            "name": f"Test {role}",
            "login": f"test.{role}.{user_id}",
            "email": f"test.{role}.{user_id}@test.com",
            "role": role,
        },
    )
    await db_session.commit()


@pytest_asyncio.fixture
async def seeded_notification(db_session):
    """Insere usuário + notificação para user_id=1 (admin nos tokens de teste)."""
    await _seed_user(db_session, user_id=1, role="admin")
    result = await db_session.execute(
        text(
            "INSERT INTO notifications (user_id, type, title, message, read) "
            "VALUES (1, 'order.assigned', 'OS Atribuida', 'Voce foi atribuido a uma OS', false) "
            "RETURNING id"
        ),
    )
    await db_session.commit()
    row = result.fetchone()
    return {"id": row[0], "user_id": 1}


@pytest_asyncio.fixture
async def seeded_notification_for_technician(db_session):
    """Insere usuário + notificação para user_id=3 (technician nos tokens de teste)."""
    await _seed_user(db_session, user_id=3, role="technician")
    result = await db_session.execute(
        text(
            "INSERT INTO notifications (user_id, type, title, message, read) "
            "VALUES (3, 'order.assigned', 'OS para Tecnico', 'Mensagem para tecnico', false) "
            "RETURNING id"
        ),
    )
    await db_session.commit()
    row = result.fetchone()
    return {"id": row[0], "user_id": 3}
