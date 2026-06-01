"""
Fixtures base para testes E2E.

Banco: Supabase (via DATABASE_URL do .env).
Redis: Upstash real (via REDIS_URL do .env).

Isolamento:
- db_session cria engine + conexão por teste e faz ROLLBACK no teardown.
- Cada request faz commit() → RELEASE SAVEPOINT (dados visíveis na sessão).
- Após o teste, rollback desfaz tudo — nenhum dado permanece no banco.

Para pular: pytest -m "not e2e"
"""

import os
from pathlib import Path

import pytest
import pytest_asyncio
import redis.asyncio as aioredis
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


# ── Resolução das configurações a partir do .env raiz ────────────────────────

class _EnvSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent.parent / ".env"),
        extra="ignore",
    )
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/manutech_test"
    redis_url: str = "redis://localhost:6379/0"


def _load_env() -> _EnvSettings:
    settings = _EnvSettings()
    if explicit_db := os.getenv("TEST_DATABASE_URL"):
        settings.database_url = explicit_db
    if explicit_redis := os.getenv("TEST_REDIS_URL"):
        settings.redis_url = explicit_redis
    return settings


_env = _load_env()

TEST_DATABASE_URL = _env.database_url
TEST_REDIS_URL = _env.redis_url.strip()

_is_supabase = "supabase.com" in TEST_DATABASE_URL or "supabase.co" in TEST_DATABASE_URL
_connect_args: dict = (
    {"ssl": "require", "prepared_statement_cache_size": 0, "statement_cache_size": 0}
    if _is_supabase
    else {}
)


# ── Sessão isolada por teste ──────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db_session():
    """
    Cria engine + sessão por teste (evita conflito de event loop no Windows).
    Rollback automático no teardown — nenhum dado persiste entre testes.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        pool_pre_ping=True,
        connect_args=_connect_args,
    )
    try:
        async with engine.connect() as conn:
            trans = await conn.begin()
            session = AsyncSession(
                conn,
                expire_on_commit=False,
                join_transaction_mode="create_savepoint",
            )
            try:
                yield session
            finally:
                await session.close()
                await trans.rollback()
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def redis_client():
    """Conexão real com o Upstash Redis por teste."""
    client = aioredis.from_url(
        TEST_REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )
    try:
        yield client
    finally:
        await client.aclose()


def make_get_db_override(session: AsyncSession):
    """
    Retorna override async generator para get_db.
    commit() → RELEASE SAVEPOINT (dentro da transação de teste).
    """
    async def _override():
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
    return _override
