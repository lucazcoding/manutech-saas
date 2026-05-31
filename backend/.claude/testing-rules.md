# Testes — Regras

## Cobertura mínima: 80%

Todo serviço deve ter:
- **Testes unitários** — services e utilities isoladas com mocks
- **Testes de integração** — rotas completas com banco em memória ou Testcontainers

---

## Stack de Testes

```
pytest
pytest-asyncio
httpx              # TestClient async do FastAPI
pytest-cov         # cobertura
factory-boy        # factories de fixtures
```

---

## Estrutura de Testes

```
services/<nome>/tests/
├── conftest.py            # fixtures compartilhadas (app, db, client, usuários)
├── unit/
│   ├── test_order_service.py
│   ├── test_state_machine.py
│   └── test_validators.py
└── integration/
    ├── test_create_order.py
    ├── test_assign_technician.py
    ├── test_order_status.py
    └── test_rbac.py
```

---

## Fixtures Base (conftest.py)

```python
# services/order/tests/conftest.py
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from ..main import app
from shared.db.session import get_db
from shared.auth.dependencies import get_current_user
from shared.schemas.auth import UserClaims

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/manutech_test"


@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        # setup: criar tabelas, limpar dados
        pass

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()  # desfaz tudo após cada teste

    await engine.dispose()


def make_user(role: str, user_id: int = 1) -> UserClaims:
    return UserClaims(id=user_id, role=role, name=f"Test {role.title()}")


@pytest_asyncio.fixture
async def client_admin(db_session):
    return await _make_client(db_session, role="admin")


@pytest_asyncio.fixture
async def client_supervisor(db_session):
    return await _make_client(db_session, role="supervisor")


@pytest_asyncio.fixture
async def client_technician(db_session):
    return await _make_client(db_session, role="technician", user_id=5)


@pytest_asyncio.fixture
async def client_attendant(db_session):
    return await _make_client(db_session, role="attendant")


async def _make_client(db_session: AsyncSession, role: str, user_id: int = 1):
    user = make_user(role, user_id)
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
```

---

## Teste de Rota — Exemplo Completo

```python
# services/order/tests/integration/test_create_order.py
import pytest


class TestCreateOrder:
    """POST /api/v1/orders"""

    @pytest.mark.asyncio
    async def test_supervisor_can_create_order(self, client_supervisor):
        response = await client_supervisor.post(
            "/api/v1/orders",
            json={
                "client_name": "Empresa X",
                "location": "Rua A, 100",
                "priority": "high",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["client_name"] == "Empresa X"
        assert data["status"] == "open"
        assert data["priority"] == "high"
        assert data["assigned_technician"] is None
        assert data["total_cost"] == 0.0

    @pytest.mark.asyncio
    async def test_attendant_can_create_order(self, client_attendant):
        response = await client_attendant.post(
            "/api/v1/orders",
            json={"client_name": "Empresa Y", "location": "Rua B, 200"},
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_technician_cannot_create_order(self, client_technician):
        response = await client_technician.post(
            "/api/v1/orders",
            json={"client_name": "X", "location": "Y"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_cannot_create_order(self, client_admin):
        # admin não tem permissão para criar OS (role não incluído)
        response = await client_admin.post(
            "/api/v1/orders",
            json={"client_name": "X", "location": "Y"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_order_with_inactive_asset_returns_400(
        self, client_supervisor, inactive_asset
    ):
        response = await client_supervisor.post(
            "/api/v1/orders",
            json={
                "client_name": "Empresa X",
                "location": "Rua A",
                "asset_id": inactive_asset.id,
            },
        )
        assert response.status_code == 400
        assert response.json()["code"] == "ASSET_INACTIVE"

    @pytest.mark.asyncio
    async def test_create_order_missing_required_fields(self, client_supervisor):
        response = await client_supervisor.post("/api/v1/orders", json={})
        assert response.status_code == 422
        assert response.json()["code"] == "VALIDATION_ERROR"
```

---

## Teste de State Machine

```python
# services/order/tests/unit/test_state_machine.py
import pytest
from ..services.state_machine import validate_status_transition
from shared.exceptions.business import BusinessError


class TestOrderStateMachine:
    def test_open_to_in_progress_is_valid(self):
        # não levanta exceção
        validate_status_transition(current="open", next="in_progress")

    def test_in_progress_to_completed_is_valid(self):
        validate_status_transition(current="in_progress", next="completed")

    def test_open_to_cancelled_is_valid(self):
        validate_status_transition(current="open", next="cancelled")

    def test_in_progress_to_cancelled_is_valid(self):
        validate_status_transition(current="in_progress", next="cancelled")

    def test_completed_to_any_is_invalid(self):
        for target in ["open", "in_progress", "cancelled"]:
            with pytest.raises(BusinessError) as exc:
                validate_status_transition(current="completed", next=target)
            assert exc.value.code == "INVALID_STATUS_TRANSITION"

    def test_cancelled_to_any_is_invalid(self):
        for target in ["open", "in_progress", "completed"]:
            with pytest.raises(BusinessError):
                validate_status_transition(current="cancelled", next=target)

    def test_open_to_completed_is_invalid(self):
        with pytest.raises(BusinessError) as exc:
            validate_status_transition(current="open", next="completed")
        assert exc.value.code == "INVALID_STATUS_TRANSITION"
```

---

## Teste de RBAC — Template para todos os serviços

Para cada rota, testar:

```python
# Template de teste RBAC
@pytest.mark.parametrize("client_fixture, expected_status", [
    ("client_admin", 200),       # ou 201/204 dependendo da rota
    ("client_supervisor", 200),
    ("client_technician", 403),
    ("client_attendant", 403),
])
async def test_rbac_<rota>(self, request, client_fixture, expected_status):
    client = request.getfixturevalue(client_fixture)
    response = await client.get("/api/v1/...")
    assert response.status_code == expected_status
```

---

## Executar testes

```bash
# Todos os testes com cobertura:
pytest services/order/tests/ --cov=services/order --cov-report=term-missing --cov-fail-under=80

# Apenas unitários:
pytest services/order/tests/unit/ -v

# Apenas integração:
pytest services/order/tests/integration/ -v

# Um teste específico:
pytest services/order/tests/integration/test_create_order.py::TestCreateOrder::test_supervisor_can_create_order -v
```
