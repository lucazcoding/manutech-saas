"""
Testes adicionais para aumentar cobertura do Order Service.
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from shared.shared.auth.dependencies import UserClaims
from shared.shared.exceptions.handlers import BusinessError

from services.order.schemas.order import (
    CreateOrderRequest,
    OrderFilters,
    UpdateOrderRequest,
)
from services.order.services.order_service import OrderService


def _make_order(order_id=1, status="open", asset_id=None):
    o = MagicMock()
    o.id = order_id
    o.order_number = 1001
    o.client_name = "X"
    o.location = "Y"
    o.description = None
    o.status = status
    o.priority = "medium"
    o.total_cost = Decimal("0.00")
    o.start_date = None
    o.asset_id = asset_id
    o.created_at = datetime.now(timezone.utc)
    o.updated_at = datetime.now(timezone.utc)
    return o


def _make_response(order):
    from services.order.schemas.order import OrderResponse
    return OrderResponse(
        id=order.id,
        order_number=order.order_number,
        client_name=order.client_name,
        location=order.location,
        description=order.description,
        status=order.status,
        priority=order.priority,
        total_cost=order.total_cost,
        start_date=order.start_date,
        asset=None,
        assigned_technician=None,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


def _make_user(role="supervisor"):
    return UserClaims(id=2, role=role, name="Test")


class TestOrderServiceCoverage:

    @pytest.mark.asyncio
    async def test_delete_order_success(self):
        db = AsyncMock()
        redis = AsyncMock()
        user = _make_user()

        order = _make_order()
        rls = MagicMock()
        order_result = MagicMock()
        order_result.scalar_one_or_none.return_value = order
        delete_result = MagicMock()

        db.execute = AsyncMock(side_effect=[rls, rls, order_result, delete_result])

        service = OrderService(db, redis, user)
        await service.delete_order(1)

    @pytest.mark.asyncio
    async def test_delete_nonexistent_order_raises_404(self):
        db = AsyncMock()
        redis = AsyncMock()
        user = _make_user()

        rls = MagicMock()
        not_found = MagicMock()
        not_found.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(side_effect=[rls, rls, not_found])

        service = OrderService(db, redis, user)
        with pytest.raises(BusinessError) as exc:
            await service.delete_order(999)
        assert exc.value.code == "ORDER_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_list_orders_applies_filters(self):
        db = AsyncMock()
        redis = AsyncMock()
        user = _make_user("admin")

        order = _make_order()
        rls = MagicMock()
        count_r = MagicMock()
        count_r.scalar_one.return_value = 1
        items_r = MagicMock()
        items_r.scalars.return_value.all.return_value = [order]

        # _build_order_response calls: asset lookup + assignment lookup
        no_asset = MagicMock()
        no_asset.scalar_one_or_none.return_value = None
        no_assign = MagicMock()
        no_assign.scalar_one_or_none.return_value = None

        db.execute = AsyncMock(side_effect=[
            rls, rls, count_r, items_r, no_asset, no_assign
        ])

        service = OrderService(db, redis, user)
        filters = OrderFilters(status="open", page=1, page_size=20)
        result = await service.list_orders(filters)
        assert result.total == 1
        assert result.pages == 1

    @pytest.mark.asyncio
    async def test_get_history_for_existing_order(self):
        db = AsyncMock()
        redis = AsyncMock()
        user = _make_user("admin")

        order = _make_order()
        rls = MagicMock()
        order_result = MagicMock()
        order_result.scalar_one_or_none.return_value = order

        history_result = MagicMock()
        history_result.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(side_effect=[rls, rls, order_result, history_result])

        service = OrderService(db, redis, user)
        history = await service.get_history(1)
        assert history == []

    @pytest.mark.asyncio
    async def test_list_attachments_for_existing_order(self):
        db = AsyncMock()
        redis = AsyncMock()
        user = _make_user("technician")

        order = _make_order()
        rls = MagicMock()
        order_result = MagicMock()
        order_result.scalar_one_or_none.return_value = order
        attach_result = MagicMock()
        attach_result.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(side_effect=[rls, rls, order_result, attach_result])

        service = OrderService(db, redis, user)
        attachments = await service.list_attachments(1)
        assert attachments == []

    @pytest.mark.asyncio
    async def test_list_orders_by_asset(self):
        db = AsyncMock()
        redis = AsyncMock()
        user = _make_user("admin")

        order = _make_order(asset_id=5)
        rls = MagicMock()
        count_r = MagicMock()
        count_r.scalar_one.return_value = 1
        items_r = MagicMock()
        items_r.scalars.return_value.all.return_value = [order]
        no_asset = MagicMock()
        no_asset.scalar_one_or_none.return_value = None
        no_assign = MagicMock()
        no_assign.scalar_one_or_none.return_value = None

        db.execute = AsyncMock(side_effect=[rls, rls, count_r, items_r, no_asset, no_assign])

        service = OrderService(db, redis, user)
        result = await service.list_orders_by_asset(5, 1, 20)
        assert result.total == 1

    @pytest.mark.asyncio
    async def test_update_order_success(self):
        db = AsyncMock()
        redis = AsyncMock()
        user = _make_user("supervisor")

        order = _make_order(status="open")
        rls = MagicMock()
        order_result = MagicMock()
        order_result.scalar_one_or_none.return_value = order

        # update() calls: execute UPDATE + get_by_id
        # get_detail calls: get_by_id + asset + assignment
        no_ref = MagicMock()
        no_ref.scalar_one_or_none.return_value = None

        db.execute = AsyncMock(side_effect=[
            rls, rls,       # RLS
            order_result,   # check exists
            MagicMock(),    # UPDATE execute
            order_result,   # get_by_id in update()
            order_result,   # get_by_id in get_detail
            no_ref,         # asset lookup
            no_ref,         # assignment lookup
        ])

        service = OrderService(db, redis, user)
        result = await service.update_order(1, UpdateOrderRequest(client_name="New"))
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_order_without_asset(self):
        db = AsyncMock()
        redis = AsyncMock()
        user = _make_user("attendant")

        order = _make_order()
        rls = MagicMock()
        no_ref = MagicMock()
        no_ref.scalar_one_or_none.return_value = None
        order_result = MagicMock()
        order_result.scalar_one_or_none.return_value = order

        async def refresh_order(obj):
            obj.id = 1
            obj.order_number = 1001
            obj.status = "open"
            obj.priority = "medium"
            obj.total_cost = Decimal("0.00")
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)

        db.execute = AsyncMock(side_effect=[
            rls, rls,       # RLS
            order_result,   # get_by_id in get_detail
            no_ref,         # asset lookup
            no_ref,         # assignment lookup
        ])
        db.refresh = AsyncMock(side_effect=refresh_order)

        service = OrderService(db, redis, user)
        result = await service.create_order(
            CreateOrderRequest(client_name="Test", location="Local")
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_history_nonexistent_order_raises_404(self):
        db = AsyncMock()
        redis = AsyncMock()
        user = _make_user("admin")

        rls = MagicMock()
        not_found = MagicMock()
        not_found.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(side_effect=[rls, rls, not_found])

        service = OrderService(db, redis, user)
        with pytest.raises(BusinessError) as exc:
            await service.get_history(999)
        assert exc.value.code == "ORDER_NOT_FOUND"
