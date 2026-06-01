"""
Testes adicionais para aumentar cobertura do Inventory Service.
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from shared.shared.auth.dependencies import UserClaims
from services.inventory.schemas.inventory import MaterialFilters, MovementFilters
from services.inventory.services.inventory_service import InventoryService


def _make_material(quantity=10.0, min_quantity=5.0, status="active"):
    m = MagicMock()
    m.id = 1
    m.name = "Parafuso"
    m.sku = "PAR-001"
    m.unit_price = Decimal("2.50")
    m.quantity_in_stock = Decimal(str(quantity))
    m.min_quantity = Decimal(str(min_quantity))
    m.status = status
    m.created_at = datetime.now(timezone.utc)
    m.updated_at = datetime.now(timezone.utc)
    return m


def _make_movement():
    m = MagicMock()
    m.id = 1
    m.material_id = 1
    m.service_order_id = None
    m.movement_type = "in"
    m.quantity = Decimal("5.0")
    m.notes = None
    m.created_at = datetime.now(timezone.utc)
    return m


def _make_user(role="admin"):
    return UserClaims(id=1, role=role, name="Test")


class TestInventoryCoverage:

    @pytest.mark.asyncio
    async def test_list_movements_empty(self):
        db = AsyncMock()
        redis = AsyncMock()
        user = _make_user("supervisor")

        rls = MagicMock()
        count_r = MagicMock()
        count_r.scalar_one.return_value = 0
        items_r = MagicMock()
        items_r.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(side_effect=[rls, rls, count_r, items_r])

        service = InventoryService(db, redis, user)
        result = await service.list_movements(MovementFilters(page=1, page_size=20))
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_list_movements_with_data(self):
        db = AsyncMock()
        redis = AsyncMock()
        user = _make_user("supervisor")

        mv = _make_movement()
        rls = MagicMock()
        count_r = MagicMock()
        count_r.scalar_one.return_value = 1
        items_r = MagicMock()
        items_r.scalars.return_value.all.return_value = [mv]
        db.execute = AsyncMock(side_effect=[rls, rls, count_r, items_r])

        service = InventoryService(db, redis, user)
        result = await service.list_movements(MovementFilters(page=1, page_size=20))
        assert result.total == 1

    @pytest.mark.asyncio
    async def test_get_stock_report(self):
        db = AsyncMock()
        redis = AsyncMock()
        user = _make_user("admin")

        m1 = _make_material(quantity=3.0, min_quantity=5.0)  # low stock
        m2 = _make_material(quantity=10.0, min_quantity=5.0)  # normal stock

        rls = MagicMock()
        materials_r = MagicMock()
        materials_r.scalars.return_value.all.return_value = [m1, m2]
        db.execute = AsyncMock(side_effect=[rls, rls, materials_r])

        service = InventoryService(db, redis, user)
        report = await service.get_stock_report()
        assert len(report) == 2
        low_stock_items = [r for r in report if r.is_low_stock]
        assert len(low_stock_items) == 1

    @pytest.mark.asyncio
    async def test_create_material_success(self):
        db = AsyncMock()
        redis = AsyncMock()
        user = _make_user()

        material = _make_material()
        rls = MagicMock()
        mat_result = MagicMock()
        mat_result.scalar_one_or_none.return_value = material

        async def refresh_mat(obj):
            obj.id = 1
            obj.status = "active"
            obj.quantity_in_stock = Decimal("0.000")
            obj.min_quantity = Decimal("5.000")
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)

        db.execute = AsyncMock(side_effect=[rls, rls, mat_result])
        db.refresh = AsyncMock(side_effect=refresh_mat)

        from services.inventory.schemas.inventory import CreateMaterialRequest
        service = InventoryService(db, redis, user)
        result = await service.create_material(
            CreateMaterialRequest(name="Parafuso M8", sku="PAR-M8", unit_price=2.5)
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_update_material_success(self):
        db = AsyncMock()
        redis = AsyncMock()
        user = _make_user("supervisor")

        material = _make_material()
        rls = MagicMock()
        mat_result = MagicMock()
        mat_result.scalar_one_or_none.return_value = material
        db.execute = AsyncMock(side_effect=[
            rls, rls, mat_result, MagicMock(), mat_result
        ])

        from services.inventory.schemas.inventory import UpdateMaterialRequest
        service = InventoryService(db, redis, user)
        result = await service.update_material(1, UpdateMaterialRequest(name="Parafuso M10"))
        assert result is not None

    @pytest.mark.asyncio
    async def test_update_material_status_success(self):
        db = AsyncMock()
        redis = AsyncMock()
        user = _make_user()

        material = _make_material()
        inactive = _make_material(status="inactive")
        rls = MagicMock()
        mat_result = MagicMock()
        mat_result.scalar_one_or_none.return_value = material
        inactive_result = MagicMock()
        inactive_result.scalar_one_or_none.return_value = inactive
        db.execute = AsyncMock(side_effect=[rls, rls, mat_result, MagicMock(), inactive_result])

        from services.inventory.schemas.inventory import UpdateMaterialStatusRequest
        service = InventoryService(db, redis, user)
        result = await service.update_material_status(1, UpdateMaterialStatusRequest(status="inactive"))
        assert result.status == "inactive"
