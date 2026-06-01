"""
Testes E2E — Auth Service.
Requerem PostgreSQL (TEST_DATABASE_URL). Pular com: pytest -m "not e2e"
"""

import pytest

pytestmark = pytest.mark.e2e


class TestLogin:
    async def test_login_valid_credentials_returns_tokens(self, auth_client, seeded_user):
        r = await auth_client.post(
            "/api/v1/auth/login",
            json={"login": seeded_user["login"], "password": seeded_user["password"]},
        )
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "Bearer"
        assert body["expires_in"] == 3600
        assert "password_hash" not in body
        assert "password_hash" not in body.get("user", {})

    async def test_login_wrong_password_returns_401(self, auth_client, seeded_user):
        r = await auth_client.post(
            "/api/v1/auth/login",
            json={"login": seeded_user["login"], "password": "senha_errada"},
        )
        assert r.status_code == 401
        assert r.json()["code"] == "INVALID_CREDENTIALS"

    async def test_login_nonexistent_user_returns_401(self, auth_client):
        r = await auth_client.post(
            "/api/v1/auth/login",
            json={"login": "nao.existe", "password": "qualquer123"},
        )
        assert r.status_code == 401
        assert r.json()["code"] == "INVALID_CREDENTIALS"

    async def test_login_inactive_user_returns_403(self, auth_client, seeded_inactive_user):
        r = await auth_client.post(
            "/api/v1/auth/login",
            json={"login": seeded_inactive_user["login"], "password": seeded_inactive_user["password"]},
        )
        assert r.status_code == 403
        assert r.json()["code"] == "USER_INACTIVE"

    async def test_rate_limit_after_5_failed_attempts_returns_429(self, auth_client):
        for _ in range(5):
            await auth_client.post(
                "/api/v1/auth/login",
                json={"login": "rate.limit.test", "password": "wrong"},
            )
        r = await auth_client.post(
            "/api/v1/auth/login",
            json={"login": "rate.limit.test", "password": "wrong"},
        )
        assert r.status_code == 429
        assert r.json()["code"] == "RATE_LIMIT_EXCEEDED"

    async def test_login_missing_fields_returns_422(self, auth_client):
        r = await auth_client.post("/api/v1/auth/login", json={})
        assert r.status_code == 422


class TestRefreshAndLogout:
    async def test_refresh_token_returns_new_access_token(self, auth_client, seeded_user):
        login_r = await auth_client.post(
            "/api/v1/auth/login",
            json={"login": seeded_user["login"], "password": seeded_user["password"]},
        )
        assert login_r.status_code == 200
        refresh_token = login_r.json()["refresh_token"]

        r = await auth_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert "refresh_token" not in body

    async def test_logout_revokes_refresh_token(self, auth_client, seeded_user, rsa_keys, admin_token):
        login_r = await auth_client.post(
            "/api/v1/auth/login",
            json={"login": seeded_user["login"], "password": seeded_user["password"]},
        )
        refresh_token = login_r.json()["refresh_token"]
        access_token = login_r.json()["access_token"]

        logout_r = await auth_client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert logout_r.status_code == 204

        r = await auth_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert r.status_code == 401
        assert r.json()["code"] == "REFRESH_TOKEN_INVALID"

    async def test_invalid_refresh_token_returns_401(self, auth_client):
        r = await auth_client.post("/api/v1/auth/refresh", json={"refresh_token": "token.invalido"})
        assert r.status_code == 401
        assert r.json()["code"] == "REFRESH_TOKEN_INVALID"


class TestGetMe:
    async def test_get_me_returns_user_data(self, auth_client_admin, seeded_user):
        r = await auth_client_admin.get("/api/v1/auth/me")
        assert r.status_code == 200
        body = r.json()
        assert "id" in body
        assert "role" in body
        assert "password_hash" not in body

    async def test_get_me_without_token_returns_401(self, auth_client):
        r = await auth_client.get("/api/v1/auth/me")
        assert r.status_code == 401


class TestUserManagement:
    async def test_admin_can_create_user(self, auth_client_admin):
        r = await auth_client_admin.post(
            "/api/v1/users",
            json={
                "name": "Novo Técnico",
                "login": "novo.tecnico",
                "email": "novo.tecnico@test.com",
                "password": "senha12345",
                "role": "technician",
            },
        )
        assert r.status_code == 201
        body = r.json()
        assert body["login"] == "novo.tecnico"
        assert body["role"] == "technician"
        assert "password_hash" not in body

    async def test_supervisor_cannot_create_user_403(self, auth_client_supervisor):
        r = await auth_client_supervisor.post(
            "/api/v1/users",
            json={
                "name": "X",
                "login": "x.user",
                "email": "x@test.com",
                "password": "senha12345",
                "role": "technician",
            },
        )
        assert r.status_code == 403

    async def test_admin_can_list_users(self, auth_client_admin):
        r = await auth_client_admin.get("/api/v1/users")
        assert r.status_code == 200
        body = r.json()
        assert "items" in body
        assert "total" in body

    async def test_supervisor_cannot_list_users_403(self, auth_client_supervisor):
        r = await auth_client_supervisor.get("/api/v1/users")
        assert r.status_code == 403

    async def test_create_user_duplicate_login_returns_409(self, auth_client_admin, seeded_user):
        r = await auth_client_admin.post(
            "/api/v1/users",
            json={
                "name": "Dup",
                "login": seeded_user["login"],
                "email": "outro.email@test.com",
                "password": "senha12345",
                "role": "technician",
            },
        )
        assert r.status_code == 409
        assert r.json()["code"] == "LOGIN_ALREADY_EXISTS"

    async def test_admin_can_update_user_status(self, auth_client_admin, seeded_user):
        r = await auth_client_admin.patch(
            f"/api/v1/users/{seeded_user['id']}/status",
            json={"status": "inactive"},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "inactive"

    async def test_create_user_invalid_role_returns_422(self, auth_client_admin):
        r = await auth_client_admin.post(
            "/api/v1/users",
            json={
                "name": "X",
                "login": "inv.role",
                "email": "inv@test.com",
                "password": "senha12345",
                "role": "superadmin",
            },
        )
        assert r.status_code == 422
