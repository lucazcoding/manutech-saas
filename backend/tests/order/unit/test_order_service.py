"""
Testes unitários — Order Service
ORDER-01: RBAC por endpoint
ORDER-02: State machine de status
ORDER-03: Validações de negócio (asset_id, technician, cancellation)
ORDER-04: Eventos Redis (order.assigned, order.status_changed)
ORDER-05: Stats com cache Redis
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from shared.shared.auth.dependencies import UserClaims
from shared.shared.exceptions.handlers import BusinessError

from services.order.schemas.order import (
    AssignOrderRequest,
    CreateOrderRequest,
    OrderFilters,
    UpdateOrderStatusRequest,
)
from services.order.services.state_machine import validate_status_transition


def _make_order(
    order_id: int = 1,
    status: str = "open",
    asset_id: int | None = None,
    order_number: int = 1001,
):
    order = MagicMock()
    order.id = order_id
    order.order_number = order_number
    order.client_name = "Empresa X"
    order.location = "Rua A, 100"
    order.description = None
    order.status = status
    order.priority = "medium"
    order.total_cost = 0
    order.start_date = None
    order.asset_id = asset_id
    order.created_at = datetime.now(timezone.utc)
    order.updated_at = datetime.now(timezone.utc)
    return order


# ─── ORDER-01: RBAC ──────────────────────────────────────────────────────────

class TestRBAC:
    def test_admin_cannot_create_order(self, rsa_keys, mock_db, fake_redis):
        from tests.order.conftest import make_client
        admin = UserClaims(id=1, role="admin", name="Admin")
        client = make_client(rsa_keys, current_user=admin, mock_db=mock_db, mock_redis=fake_redis)
        resp = client.post("/api/v1/orders", json={"client_name": "X", "location": "Y"})
        assert resp.status_code == 403

    def test_technician_cannot_create_order(self, rsa_keys, mock_db, fake_redis):
        from tests.order.conftest import make_client
        tech = UserClaims(id=3, role="technician", name="Tech")
        client = make_client(rsa_keys, current_user=tech, mock_db=mock_db, mock_redis=fake_redis)
        resp = client.post("/api/v1/orders", json={"client_name": "X", "location": "Y"})
        assert resp.status_code == 403

    def test_attendant_cannot_list_orders(self, rsa_keys, mock_db, fake_redis):
        from tests.order.conftest import make_client
        att = UserClaims(id=4, role="attendant", name="Att")
        client = make_client(rsa_keys, current_user=att, mock_db=mock_db, mock_redis=fake_redis)
        resp = client.get("/api/v1/orders")
        assert resp.status_code == 403

    def test_technician_cannot_update_order(self, rsa_keys, mock_db, fake_redis):
        from tests.order.conftest import make_client
        tech = UserClaims(id=3, role="technician", name="Tech")
        client = make_client(rsa_keys, current_user=tech, mock_db=mock_db, mock_redis=fake_redis)
        resp = client.put("/api/v1/orders/1", json={"client_name": "Y"})
        assert resp.status_code == 403

    def test_technician_cannot_assign(self, rsa_keys, mock_db, fake_redis):
        from tests.order.conftest import make_client
        tech = UserClaims(id=3, role="technician", name="Tech")
        client = make_client(rsa_keys, current_user=tech, mock_db=mock_db, mock_redis=fake_redis)
        resp = client.patch("/api/v1/orders/1/assign", json={"technician_id": 3})
        assert resp.status_code == 403

    def test_attendant_cannot_view_stats(self, rsa_keys, mock_db, fake_redis):
        from tests.order.conftest import make_client
        att = UserClaims(id=4, role="attendant", name="Att")
        client = make_client(rsa_keys, current_user=att, mock_db=mock_db, mock_redis=fake_redis)
        resp = client.get("/api/v1/orders/stats")
        assert resp.status_code == 403

    def test_attendant_cannot_delete_order(self, rsa_keys, mock_db, fake_redis):
        from tests.order.conftest import make_client
        att = UserClaims(id=4, role="attendant", name="Att")
        client = make_client(rsa_keys, current_user=att, mock_db=mock_db, mock_redis=fake_redis)
        resp = client.delete("/api/v1/orders/1")
        assert resp.status_code == 403


# ─── ORDER-02: State Machine ─────────────────────────────────────────────────

class TestStateMachine:
    def test_open_to_in_progress_valid(self):
        validate_status_transition("open", "in_progress")

    def test_open_to_cancelled_valid(self):
        validate_status_transition("open", "cancelled")

    def test_in_progress_to_completed_valid(self):
        validate_status_transition("in_progress", "completed")

    def test_in_progress_to_cancelled_valid(self):
        validate_status_transition("in_progress", "cancelled")

    def test_completed_to_open_invalid(self):
        with pytest.raises(BusinessError) as exc:
            validate_status_transition("completed", "open")
        assert exc.value.code == "INVALID_STATUS_TRANSITION"

    def test_completed_to_in_progress_invalid(self):
        with pytest.raises(BusinessError) as exc:
            validate_status_transition("completed", "in_progress")
        assert exc.value.code == "INVALID_STATUS_TRANSITION"

    def test_cancelled_to_open_invalid(self):
        with pytest.raises(BusinessError) as exc:
            validate_status_transition("cancelled", "open")
        assert exc.value.code == "INVALID_STATUS_TRANSITION"

    def test_open_to_completed_invalid(self):
        with pytest.raises(BusinessError) as exc:
            validate_status_transition("open", "completed")
        assert exc.value.code == "INVALID_STATUS_TRANSITION"


# ─── ORDER-03: Regras de Negócio ─────────────────────────────────────────────

class TestBusinessRules:
    @pytest.mark.asyncio
    async def test_cancel_without_reason_raises_400(self):
        from services.order.services.order_service import OrderService

        db = AsyncMock()
        redis = AsyncMock()
        user = UserClaims(id=2, role="supervisor", name="Sup")

        order = _make_order(status="open")
        rls_mock = MagicMock()
        get_result = MagicMock()
        get_result.scalar_one_or_none.return_value = order

        db.execute = AsyncMock(side_effect=[rls_mock, rls_mock, get_result])

        service = OrderService(db, redis, user)

        with pytest.raises(BusinessError) as exc:
            await service.update_status(1, UpdateOrderStatusRequest(status="cancelled"))

        assert exc.value.code == "CANCELLATION_REASON_REQUIRED"
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_in_progress_without_technician_raises_400(self):
        from services.order.services.order_service import OrderService

        db = AsyncMock()
        redis = AsyncMock()
        user = UserClaims(id=2, role="supervisor", name="Sup")

        order = _make_order(status="open")
        rls_mock = MagicMock()
        get_order_result = MagicMock()
        get_order_result.scalar_one_or_none.return_value = order
        no_assignment_result = MagicMock()
        no_assignment_result.scalar_one_or_none.return_value = None

        db.execute = AsyncMock(side_effect=[rls_mock, rls_mock, get_order_result, no_assignment_result])

        service = OrderService(db, redis, user)

        with pytest.raises(BusinessError) as exc:
            await service.update_status(1, UpdateOrderStatusRequest(status="in_progress"))

        assert exc.value.code == "TECHNICIAN_REQUIRED"
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_order_not_found_raises_404(self):
        from services.order.services.order_service import OrderService

        db = AsyncMock()
        redis = AsyncMock()
        user = UserClaims(id=2, role="supervisor", name="Sup")

        rls_mock = MagicMock()
        not_found = MagicMock()
        not_found.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(side_effect=[rls_mock, rls_mock, not_found])

        service = OrderService(db, redis, user)

        with pytest.raises(BusinessError) as exc:
            await service.get_order(999)

        assert exc.value.code == "ORDER_NOT_FOUND"
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_assign_non_technician_raises_422(self):
        from services.order.services.order_service import OrderService

        db = AsyncMock()
        redis = AsyncMock()
        user = UserClaims(id=2, role="supervisor", name="Sup")

        order = _make_order(status="open")
        rls_mock = MagicMock()
        order_result = MagicMock()
        order_result.scalar_one_or_none.return_value = order

        not_tech = MagicMock()
        not_tech.id = 2
        not_tech.role = "supervisor"
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = not_tech

        db.execute = AsyncMock(side_effect=[rls_mock, rls_mock, order_result, user_result])

        service = OrderService(db, redis, user)

        with pytest.raises(BusinessError) as exc:
            await service.assign_technician(1, AssignOrderRequest(technician_id=2))

        assert exc.value.code == "NOT_A_TECHNICIAN"
        assert exc.value.status_code == 422

    @pytest.mark.asyncio
    async def test_create_with_inactive_asset_raises_400(self):
        from services.order.services.order_service import OrderService

        db = AsyncMock()
        redis = AsyncMock()
        user = UserClaims(id=2, role="supervisor", name="Sup")

        inactive_asset = MagicMock()
        inactive_asset.id = 5
        inactive_asset.status = "inactive"

        rls_mock = MagicMock()
        asset_result = MagicMock()
        asset_result.scalar_one_or_none.return_value = inactive_asset

        db.execute = AsyncMock(side_effect=[rls_mock, rls_mock, asset_result])

        service = OrderService(db, redis, user)

        with pytest.raises(BusinessError) as exc:
            await service.create_order(
                CreateOrderRequest(client_name="X", location="Y", asset_id=5)
            )

        assert exc.value.code == "ASSET_INACTIVE"

    @pytest.mark.asyncio
    async def test_update_closed_order_raises_400(self):
        from services.order.services.order_service import OrderService
        from services.order.schemas.order import UpdateOrderRequest

        db = AsyncMock()
        redis = AsyncMock()
        user = UserClaims(id=2, role="supervisor", name="Sup")

        order = _make_order(status="completed")
        rls_mock = MagicMock()
        order_result = MagicMock()
        order_result.scalar_one_or_none.return_value = order

        db.execute = AsyncMock(side_effect=[rls_mock, rls_mock, order_result])

        service = OrderService(db, redis, user)

        with pytest.raises(BusinessError) as exc:
            await service.update_order(1, UpdateOrderRequest(client_name="Y"))

        assert exc.value.code == "ORDER_CLOSED"


# ─── ORDER-04: Eventos Redis ─────────────────────────────────────────────────

class TestRedisEvents:
    @pytest.mark.asyncio
    async def test_status_change_publishes_event(self, fake_redis):
        from services.order.services.order_service import OrderService

        db = AsyncMock()
        user = UserClaims(id=2, role="supervisor", name="Sup")

        order = _make_order(status="open")
        rls_mock = MagicMock()
        order_result = MagicMock()
        order_result.scalar_one_or_none.return_value = order

        assignment = MagicMock()
        assignment.technician_id = 5
        assignment_result = MagicMock()
        assignment_result.scalar_one_or_none.return_value = assignment

        # For update_status and get_detail
        updated_order = _make_order(status="in_progress")
        updated_result = MagicMock()
        updated_result.scalar_one_or_none.return_value = updated_order

        # get_detail also calls for asset and assignment
        no_asset = MagicMock()
        no_asset.scalar_one_or_none.return_value = None

        db.execute = AsyncMock(side_effect=[
            rls_mock, rls_mock,   # RLS
            order_result,          # get_by_id
            assignment_result,     # get_active_assignment
            MagicMock(),           # update_status execute
            updated_result,        # get_by_id in get_detail
            no_asset,              # asset lookup (None)
            assignment_result,     # assignment lookup
            MagicMock(),           # technician lookup
        ])

        service = OrderService(db, fake_redis, user)

        # Publishes event to Redis — no exception expected
        with patch("services.order.services.order_service.publish_event", new_callable=AsyncMock) as mock_pub:
            await service.update_status(1, UpdateOrderStatusRequest(status="in_progress"))
            mock_pub.assert_called_once()
            call_args = mock_pub.call_args
            assert call_args[0][1] == "order.status_changed"

    @pytest.mark.asyncio
    async def test_assign_publishes_event(self, fake_redis):
        from services.order.services.order_service import OrderService

        db = AsyncMock()
        user = UserClaims(id=2, role="supervisor", name="Sup")

        order = _make_order(status="open")
        rls_mock = MagicMock()
        order_result = MagicMock()
        order_result.scalar_one_or_none.return_value = order

        tech = MagicMock()
        tech.id = 5
        tech.role = "technician"
        tech_result = MagicMock()
        tech_result.scalar_one_or_none.return_value = tech

        no_prev = MagicMock()
        no_prev.scalar_one_or_none.return_value = None

        # assign_technician flow:
        # 1+2: RLS, 3: get_by_id order, 4: get_user_by_id,
        # 5: get_active_assignment, 6: flush (via assign_technician)
        # get_detail calls: 7: get_by_id, 8: asset lookup, 9: assignment lookup
        generic = MagicMock()
        generic.scalar_one_or_none.return_value = None

        db.execute = AsyncMock(side_effect=[
            rls_mock, rls_mock,    # RLS
            order_result,           # get_by_id(order_id)
            tech_result,            # get_user_by_id
            no_prev,                # get_active_assignment
            generic,                # update/flush
            order_result,           # get_by_id in get_detail
            generic,                # asset lookup
            no_prev,                # assignment lookup in _build_order_response
        ])

        with patch("services.order.services.order_service.publish_event", new_callable=AsyncMock) as mock_pub:
            service = OrderService(db, fake_redis, user)
            try:
                await service.assign_technician(1, AssignOrderRequest(technician_id=5))
            except Exception:
                pass
            mock_pub.assert_called_once()
            call_args = mock_pub.call_args
            assert call_args[0][1] == "order.assigned"


# ─── ORDER-05: Stats com cache Redis ─────────────────────────────────────────

class TestStatsCache:
    @pytest.mark.asyncio
    async def test_stats_cached_in_redis(self, fake_redis):
        from services.order.services.order_service import OrderService
        from services.order.config import OrderSettings

        db = AsyncMock()
        user = UserClaims(id=1, role="admin", name="Admin")

        rls_mock = MagicMock()
        status_result = MagicMock()
        status_result.all.return_value = [("open", 5), ("in_progress", 3)]
        priority_result = MagicMock()
        priority_result.all.return_value = [("medium", 8)]

        db.execute = AsyncMock(side_effect=[
            rls_mock, rls_mock,  # RLS
            status_result,        # status count
            priority_result,      # priority count
        ])

        settings = OrderSettings(
            jwt_public_key="",
            database_url="",
            stats_cache_ttl_seconds=30,
        )
        service = OrderService(db, fake_redis, user)
        stats = await service.get_stats(settings)

        assert stats.total == 8
        assert stats.by_status["open"] == 5

        # Segunda chamada deve usar cache — db.execute não chamado novamente
        db.execute = AsyncMock(side_effect=[rls_mock, rls_mock])
        service2 = OrderService(db, fake_redis, user)
        stats2 = await service2.get_stats(settings)
        assert stats2.total == 8
        db.execute.assert_called()  # RLS ainda é chamado

    def test_missing_required_fields_returns_422(self, rsa_keys, mock_db, fake_redis):
        from tests.order.conftest import make_client
        sup = UserClaims(id=2, role="supervisor", name="Sup")
        client = make_client(rsa_keys, current_user=sup, mock_db=mock_db, mock_redis=fake_redis)
        resp = client.post("/api/v1/orders", json={})
        assert resp.status_code == 422
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_invalid_status_transition_returns_400(self, rsa_keys, mock_db, fake_redis):
        from tests.order.conftest import make_client
        sup = UserClaims(id=2, role="supervisor", name="Sup")

        order = _make_order(status="completed")
        rls_mock = MagicMock()
        order_result = MagicMock()
        order_result.scalar_one_or_none.return_value = order
        mock_db.execute = AsyncMock(side_effect=[rls_mock, rls_mock, order_result])

        client = make_client(rsa_keys, current_user=sup, mock_db=mock_db, mock_redis=fake_redis)
        resp = client.patch(
            "/api/v1/orders/1/status",
            json={"status": "open"},
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == "INVALID_STATUS_TRANSITION"

    def test_upload_oversized_file_returns_413(self, rsa_keys, mock_db, fake_redis):
        from tests.order.conftest import make_client
        sup = UserClaims(id=2, role="supervisor", name="Sup")

        order = _make_order()
        rls_mock = MagicMock()
        order_result = MagicMock()
        order_result.scalar_one_or_none.return_value = order
        mock_db.execute = AsyncMock(side_effect=[rls_mock, rls_mock, order_result])

        client = make_client(rsa_keys, current_user=sup, mock_db=mock_db, mock_redis=fake_redis)
        oversized = b"x" * (21 * 1024 * 1024)  # 21 MB
        resp = client.post(
            "/api/v1/orders/1/attachments",
            files={"file": ("test.pdf", oversized, "application/pdf")},
        )
        assert resp.status_code == 413
        assert resp.json()["code"] == "FILE_TOO_LARGE"

    def test_upload_invalid_mime_type_returns_422(self, rsa_keys, mock_db, fake_redis):
        from tests.order.conftest import make_client
        sup = UserClaims(id=2, role="supervisor", name="Sup")

        order = _make_order()
        rls_mock = MagicMock()
        order_result = MagicMock()
        order_result.scalar_one_or_none.return_value = order
        mock_db.execute = AsyncMock(side_effect=[rls_mock, rls_mock, order_result])

        client = make_client(rsa_keys, current_user=sup, mock_db=mock_db, mock_redis=fake_redis)
        resp = client.post(
            "/api/v1/orders/1/attachments",
            files={"file": ("test.exe", b"malware", "application/x-msdownload")},
        )
        assert resp.status_code == 422
        assert resp.json()["code"] == "UNSUPPORTED_MIME_TYPE"
