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
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

_ROOT = Path(__file__).parent.parent.parent


# ── Resolução das configurações ───────────────────────────────────────────────
# Prioridade (maior para menor):
#   1. Variáveis de ambiente do shell (TEST_DATABASE_URL / TEST_REDIS_URL)
#   2. Arquivo .env.test.docker  ← usado quando o stack Docker está local
#   3. Arquivo .env raiz         ← fallback padrão
# ─────────────────────────────────────────────────────────────────────────────

_TEST_ENV_FILE = _ROOT / ".env.test.docker"
_MAIN_ENV_FILE = _ROOT / ".env"

# pydantic-settings lê o último arquivo da lista com maior prioridade
_env_files = [str(_MAIN_ENV_FILE)]
if _TEST_ENV_FILE.exists():
    _env_files.append(str(_TEST_ENV_FILE))


class _EnvSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_files,
        extra="ignore",
    )
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/manutech_test"
    redis_url: str = "redis://localhost:6379/0"


def _load_env() -> _EnvSettings:
    settings = _EnvSettings()
    # Variáveis explícitas no shell ainda têm prioridade máxima
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


@pytest_asyncio.fixture(autouse=True)
async def seed_base_users(db_session):
    """
    Semeia os usuários base correspondentes aos tokens de teste.
    Evita violações de chave estrangeira nas tabelas audit_logs ou RLS.
    """
    dummy_hash = "$2b$04$eImiTXuWV5jvhgh2GP5Ur.8VHgQ4.P4e3X5Y0F.7P3q3X3X3X3X3X"
    await db_session.execute(
        text(
            """
            INSERT INTO users (id, login, name, email, password_hash, role, status)
            VALUES
                (1, 'admin.test', 'Admin Test', 'admin.test@test.com', :pwd, 'admin', 'active'),
                (2, 'supervisor.test', 'Supervisor Test', 'supervisor.test@test.com', :pwd, 'supervisor', 'active'),
                (3, 'technician.test', 'Technician Test', 'technician.test@test.com', :pwd, 'technician', 'active'),
                (4, 'attendant.test', 'Attendant Test', 'attendant.test@test.com', :pwd, 'attendant', 'active')
            ON CONFLICT (id) DO UPDATE SET
                login = EXCLUDED.login,
                name = EXCLUDED.name,
                email = EXCLUDED.email,
                role = EXCLUDED.role,
                status = EXCLUDED.status
            """
        ),
        {"pwd": dummy_hash}
    )
    # Sincroniza a sequence do id de users para evitar erros em inserts subsequentes sem ID
    await db_session.execute(
        text("SELECT setval('users_id_seq', COALESCE((SELECT MAX(id) FROM users), 1))")
    )
    await db_session.commit()


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
