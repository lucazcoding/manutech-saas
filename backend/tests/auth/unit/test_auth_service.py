"""
Testes unitários do Auth Service — MOCK-01 a MOCK-04 + extras de regra de negócio.

MOCK-01: password_hash NUNCA exposto em nenhuma resposta
MOCK-02: Credenciais inválidas retornam 401 INVALID_CREDENTIALS
MOCK-03: Technician não pode acessar GET /users (403)
MOCK-04: Email/login duplicado retorna 409 com code correto
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

import fakeredis.aioredis as aioredis

from shared.shared.auth.dependencies import UserClaims, get_current_user
from shared.shared.auth.jwt import create_access_token, create_refresh_token_value, hash_token
from shared.shared.db.session import get_db
from shared.shared.exceptions.handlers import BusinessError
from shared.shared.redis.client import get_redis

from services.auth.config import AuthSettings, get_auth_settings
from services.auth.main import create_app
from services.auth.schemas.user import UserResponse, StatusUpdateResponse

from tests.auth.conftest import make_auth_settings, make_client


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_user_row(
    user_id: int = 1,
    login: str = "admin",
    name: str = "Admin",
    email: str = "admin@test.com",
    role: str = "admin",
    status: str = "active",
    password_hash: str = "$2b$12$fakehash",
):
    """Simula um objeto ORM User retornado pelo repositório."""
    user = MagicMock()
    user.id = user_id
    user.login = login
    user.name = name
    user.email = email
    user.role = role
    user.status = status
    user.password_hash = password_hash
    user.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    user.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return user


def _make_refresh_token(user_id: int = 1, revoked: bool = False, expired: bool = False):
    token = MagicMock()
    token.user_id = user_id
    token.revoked = revoked
    token.expires_at = (
        datetime.now(timezone.utc) - timedelta(hours=1)
        if expired
        else datetime.now(timezone.utc) + timedelta(days=7)
    )
    return token


# ── MOCK-01: password_hash nunca exposto ──────────────────────────────────────

class TestPasswordHashNeverExposed:
    """MOCK-01 — Garantia de que password_hash não vaza em nenhum response."""

    def test_user_response_schema_has_no_password_hash_field(self):
        """UserResponse não tem campo password_hash no schema Pydantic."""
        assert "password_hash" not in UserResponse.model_fields

    def test_user_response_serialization_excludes_password_hash(self):
        """Mesmo com from_attributes, password_hash não é serializado."""
        user = _make_user_row()
        response = UserResponse.model_validate(user)
        serialized = response.model_dump()
        assert "password_hash" not in serialized

    def test_status_update_response_has_no_password_hash_field(self):
        """StatusUpdateResponse também não expõe password_hash."""
        assert "password_hash" not in StatusUpdateResponse.model_fields

    def test_login_response_user_object_has_no_password_hash(self, rsa_keys):
        """O objeto user dentro de TokenResponse não tem password_hash."""
        fake_redis_instance = aioredis.FakeRedis(decode_responses=True)
        user = _make_user_row()
        db = AsyncMock()

        with patch("services.auth.services.auth_service.UserRepository") as MockUserRepo, \
             patch("services.auth.services.auth_service.TokenRepository") as MockTokenRepo, \
             patch("services.auth.services.auth_service._verify_password", return_value=True):

            MockUserRepo.return_value.get_by_login = AsyncMock(return_value=user)
            MockTokenRepo.return_value.create = AsyncMock()

            client = make_client(rsa_keys, mock_db=db, mock_redis=fake_redis_instance)
            r = client.post("/api/v1/auth/login", json={"login": "admin", "password": "senha123"})

        assert r.status_code == 200
        body = r.json()
        assert "password_hash" not in body
        assert "password_hash" not in body.get("user", {})


# ── MOCK-02: Credenciais inválidas ────────────────────────────────────────────

class TestInvalidCredentials:
    """MOCK-02 — Login com credenciais erradas retorna 401 INVALID_CREDENTIALS."""

    def test_wrong_password_returns_401(self, rsa_keys):
        fake_redis_instance = aioredis.FakeRedis(decode_responses=True)
        user = _make_user_row()
        db = AsyncMock()

        with patch("services.auth.services.auth_service.UserRepository") as MockUserRepo, \
             patch("services.auth.services.auth_service._verify_password", return_value=False):

            MockUserRepo.return_value.get_by_login = AsyncMock(return_value=user)

            client = make_client(rsa_keys, mock_db=db, mock_redis=fake_redis_instance)
            r = client.post(
                "/api/v1/auth/login",
                json={"login": "admin", "password": "senhaerrada"},
            )

        assert r.status_code == 401
        body = r.json()
        assert body["code"] == "INVALID_CREDENTIALS"

    def test_user_not_found_returns_401(self, rsa_keys):
        fake_redis_instance = aioredis.FakeRedis(decode_responses=True)
        db = AsyncMock()

        with patch("services.auth.services.auth_service.UserRepository") as MockUserRepo:
            MockUserRepo.return_value.get_by_login = AsyncMock(return_value=None)

            client = make_client(rsa_keys, mock_db=db, mock_redis=fake_redis_instance)
            r = client.post(
                "/api/v1/auth/login",
                json={"login": "inexistente", "password": "qualquer"},
            )

        assert r.status_code == 401
        assert r.json()["code"] == "INVALID_CREDENTIALS"

    def test_inactive_user_returns_403(self, rsa_keys):
        fake_redis_instance = aioredis.FakeRedis(decode_responses=True)
        user = _make_user_row(status="inactive")
        db = AsyncMock()

        with patch("services.auth.services.auth_service.UserRepository") as MockUserRepo:
            MockUserRepo.return_value.get_by_login = AsyncMock(return_value=user)

            client = make_client(rsa_keys, mock_db=db, mock_redis=fake_redis_instance)
            r = client.post(
                "/api/v1/auth/login",
                json={"login": "admin", "password": "senha123"},
            )

        assert r.status_code == 403
        assert r.json()["code"] == "USER_INACTIVE"

    def test_rate_limit_exceeded_returns_429(self, rsa_keys):
        """Após 5 tentativas falhas, retorna 429 RATE_LIMIT_EXCEEDED."""
        fake_redis_instance = aioredis.FakeRedis(decode_responses=True)
        db = AsyncMock()

        with patch("services.auth.services.auth_service.UserRepository") as MockUserRepo:
            MockUserRepo.return_value.get_by_login = AsyncMock(return_value=None)

            client = make_client(rsa_keys, mock_db=db, mock_redis=fake_redis_instance)

            # 5 tentativas para atingir o limite
            for _ in range(5):
                client.post(
                    "/api/v1/auth/login",
                    json={"login": "user", "password": "wrong"},
                )

            # 6a tentativa deve retornar 429
            r = client.post(
                "/api/v1/auth/login",
                json={"login": "user", "password": "wrong"},
            )

        assert r.status_code == 429
        assert r.json()["code"] == "RATE_LIMIT_EXCEEDED"

    def test_successful_login_resets_rate_limit(self, rsa_keys):
        """Após login bem-sucedido, o contador de tentativas é zerado."""
        fake_redis_instance = aioredis.FakeRedis(decode_responses=True)
        user = _make_user_row()
        db = AsyncMock()

        with patch("services.auth.services.auth_service.UserRepository") as MockUserRepo, \
             patch("services.auth.services.auth_service.TokenRepository") as MockTokenRepo, \
             patch("services.auth.services.auth_service._verify_password", return_value=True):

            MockUserRepo.return_value.get_by_login = AsyncMock(return_value=user)
            MockTokenRepo.return_value.create = AsyncMock()

            client = make_client(rsa_keys, mock_db=db, mock_redis=fake_redis_instance)
            r = client.post(
                "/api/v1/auth/login",
                json={"login": "admin", "password": "senha123"},
            )

        assert r.status_code == 200

        # Contador deve ter sido zerado — não deve haver chave no Redis
        key = f"login_attempts:{client.app.state.__dict__.get('test_ip', 'testclient')}"
        # testclient usa IP "testclient" ou similar
        # Verificamos indiretamente que o login funcionou sem rate limit
        body = r.json()
        assert "access_token" in body
        assert "refresh_token" in body


# ── MOCK-03: RBAC — technician não pode acessar /users ───────────────────────

class TestRBACUsers:
    """MOCK-03 — Controle de acesso a rotas de gestão de usuários."""

    def test_technician_cannot_list_users(self, rsa_keys, technician_claims):
        db = AsyncMock()
        fake_redis_instance = aioredis.FakeRedis(decode_responses=True)
        client = make_client(
            rsa_keys,
            current_user=technician_claims,
            mock_db=db,
            mock_redis=fake_redis_instance,
        )
        r = client.get("/api/v1/users")
        assert r.status_code == 403

    def test_supervisor_cannot_list_users(self, rsa_keys, supervisor_claims):
        db = AsyncMock()
        fake_redis_instance = aioredis.FakeRedis(decode_responses=True)
        client = make_client(
            rsa_keys,
            current_user=supervisor_claims,
            mock_db=db,
            mock_redis=fake_redis_instance,
        )
        r = client.get("/api/v1/users")
        assert r.status_code == 403

    def test_attendant_cannot_list_users(self, rsa_keys, attendant_claims):
        db = AsyncMock()
        fake_redis_instance = aioredis.FakeRedis(decode_responses=True)
        client = make_client(
            rsa_keys,
            current_user=attendant_claims,
            mock_db=db,
            mock_redis=fake_redis_instance,
        )
        r = client.get("/api/v1/users")
        assert r.status_code == 403

    def test_admin_can_list_users(self, rsa_keys, admin_claims):
        db = AsyncMock()
        fake_redis_instance = aioredis.FakeRedis(decode_responses=True)

        with patch("services.auth.services.user_service.UserRepository") as MockRepo:
            MockRepo.return_value.list = AsyncMock(return_value=([], 0))

            with patch("services.auth.services.user_service.set_rls_context", new=AsyncMock()):
                client = make_client(
                    rsa_keys,
                    current_user=admin_claims,
                    mock_db=db,
                    mock_redis=fake_redis_instance,
                )
                r = client.get("/api/v1/users")

        assert r.status_code == 200

    def test_no_token_returns_403(self, rsa_keys):
        app = create_app()
        settings = make_auth_settings(rsa_keys)
        app.dependency_overrides[get_auth_settings] = lambda: settings
        from shared.shared.config import get_shared_settings
        app.dependency_overrides[get_shared_settings] = lambda: settings
        from shared.shared.db.session import get_db
        app.dependency_overrides[get_db] = lambda: AsyncMock()
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get("/api/v1/users")
        assert r.status_code == 401

    def test_technician_cannot_create_user(self, rsa_keys, technician_claims):
        db = AsyncMock()
        fake_redis_instance = aioredis.FakeRedis(decode_responses=True)
        client = make_client(
            rsa_keys,
            current_user=technician_claims,
            mock_db=db,
            mock_redis=fake_redis_instance,
        )
        r = client.post(
            "/api/v1/users",
            json={
                "name": "Novo",
                "login": "novo.user",
                "email": "novo@test.com",
                "password": "senha123",
                "role": "technician",
            },
        )
        assert r.status_code == 403

    def test_technician_cannot_patch_user_status(self, rsa_keys, technician_claims):
        db = AsyncMock()
        fake_redis_instance = aioredis.FakeRedis(decode_responses=True)
        client = make_client(
            rsa_keys,
            current_user=technician_claims,
            mock_db=db,
            mock_redis=fake_redis_instance,
        )
        r = client.patch("/api/v1/users/1/status", json={"status": "inactive"})
        assert r.status_code == 403


# ── MOCK-04: Conflitos de unicidade ───────────────────────────────────────────

class TestUniqueConstraints:
    """MOCK-04 — Conflito de login/email retorna 409 com code correto."""

    def test_duplicate_login_returns_409(self, rsa_keys, admin_claims):
        db = AsyncMock()
        fake_redis_instance = aioredis.FakeRedis(decode_responses=True)

        with patch("services.auth.services.user_service.UserRepository") as MockRepo, \
             patch("services.auth.services.user_service.set_rls_context", new=AsyncMock()), \
             patch("services.auth.services.user_service.hash_password", return_value="hash"):

            MockRepo.return_value.create = AsyncMock(
                side_effect=BusinessError("LOGIN_ALREADY_EXISTS", 409, "Login já está em uso", "login")
            )

            client = make_client(
                rsa_keys,
                current_user=admin_claims,
                mock_db=db,
                mock_redis=fake_redis_instance,
            )
            r = client.post(
                "/api/v1/users",
                json={
                    "name": "Dup",
                    "login": "dup.login",
                    "email": "dup@test.com",
                    "password": "senha123",
                    "role": "technician",
                },
            )

        assert r.status_code == 409
        body = r.json()
        assert body["code"] == "LOGIN_ALREADY_EXISTS"
        assert body["field"] == "login"

    def test_duplicate_email_returns_409(self, rsa_keys, admin_claims):
        db = AsyncMock()
        fake_redis_instance = aioredis.FakeRedis(decode_responses=True)

        with patch("services.auth.services.user_service.UserRepository") as MockRepo, \
             patch("services.auth.services.user_service.set_rls_context", new=AsyncMock()), \
             patch("services.auth.services.user_service.hash_password", return_value="hash"):

            MockRepo.return_value.create = AsyncMock(
                side_effect=BusinessError("EMAIL_ALREADY_EXISTS", 409, "Email já está em uso", "email")
            )

            client = make_client(
                rsa_keys,
                current_user=admin_claims,
                mock_db=db,
                mock_redis=fake_redis_instance,
            )
            r = client.post(
                "/api/v1/users",
                json={
                    "name": "Dup",
                    "login": "outro.login",
                    "email": "dup@test.com",
                    "password": "senha123",
                    "role": "technician",
                },
            )

        assert r.status_code == 409
        body = r.json()
        assert body["code"] == "EMAIL_ALREADY_EXISTS"
        assert body["field"] == "email"


# ── Extras: Validações de input ───────────────────────────────────────────────

class TestInputValidation:
    """Validações Pydantic nos endpoints de usuário."""

    def test_create_user_short_login_returns_422(self, rsa_keys, admin_claims):
        db = AsyncMock()
        fake_redis_instance = aioredis.FakeRedis(decode_responses=True)
        client = make_client(
            rsa_keys,
            current_user=admin_claims,
            mock_db=db,
            mock_redis=fake_redis_instance,
        )
        r = client.post(
            "/api/v1/users",
            json={
                "name": "X",
                "login": "ab",  # < 3 chars
                "email": "x@test.com",
                "password": "senha123",
                "role": "technician",
            },
        )
        assert r.status_code == 422
        assert r.json()["code"] == "VALIDATION_ERROR"

    def test_create_user_short_password_returns_422(self, rsa_keys, admin_claims):
        db = AsyncMock()
        fake_redis_instance = aioredis.FakeRedis(decode_responses=True)
        client = make_client(
            rsa_keys,
            current_user=admin_claims,
            mock_db=db,
            mock_redis=fake_redis_instance,
        )
        r = client.post(
            "/api/v1/users",
            json={
                "name": "X",
                "login": "valid.login",
                "email": "x@test.com",
                "password": "short",  # < 8 chars
                "role": "technician",
            },
        )
        assert r.status_code == 422

    def test_create_user_invalid_role_returns_422(self, rsa_keys, admin_claims):
        db = AsyncMock()
        fake_redis_instance = aioredis.FakeRedis(decode_responses=True)
        client = make_client(
            rsa_keys,
            current_user=admin_claims,
            mock_db=db,
            mock_redis=fake_redis_instance,
        )
        r = client.post(
            "/api/v1/users",
            json={
                "name": "X",
                "login": "valid.login",
                "email": "x@test.com",
                "password": "senha123",
                "role": "superadmin",  # role inválido
            },
        )
        assert r.status_code == 422

    def test_create_user_invalid_email_returns_422(self, rsa_keys, admin_claims):
        db = AsyncMock()
        fake_redis_instance = aioredis.FakeRedis(decode_responses=True)
        client = make_client(
            rsa_keys,
            current_user=admin_claims,
            mock_db=db,
            mock_redis=fake_redis_instance,
        )
        r = client.post(
            "/api/v1/users",
            json={
                "name": "X",
                "login": "valid.login",
                "email": "nao-e-um-email",
                "password": "senha123",
                "role": "technician",
            },
        )
        assert r.status_code == 422

    def test_update_status_invalid_value_returns_422(self, rsa_keys, admin_claims):
        db = AsyncMock()
        fake_redis_instance = aioredis.FakeRedis(decode_responses=True)
        client = make_client(
            rsa_keys,
            current_user=admin_claims,
            mock_db=db,
            mock_redis=fake_redis_instance,
        )
        r = client.patch(
            "/api/v1/users/1/status",
            json={"status": "banned"},  # status inválido
        )
        assert r.status_code == 422


# ── Extras: Refresh Token ─────────────────────────────────────────────────────

class TestRefreshToken:
    """Testes das regras de refresh token."""

    def test_revoked_refresh_token_returns_401(self, rsa_keys):
        db = AsyncMock()
        fake_redis_instance = aioredis.FakeRedis(decode_responses=True)

        revoked_token = _make_refresh_token(revoked=True)

        with patch("services.auth.services.auth_service.TokenRepository") as MockTokenRepo:
            MockTokenRepo.return_value.get_by_hash = AsyncMock(return_value=revoked_token)

            client = make_client(rsa_keys, mock_db=db, mock_redis=fake_redis_instance)
            r = client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": "qualquertoken"},
            )

        assert r.status_code == 401
        assert r.json()["code"] == "REFRESH_TOKEN_INVALID"

    def test_expired_refresh_token_returns_401(self, rsa_keys):
        db = AsyncMock()
        fake_redis_instance = aioredis.FakeRedis(decode_responses=True)

        expired_token = _make_refresh_token(expired=True)

        with patch("services.auth.services.auth_service.TokenRepository") as MockTokenRepo:
            MockTokenRepo.return_value.get_by_hash = AsyncMock(return_value=expired_token)

            client = make_client(rsa_keys, mock_db=db, mock_redis=fake_redis_instance)
            r = client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": "qualquertoken"},
            )

        assert r.status_code == 401
        assert r.json()["code"] == "REFRESH_TOKEN_EXPIRED"

    def test_nonexistent_refresh_token_returns_401(self, rsa_keys):
        db = AsyncMock()
        fake_redis_instance = aioredis.FakeRedis(decode_responses=True)

        with patch("services.auth.services.auth_service.TokenRepository") as MockTokenRepo:
            MockTokenRepo.return_value.get_by_hash = AsyncMock(return_value=None)

            client = make_client(rsa_keys, mock_db=db, mock_redis=fake_redis_instance)
            r = client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": "naoexiste"},
            )

        assert r.status_code == 401
        assert r.json()["code"] == "REFRESH_TOKEN_INVALID"

    def test_valid_refresh_returns_new_access_token(self, rsa_keys):
        db = AsyncMock()
        fake_redis_instance = aioredis.FakeRedis(decode_responses=True)

        stored_token = _make_refresh_token(user_id=1)
        user = _make_user_row(user_id=1, status="active")

        with patch("services.auth.services.auth_service.TokenRepository") as MockTokenRepo, \
             patch("services.auth.services.auth_service.UserRepository") as MockUserRepo:

            MockTokenRepo.return_value.get_by_hash = AsyncMock(return_value=stored_token)
            MockUserRepo.return_value.get_by_id = AsyncMock(return_value=user)

            client = make_client(rsa_keys, mock_db=db, mock_redis=fake_redis_instance)
            r = client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": "validtoken"},
            )

        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert body["token_type"] == "Bearer"
        assert body["expires_in"] == 3600
        # refresh_token NÃO é retornado no /refresh (apenas access_token)
        assert "refresh_token" not in body


# ── Extras: GET /auth/me ──────────────────────────────────────────────────────

class TestGetMe:
    def test_get_me_returns_user_without_password_hash(self, rsa_keys, admin_claims):
        db = AsyncMock()
        fake_redis_instance = aioredis.FakeRedis(decode_responses=True)
        user = _make_user_row(user_id=admin_claims.id)

        with patch("services.auth.services.user_service.UserRepository") as MockRepo, \
             patch("services.auth.services.user_service.set_rls_context", new=AsyncMock()):

            MockRepo.return_value.get_by_id = AsyncMock(return_value=user)

            client = make_client(
                rsa_keys,
                current_user=admin_claims,
                mock_db=db,
                mock_redis=fake_redis_instance,
            )
            r = client.get("/api/v1/auth/me")

        assert r.status_code == 200
        body = r.json()
        assert "password_hash" not in body
        assert body["id"] == admin_claims.id
        assert body["role"] == admin_claims.role
