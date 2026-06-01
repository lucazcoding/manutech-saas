"""
Fixtures para testes unitários (mockados).

Estratégia:
- AsyncMock para AsyncSession (sem banco real).
- FakeRedis para Redis.
- get_current_user sobrescrito via dependency_overrides por role.
- Nenhum serviço externo é chamado.
"""

from unittest.mock import AsyncMock, MagicMock

import fakeredis.aioredis as fakeredis
import pytest

from shared.shared.auth.dependencies import UserClaims


@pytest.fixture
def mock_db():
    """AsyncSession mockado — simula commit, rollback e execute."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def mock_redis():
    """Redis falso em memória."""
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def admin_claims() -> UserClaims:
    return UserClaims(id=1, role="admin", name="Admin Test")


@pytest.fixture
def supervisor_claims() -> UserClaims:
    return UserClaims(id=2, role="supervisor", name="Supervisor Test")


@pytest.fixture
def technician_claims() -> UserClaims:
    return UserClaims(id=3, role="technician", name="Technician Test")


@pytest.fixture
def attendant_claims() -> UserClaims:
    return UserClaims(id=4, role="attendant", name="Attendant Test")


def override_current_user(claims: UserClaims):
    """
    Retorna uma função para sobrescrever get_current_user em tests unitários.

    Uso:
        from shared.shared.auth.dependencies import get_current_user
        app.dependency_overrides[get_current_user] = override_current_user(admin_claims)
    """
    async def _override():
        return claims
    return _override
