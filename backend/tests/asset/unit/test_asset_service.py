"""
Testes unitários — Asset Service
ASSET-01: RBAC correto por endpoint
ASSET-02: 404 para asset não encontrado
ASSET-03: 409 para serial_number duplicado
ASSET-04: Filtros de listagem
ASSET-05: Validações de input
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from shared.shared.auth.dependencies import UserClaims
from shared.shared.exceptions.handlers import BusinessError

from services.asset.schemas.asset import (
    AssetFilters,
    CreateAssetRequest,
    UpdateAssetRequest,
    UpdateAssetStatusRequest,
)
from services.asset.services.asset_service import AssetService


def _make_asset(
    asset_id: int = 1,
    name: str = "Compressor A",
    status: str = "active",
    serial_number: str | None = None,
):
    asset = MagicMock()
    asset.id = asset_id
    asset.name = name
    asset.model = "M100"
    asset.manufacturer = "ACME"
    asset.serial_number = serial_number
    asset.location = "Sala 1"
    asset.status = status
    asset.created_at = datetime.now(timezone.utc)
    asset.updated_at = datetime.now(timezone.utc)
    return asset


def _make_user(role: str = "admin") -> UserClaims:
    return UserClaims(id=1, role=role, name="Test User")


# ─── ASSET-01: RBAC via TestClient ──────────────────────────────────────────

class TestRBAC:
    """RBAC correto em cada endpoint"""

    def test_technician_cannot_create_asset(self, rsa_keys, mock_db):
        from tests.asset.conftest import make_client
        from tests.asset.conftest import UserClaims as UC
        tech = UserClaims(id=3, role="technician", name="Tech")
        client = make_client(rsa_keys, current_user=tech, mock_db=mock_db)
        resp = client.post("/api/v1/assets", json={"name": "X"})
        assert resp.status_code == 403

    def test_attendant_cannot_create_asset(self, rsa_keys, mock_db):
        from tests.asset.conftest import make_client
        att = UserClaims(id=4, role="attendant", name="Att")
        client = make_client(rsa_keys, current_user=att, mock_db=mock_db)
        resp = client.post("/api/v1/assets", json={"name": "X"})
        assert resp.status_code == 403

    def test_technician_cannot_update_asset(self, rsa_keys, mock_db):
        from tests.asset.conftest import make_client
        tech = UserClaims(id=3, role="technician", name="Tech")
        client = make_client(rsa_keys, current_user=tech, mock_db=mock_db)
        resp = client.put("/api/v1/assets/1", json={"name": "Y"})
        assert resp.status_code == 403

    def test_attendant_cannot_change_status(self, rsa_keys, mock_db):
        from tests.asset.conftest import make_client
        att = UserClaims(id=4, role="attendant", name="Att")
        client = make_client(rsa_keys, current_user=att, mock_db=mock_db)
        resp = client.patch("/api/v1/assets/1/status", json={"status": "inactive"})
        assert resp.status_code == 403

    def test_technician_can_list_assets(self, rsa_keys, mock_db):
        from tests.asset.conftest import make_client
        tech = UserClaims(id=3, role="technician", name="Tech")

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 0
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        client = make_client(rsa_keys, current_user=tech, mock_db=mock_db)
        resp = client.get("/api/v1/assets")
        assert resp.status_code == 200

    def test_attendant_can_get_asset_by_id(self, rsa_keys, mock_db):
        from tests.asset.conftest import make_client
        att = UserClaims(id=4, role="attendant", name="Att")

        asset = _make_asset()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = asset
        mock_db.execute = AsyncMock(return_value=mock_result)

        client = make_client(rsa_keys, current_user=att, mock_db=mock_db)
        resp = client.get("/api/v1/assets/1")
        assert resp.status_code == 200


# ─── ASSET-02: 404 para asset não encontrado ────────────────────────────────

class TestAssetNotFound:
    @pytest.mark.asyncio
    async def test_get_nonexistent_asset_raises_404(self):
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        user = _make_user("admin")
        service = AssetService(db, user)

        with pytest.raises(BusinessError) as exc:
            await service.get_asset(999)

        assert exc.value.code == "ASSET_NOT_FOUND"
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_nonexistent_asset_raises_404(self):
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        user = _make_user("supervisor")
        service = AssetService(db, user)

        with pytest.raises(BusinessError) as exc:
            await service.update_asset(999, UpdateAssetRequest())

        assert exc.value.code == "ASSET_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_update_status_nonexistent_asset_raises_404(self):
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        user = _make_user("admin")
        service = AssetService(db, user)

        with pytest.raises(BusinessError) as exc:
            await service.update_asset_status(999, UpdateAssetStatusRequest(status="inactive"))

        assert exc.value.code == "ASSET_NOT_FOUND"


# ─── ASSET-03: serial_number duplicado → 409 ────────────────────────────────

class TestSerialNumberDuplicate:
    def test_duplicate_serial_number_returns_409(self, rsa_keys, mock_db):
        from tests.asset.conftest import make_client
        from sqlalchemy.exc import IntegrityError

        admin = UserClaims(id=1, role="admin", name="Admin")

        async def raise_integrity(*args, **kwargs):
            raise IntegrityError(
                statement="INSERT",
                params={},
                orig=Exception("duplicate key value violates unique constraint \"assets_serial_number_key\""),
            )

        mock_db.flush = AsyncMock(side_effect=raise_integrity)

        client = make_client(rsa_keys, current_user=admin, mock_db=mock_db)
        resp = client.post(
            "/api/v1/assets",
            json={"name": "Compressor B", "serial_number": "SN-001"},
        )
        assert resp.status_code == 409
        assert resp.json()["code"] == "SERIAL_NUMBER_ALREADY_EXISTS"


# ─── ASSET-04: Filtros de listagem ──────────────────────────────────────────

class TestListFilters:
    @pytest.mark.asyncio
    async def test_list_returns_paginated_response(self):
        # set_rls_context faz 2 chamadas, depois list faz count + items = 4 total
        db = AsyncMock()

        rls_mock = MagicMock()
        count_result = MagicMock()
        count_result.scalar_one.return_value = 2

        asset1 = _make_asset(1, "Compressor A")
        asset2 = _make_asset(2, "Motor B")
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = [asset1, asset2]

        db.execute = AsyncMock(side_effect=[rls_mock, rls_mock, count_result, items_result])

        user = _make_user("supervisor")
        service = AssetService(db, user)

        result = await service.list_assets(AssetFilters(page=1, page_size=20))

        assert result.total == 2
        assert result.page == 1
        assert result.pages == 1
        assert len(result.items) == 2

    @pytest.mark.asyncio
    async def test_empty_list_returns_zero_pages(self):
        db = AsyncMock()

        rls_mock = MagicMock()
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = []

        db.execute = AsyncMock(side_effect=[rls_mock, rls_mock, count_result, items_result])

        user = _make_user("admin")
        service = AssetService(db, user)

        result = await service.list_assets(AssetFilters(page=1, page_size=20))

        assert result.total == 0
        assert result.pages == 0
        assert result.items == []


# ─── ASSET-05: Validações de input ──────────────────────────────────────────

class TestInputValidation:
    def test_empty_name_returns_422(self, rsa_keys, mock_db):
        from tests.asset.conftest import make_client
        admin = UserClaims(id=1, role="admin", name="Admin")
        client = make_client(rsa_keys, current_user=admin, mock_db=mock_db)
        resp = client.post("/api/v1/assets", json={"name": "  "})
        assert resp.status_code == 422

    def test_missing_name_returns_422(self, rsa_keys, mock_db):
        from tests.asset.conftest import make_client
        admin = UserClaims(id=1, role="admin", name="Admin")
        client = make_client(rsa_keys, current_user=admin, mock_db=mock_db)
        resp = client.post("/api/v1/assets", json={})
        assert resp.status_code == 422
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_invalid_status_returns_422(self, rsa_keys, mock_db):
        from tests.asset.conftest import make_client
        admin = UserClaims(id=1, role="admin", name="Admin")
        client = make_client(rsa_keys, current_user=admin, mock_db=mock_db)
        resp = client.patch("/api/v1/assets/1/status", json={"status": "disabled"})
        assert resp.status_code == 422

    def test_create_asset_with_all_fields(self, rsa_keys, mock_db):
        from tests.asset.conftest import make_client
        admin = UserClaims(id=1, role="admin", name="Admin")

        # set_rls faz 2 executes, get_by_id (no refresh) faz 1 execute
        asset = _make_asset(serial_number="SN-123")
        rls_mock = MagicMock()
        get_result = MagicMock()
        get_result.scalar_one_or_none.return_value = asset

        mock_db.execute = AsyncMock(side_effect=[rls_mock, rls_mock, get_result])

        now = datetime.now(timezone.utc)

        async def refresh_asset(obj):
            obj.id = 1
            obj.status = "active"
            obj.created_at = now
            obj.updated_at = now

        mock_db.refresh = AsyncMock(side_effect=refresh_asset)

        client = make_client(rsa_keys, current_user=admin, mock_db=mock_db)
        resp = client.post(
            "/api/v1/assets",
            json={
                "name": "Compressor A",
                "model": "M100",
                "manufacturer": "ACME",
                "serial_number": "SN-123",
                "location": "Sala 1",
            },
        )
        assert resp.status_code == 201
