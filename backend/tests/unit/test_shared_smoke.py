"""
Smoke tests da Phase 0 — validam shared/ antes de qualquer serviço ser implementado.
Cobrem: JWT, RBAC, paginação, BusinessError, envelope de erro, hash de token.
"""

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared.shared.auth.dependencies import UserClaims, get_current_user, require_roles
from shared.shared.auth.jwt import (
    create_access_token,
    create_refresh_token_value,
    hash_token,
    verify_token,
)
from shared.shared.exceptions.handlers import BusinessError, setup_exception_handlers
from shared.shared.schemas.pagination import PaginatedResponse


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def keys():
    pk = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv = pk.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ).decode()
    pub = pk.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return {"private": priv, "public": pub}


# ── JWT RS256 ─────────────────────────────────────────────────────────────────

def test_jwt_sign_and_verify(keys):
    token = create_access_token(
        {"sub": "42", "role": "supervisor", "name": "João"},
        keys["private"],
    )
    payload = verify_token(token, keys["public"])
    assert payload["sub"] == "42"
    assert payload["role"] == "supervisor"
    assert "exp" in payload
    assert "iat" in payload


def test_jwt_wrong_key_raises(keys):
    import jwt as pyjwt

    other_pk = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_pub = other_pk.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    token = create_access_token({"sub": "1", "role": "admin", "name": "X"}, keys["private"])
    with pytest.raises(pyjwt.InvalidTokenError):
        verify_token(token, other_pub)


# ── Hash de refresh token ─────────────────────────────────────────────────────

def test_hash_token_is_sha256():
    raw = create_refresh_token_value()
    hashed = hash_token(raw)
    assert hashed != raw
    assert len(hashed) == 64  # sha256 hex
    assert hash_token(raw) == hash_token(raw)  # determinístico


def test_refresh_token_unique():
    assert create_refresh_token_value() != create_refresh_token_value()


# ── PaginatedResponse ─────────────────────────────────────────────────────────

def test_paginated_response_pages():
    r = PaginatedResponse.build(items=list(range(20)), total=55, page=2, page_size=20)
    assert r.pages == 3
    assert r.total == 55
    assert r.page == 2
    assert len(r.items) == 20


def test_paginated_response_empty():
    r = PaginatedResponse.build(items=[], total=0, page=1, page_size=20)
    assert r.pages == 0
    assert r.items == []


# ── BusinessError ─────────────────────────────────────────────────────────────

def test_business_error_fields():
    err = BusinessError("ORDER_NOT_FOUND", 404, "Ordem não encontrada", "id")
    assert err.code == "ORDER_NOT_FOUND"
    assert err.status_code == 404
    assert err.field == "id"
    assert str(err) == "Ordem não encontrada"


def test_business_error_no_field():
    err = BusinessError("INTERNAL", 500, "Erro")
    assert err.field is None


# ── Exception handlers via FastAPI ────────────────────────────────────────────

@pytest.fixture(scope="module")
def test_app():
    app = FastAPI()
    setup_exception_handlers(app)

    @app.get("/business")
    async def _business():
        raise BusinessError("ORDER_CLOSED", 400, "OS encerrada", "order_id")

    @app.get("/business-no-field")
    async def _business_no_field():
        raise BusinessError("GENERAL", 422, "Erro geral")

    @app.get("/crash")
    async def _crash():
        raise RuntimeError("Boom")

    @app.post("/validation")
    async def _validation(body: dict):
        pass

    return TestClient(app, raise_server_exceptions=False)


def test_handler_business_error_envelope(test_app):
    r = test_app.get("/business")
    assert r.status_code == 400
    body = r.json()
    assert body["code"] == "ORDER_CLOSED"
    assert body["detail"] == "OS encerrada"
    assert body["field"] == "order_id"


def test_handler_business_error_no_field(test_app):
    r = test_app.get("/business-no-field")
    assert r.status_code == 422
    body = r.json()
    assert "field" not in body or body.get("field") is None


def test_handler_500_no_stack_trace(test_app):
    r = test_app.get("/crash")
    assert r.status_code == 500
    body = r.json()
    assert body["code"] == "INTERNAL_ERROR"
    assert "Traceback" not in r.text
    assert "RuntimeError" not in r.text
    assert "Boom" not in r.text


# ── RBAC: require_roles ───────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def rbac_app(keys):
    from fastapi import Depends

    from shared.shared.config import SharedSettings, get_shared_settings

    app = FastAPI()
    setup_exception_handlers(app)

    app.dependency_overrides[get_shared_settings] = lambda: SharedSettings(
        jwt_public_key=keys["public"]
    )

    @app.get("/admin-only")
    async def _admin(_: None = Depends(require_roles(["admin"]))):
        return {"ok": True}

    @app.get("/multi-role")
    async def _multi(_: None = Depends(require_roles(["admin", "supervisor"]))):
        return {"ok": True}

    return app


def test_rbac_admin_allowed(rbac_app, keys):
    token = create_access_token({"sub": "1", "role": "admin", "name": "A"}, keys["private"])
    client = TestClient(rbac_app)
    r = client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


def test_rbac_technician_denied(rbac_app, keys):
    token = create_access_token({"sub": "3", "role": "technician", "name": "T"}, keys["private"])
    client = TestClient(rbac_app, raise_server_exceptions=False)
    r = client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_rbac_supervisor_allowed_multi(rbac_app, keys):
    token = create_access_token({"sub": "2", "role": "supervisor", "name": "S"}, keys["private"])
    client = TestClient(rbac_app)
    r = client.get("/multi-role", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


def test_rbac_attendant_denied_multi(rbac_app, keys):
    token = create_access_token({"sub": "4", "role": "attendant", "name": "At"}, keys["private"])
    client = TestClient(rbac_app, raise_server_exceptions=False)
    r = client.get("/multi-role", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_rbac_no_token(rbac_app):
    client = TestClient(rbac_app, raise_server_exceptions=False)
    r = client.get("/admin-only")
    assert r.status_code == 403  # HTTPBearer sem credenciais retorna 403 no FastAPI (auto_error=True)


def test_rbac_invalid_token(rbac_app):
    client = TestClient(rbac_app, raise_server_exceptions=False)
    r = client.get("/admin-only", headers={"Authorization": "Bearer token.invalido.aqui"})
    assert r.status_code == 401
