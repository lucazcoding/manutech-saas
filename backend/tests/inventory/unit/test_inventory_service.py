"""
Testes unitários — Inventory Service
INV-01: RBAC por endpoint
INV-02: Material não encontrado → 404
INV-03: SKU duplicado → 409
INV-04: Insufficient stock → 400 (bloqueado pelo trigger)
INV-05: stock.low_alert publicado ao atingir min_quantity
INV-06: Validações de input
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from shared.shared.auth.dependencies import UserClaims
from shared.shared.exceptions.handlers import BusinessError

from services.inventory.schemas.inventory import (
    CreateMovementRequest,
    MaterialFilters,
    MovementFilters,
)
from services.inventory.services.inventory_service import InventoryService


def _make_material(
    material_id: int = 1,
    quantity: float = 10.0,
    min_quantity: float = 5.0,
    status: str = "active",
    sku: str = "MAT-001",
):
    m = MagicMock()
    m.id = material_id
    m.name = "Parafuso M8"
    m.sku = sku
    m.unit_price = Decimal("2.50")
    m.quantity_in_stock = Decimal(str(quantity))
    m.min_quantity = Decimal(str(min_quantity))
    m.status = status
    m.created_at = datetime.now(timezone.utc)
    m.updated_at = datetime.now(timezone.utc)
    return m


def _make_movement(movement_id: int = 1):
    m = MagicMock()
    m.id = movement_id
    m.material_id = 1
    m.service_order_id = None
    m.movement_type = "out"
    m.quantity = Decimal("3.0")
    m.notes = None
    m.created_at = datetime.now(timezone.utc)
    return m


def _make_user(role: str = "admin") -> UserClaims:
    return UserClaims(id=1, role=role, name="Test User")


# ─── INV-01: RBAC ────────────────────────────────────────────────────────────

class TestRBAC:
    def test_supervisor_cannot_change_material_status(self, rsa_keys, mock_db, fake_redis):
        from tests.inventory.conftest import make_client
        sup = UserClaims(id=2, role="supervisor", name="Sup")
        client = make_client(rsa_keys, current_user=sup, mock_db=mock_db, mock_redis=fake_redis)
        resp = client.patch("/api/v1/materials/1/status", json={"status": "inactive"})
        assert resp.status_code == 403

    def test_technician_cannot_create_material(self, rsa_keys, mock_db, fake_redis):
        from tests.inventory.conftest import make_client
        tech = UserClaims(id=3, role="technician", name="Tech")
        client = make_client(rsa_keys, current_user=tech, mock_db=mock_db, mock_redis=fake_redis)
        resp = client.post(
            "/api/v1/materials",
            json={"name": "Parafuso", "sku": "X", "unit_price": 1.0},
        )
        assert resp.status_code == 403

    def test_attendant_cannot_create_movement(self, rsa_keys, mock_db, fake_redis):
        from tests.inventory.conftest import make_client
        att = UserClaims(id=4, role="attendant", name="Att")
        client = make_client(rsa_keys, current_user=att, mock_db=mock_db, mock_redis=fake_redis)
        resp = client.post(
            "/api/v1/movements",
            json={"material_id": 1, "movement_type": "out", "quantity": 1},
        )
        assert resp.status_code == 403

    def test_attendant_cannot_list_movements(self, rsa_keys, mock_db, fake_redis):
        from tests.inventory.conftest import make_client
        att = UserClaims(id=4, role="attendant", name="Att")
        client = make_client(rsa_keys, current_user=att, mock_db=mock_db, mock_redis=fake_redis)
        resp = client.get("/api/v1/movements")
        assert resp.status_code == 403

    def test_technician_can_list_materials(self, rsa_keys, mock_db, fake_redis):
        from tests.inventory.conftest import make_client
        tech = UserClaims(id=3, role="technician", name="Tech")

        rls = MagicMock()
        count_r = MagicMock()
        count_r.scalar_one.return_value = 0
        items_r = MagicMock()
        items_r.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(side_effect=[rls, rls, count_r, items_r])

        client = make_client(rsa_keys, current_user=tech, mock_db=mock_db, mock_redis=fake_redis)
        resp = client.get("/api/v1/materials")
        assert resp.status_code == 200


# ─── INV-02: Material não encontrado ─────────────────────────────────────────

class TestMaterialNotFound:
    @pytest.mark.asyncio
    async def test_get_nonexistent_material_raises_404(self):
        db = AsyncMock()
        redis = AsyncMock()
        rls = MagicMock()
        not_found = MagicMock()
        not_found.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(side_effect=[rls, rls, not_found])

        user = _make_user("admin")
        service = InventoryService(db, redis, user)

        with pytest.raises(BusinessError) as exc:
            await service.get_material(999)

        assert exc.value.code == "MATERIAL_NOT_FOUND"
        assert exc.value.status_code == 404


# ─── INV-03: SKU duplicado ───────────────────────────────────────────────────

class TestSKUDuplicate:
    def test_duplicate_sku_returns_409(self, rsa_keys, mock_db, fake_redis):
        from tests.inventory.conftest import make_client
        from sqlalchemy.exc import IntegrityError

        admin = UserClaims(id=1, role="admin", name="Admin")

        async def raise_integrity(*args, **kwargs):
            raise IntegrityError(
                statement="INSERT",
                params={},
                orig=Exception('duplicate key value violates unique constraint "materials_sku_key"'),
            )

        mock_db.flush = AsyncMock(side_effect=raise_integrity)

        client = make_client(rsa_keys, current_user=admin, mock_db=mock_db, mock_redis=fake_redis)
        resp = client.post(
            "/api/v1/materials",
            json={"name": "Parafuso", "sku": "DUPE", "unit_price": 1.0},
        )
        assert resp.status_code == 409
        assert resp.json()["code"] == "SKU_ALREADY_EXISTS"


# ─── INV-04: Insufficient stock ──────────────────────────────────────────────

class TestInsufficientStock:
    @pytest.mark.asyncio
    async def test_insufficient_stock_raises_400(self):
        db = AsyncMock()
        redis = AsyncMock()
        user = _make_user("supervisor")

        material = _make_material(quantity=1.0)
        rls = MagicMock()
        mat_result = MagicMock()
        mat_result.scalar_one_or_none.return_value = material

        async def flush_raises():
            raise Exception("Estoque insuficiente para material 1: saldo 1.000 - saída 5.000 = -4.000")

        db.execute = AsyncMock(side_effect=[rls, rls, mat_result])
        db.flush = AsyncMock(side_effect=flush_raises)

        service = InventoryService(db, redis, user)

        with pytest.raises(BusinessError) as exc:
            await service.create_movement(
                CreateMovementRequest(material_id=1, movement_type="out", quantity=5.0)
            )

        assert exc.value.code == "INSUFFICIENT_STOCK"
        assert exc.value.status_code == 400


# ─── INV-05: stock.low_alert ─────────────────────────────────────────────────

class TestLowStockAlert:
    @pytest.mark.asyncio
    async def test_low_stock_publishes_event(self, fake_redis):
        db = AsyncMock()
        user = _make_user("supervisor")

        material_before = _make_material(quantity=10.0, min_quantity=5.0)
        material_after = _make_material(quantity=4.0, min_quantity=5.0)  # below min
        movement = _make_movement()

        rls = MagicMock()
        mat_result = MagicMock()
        mat_result.scalar_one_or_none.return_value = material_before
        mat_after_result = MagicMock()
        mat_after_result.scalar_one_or_none.return_value = material_after
        mov_result = MagicMock()
        mov_result.scalar_one_or_none.return_value = movement

        db.execute = AsyncMock(side_effect=[rls, rls, mat_result, mat_after_result])
        db.refresh = AsyncMock(side_effect=lambda obj: None)

        # Mock movement creation to succeed
        with patch(
            "services.inventory.repositories.inventory_repository.MovementRepository.create",
            new_callable=AsyncMock,
            return_value=movement,
        ):
            with patch(
                "services.inventory.services.inventory_service.publish_event",
                new_callable=AsyncMock,
            ) as mock_pub:
                service = InventoryService(db, fake_redis, user)
                await service.create_movement(
                    CreateMovementRequest(material_id=1, movement_type="out", quantity=6.0)
                )
                mock_pub.assert_called_once()
                assert mock_pub.call_args[0][1] == "stock.low_alert"

    @pytest.mark.asyncio
    async def test_no_alert_when_stock_above_min(self, fake_redis):
        db = AsyncMock()
        user = _make_user("supervisor")

        material = _make_material(quantity=10.0, min_quantity=5.0)
        movement = _make_movement()

        rls = MagicMock()
        mat_result = MagicMock()
        mat_result.scalar_one_or_none.return_value = material

        db.execute = AsyncMock(side_effect=[rls, rls, mat_result, mat_result])

        with patch(
            "services.inventory.repositories.inventory_repository.MovementRepository.create",
            new_callable=AsyncMock,
            return_value=movement,
        ):
            with patch(
                "services.inventory.services.inventory_service.publish_event",
                new_callable=AsyncMock,
            ) as mock_pub:
                service = InventoryService(db, fake_redis, user)
                await service.create_movement(
                    CreateMovementRequest(material_id=1, movement_type="out", quantity=3.0)
                )
                mock_pub.assert_not_called()


# ─── INV-06: Validações ──────────────────────────────────────────────────────

class TestInputValidation:
    def test_negative_unit_price_returns_422(self, rsa_keys, mock_db, fake_redis):
        from tests.inventory.conftest import make_client
        admin = UserClaims(id=1, role="admin", name="Admin")
        client = make_client(rsa_keys, current_user=admin, mock_db=mock_db, mock_redis=fake_redis)
        resp = client.post(
            "/api/v1/materials",
            json={"name": "Mat", "sku": "X", "unit_price": -1.0},
        )
        assert resp.status_code == 422

    def test_zero_quantity_movement_returns_422(self, rsa_keys, mock_db, fake_redis):
        from tests.inventory.conftest import make_client
        sup = UserClaims(id=2, role="supervisor", name="Sup")
        client = make_client(rsa_keys, current_user=sup, mock_db=mock_db, mock_redis=fake_redis)
        resp = client.post(
            "/api/v1/movements",
            json={"material_id": 1, "movement_type": "out", "quantity": 0},
        )
        assert resp.status_code == 422

    def test_invalid_movement_type_returns_422(self, rsa_keys, mock_db, fake_redis):
        from tests.inventory.conftest import make_client
        sup = UserClaims(id=2, role="supervisor", name="Sup")
        client = make_client(rsa_keys, current_user=sup, mock_db=mock_db, mock_redis=fake_redis)
        resp = client.post(
            "/api/v1/movements",
            json={"material_id": 1, "movement_type": "transfer", "quantity": 1},
        )
        assert resp.status_code == 422
