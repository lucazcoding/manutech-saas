import bcrypt as _bcrypt
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from services.order.dependencies import get_storage
from services.order.main import create_app
from shared.shared.config import SharedSettings, get_shared_settings
from shared.shared.db.session import get_db
from shared.shared.redis.client import get_redis
from tests.e2e.conftest import TEST_DATABASE_URL, make_get_db_override



class _MockStorage:
    async def upload(self, file_content: bytes, file_name: str, content_type: str) -> str:
        return f"https://fake-storage.test/{file_name}"


def _make_settings(rsa_keys: dict) -> SharedSettings:
    return SharedSettings(jwt_public_key=rsa_keys["public"], database_url=TEST_DATABASE_URL)


def _make_app(db_session, redis_client, rsa_keys):
    app = create_app()
    settings = _make_settings(rsa_keys)
    app.dependency_overrides[get_shared_settings] = lambda: settings
    app.dependency_overrides[get_db] = make_get_db_override(db_session)
    app.dependency_overrides[get_redis] = lambda: redis_client
    app.dependency_overrides[get_storage] = lambda: _MockStorage()
    return app


@pytest_asyncio.fixture
async def order_client_admin(db_session, redis_client, rsa_keys, admin_token):
    app = _make_app(db_session, redis_client, rsa_keys)
    headers = {"Authorization": f"Bearer {admin_token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def order_client_supervisor(db_session, redis_client, rsa_keys, supervisor_token):
    app = _make_app(db_session, redis_client, rsa_keys)
    headers = {"Authorization": f"Bearer {supervisor_token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def order_client_technician(db_session, redis_client, rsa_keys, technician_token):
    app = _make_app(db_session, redis_client, rsa_keys)
    headers = {"Authorization": f"Bearer {technician_token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def order_client_attendant(db_session, redis_client, rsa_keys, attendant_token):
    app = _make_app(db_session, redis_client, rsa_keys)
    headers = {"Authorization": f"Bearer {attendant_token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seeded_order(db_session):
    """OS em status 'open'."""
    result = await db_session.execute(
        text(
            "INSERT INTO service_orders (client_name, location, status, priority) "
            "VALUES ('Cliente E2E', 'Rua Teste, 1', 'open', 'medium') "
            "RETURNING id"
        )
    )
    await db_session.commit()
    order_id = result.scalar_one()
    return {"id": order_id, "status": "open"}


@pytest_asyncio.fixture
async def seeded_technician_user(db_session):
    """Usuário com role technician (user_id=3 nos tokens de teste)."""
    pwd_hash = _bcrypt.hashpw("senha123".encode(), _bcrypt.gensalt(rounds=4)).decode()
    result = await db_session.execute(
        text(
            "INSERT INTO users (id, name, login, email, password_hash, role, status) "
            "VALUES (3, 'Tech E2E', 'tech.e2e', 'tech.e2e@test.com', :pwd, 'technician', 'active') "
            "ON CONFLICT (id) DO UPDATE SET name='Tech E2E' "
            "RETURNING id"
        ),
        {"pwd": pwd_hash},
    )
    await db_session.commit()
    user_id = result.scalar_one()
    return {"id": user_id, "role": "technician"}


@pytest_asyncio.fixture
async def seeded_in_progress_order(db_session, seeded_technician_user):
    """OS em status 'in_progress' com técnico atribuído."""
    result = await db_session.execute(
        text(
            "INSERT INTO service_orders (client_name, location, status, priority) "
            "VALUES ('Cliente Prog', 'Rua Prog, 2', 'in_progress', 'high') "
            "RETURNING id"
        )
    )
    await db_session.commit()
    order_id = result.scalar_one()
    await db_session.execute(
        text(
            "INSERT INTO order_assignments (service_order_id, technician_id, active) "
            "VALUES (:oid, :tid, true)"
        ),
        {"oid": order_id, "tid": seeded_technician_user["id"]},
    )
    await db_session.commit()
    return {"id": order_id, "status": "in_progress"}
