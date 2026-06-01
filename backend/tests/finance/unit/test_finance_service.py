"""
Testes unitários — Finance Service
FIN-01: RBAC por endpoint
FIN-02: Budget state machine (edição apenas em draft)
FIN-03: Cost CRUD
FIN-04: Budget CRUD
FIN-05: Relatório financeiro
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from shared.shared.auth.dependencies import UserClaims
from shared.shared.exceptions.handlers import BusinessError

from services.finance.schemas.finance import (
    CreateCostRequest,
    UpdateBudgetRequest,
)
from services.finance.services.finance_service import FinanceService


def _make_cost(cost_id: int = 1):
    c = MagicMock()
    c.id = cost_id
    c.service_order_id = 1
    c.description = "Mão de obra"
    c.amount = Decimal("150.00")
    c.cost_type = "labor"
    c.created_at = datetime.now(timezone.utc)
    return c


def _make_budget(budget_id: int = 1, status: str = "draft"):
    b = MagicMock()
    b.id = budget_id
    b.budget_number = 1001
    b.service_order_id = None
    b.client_name = "Empresa Y"
    b.description = None
    b.total_amount = Decimal("0.00")
    b.status = status
    b.valid_until = None
    b.created_by = 1
    b.created_at = datetime.now(timezone.utc)
    b.updated_at = datetime.now(timezone.utc)
    return b


def _make_user(role: str = "admin") -> UserClaims:
    return UserClaims(id=1, role=role, name="Test")


# ─── FIN-01: RBAC ────────────────────────────────────────────────────────────

class TestRBAC:
    def test_technician_cannot_list_costs(self, rsa_keys, mock_db):
        from tests.finance.conftest import make_client
        tech = UserClaims(id=3, role="technician", name="Tech")
        client = make_client(rsa_keys, current_user=tech, mock_db=mock_db)
        resp = client.get("/api/v1/costs")
        assert resp.status_code == 403

    def test_technician_can_create_cost(self, rsa_keys, mock_db):
        from tests.finance.conftest import make_client
        tech = UserClaims(id=3, role="technician", name="Tech")

        cost = _make_cost()
        rls = MagicMock()
        get_result = MagicMock()
        get_result.scalar_one_or_none.return_value = cost
        mock_db.execute = AsyncMock(side_effect=[rls, rls, get_result])

        async def refresh_obj(obj):
            obj.id = 1
            obj.created_at = datetime.now(timezone.utc)

        mock_db.refresh = AsyncMock(side_effect=refresh_obj)

        client = make_client(rsa_keys, current_user=tech, mock_db=mock_db)
        resp = client.post(
            "/api/v1/costs",
            json={"service_order_id": 1, "description": "Labor", "amount": 100.0},
        )
        assert resp.status_code == 201

    def test_technician_cannot_update_cost(self, rsa_keys, mock_db):
        from tests.finance.conftest import make_client
        tech = UserClaims(id=3, role="technician", name="Tech")
        client = make_client(rsa_keys, current_user=tech, mock_db=mock_db)
        resp = client.put("/api/v1/costs/1", json={"amount": 200.0})
        assert resp.status_code == 403

    def test_attendant_cannot_access_budgets(self, rsa_keys, mock_db):
        from tests.finance.conftest import make_client
        att = UserClaims(id=4, role="attendant", name="Att")
        client = make_client(rsa_keys, current_user=att, mock_db=mock_db)
        resp = client.get("/api/v1/budgets")
        assert resp.status_code == 403

    def test_technician_can_get_order_budget(self, rsa_keys, mock_db):
        from tests.finance.conftest import make_client
        tech = UserClaims(id=3, role="technician", name="Tech")

        budget = _make_budget()
        rls = MagicMock()
        bgt_result = MagicMock()
        bgt_result.scalar_one_or_none.return_value = budget
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(side_effect=[rls, rls, bgt_result, items_result])

        client = make_client(rsa_keys, current_user=tech, mock_db=mock_db)
        resp = client.get("/api/v1/orders/1/budget")
        assert resp.status_code == 200

    def test_attendant_cannot_get_reports(self, rsa_keys, mock_db):
        from tests.finance.conftest import make_client
        att = UserClaims(id=4, role="attendant", name="Att")
        client = make_client(rsa_keys, current_user=att, mock_db=mock_db)
        resp = client.get("/api/v1/reports/financial")
        assert resp.status_code == 403


# ─── FIN-02: Budget State Machine ────────────────────────────────────────────

class TestBudgetStateMachine:
    @pytest.mark.asyncio
    async def test_update_non_draft_budget_raises_400(self):
        db = AsyncMock()
        user = _make_user("admin")

        budget = _make_budget(status="sent")
        rls = MagicMock()
        bgt_result = MagicMock()
        bgt_result.scalar_one_or_none.return_value = budget
        db.execute = AsyncMock(side_effect=[rls, rls, bgt_result])

        service = FinanceService(db, user)

        with pytest.raises(BusinessError) as exc:
            await service.update_budget(1, UpdateBudgetRequest(client_name="Y"))

        assert exc.value.code == "BUDGET_NOT_EDITABLE"
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_update_draft_budget_succeeds(self):
        db = AsyncMock()
        user = _make_user("admin")

        budget = _make_budget(status="draft")
        rls = MagicMock()
        bgt_result = MagicMock()
        bgt_result.scalar_one_or_none.return_value = budget
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = []

        # 2 RLS + check get_by_id + update execute + get_by_id in update() + get_by_id in get_detail + items
        db.execute = AsyncMock(side_effect=[
            rls, rls,
            bgt_result,   # check exists
            MagicMock(),  # UPDATE execute
            bgt_result,   # get_by_id return in update()
            bgt_result,   # get_by_id in get_detail()
            items_result, # _get_items
        ])

        service = FinanceService(db, user)
        result = await service.update_budget(1, UpdateBudgetRequest(client_name="New Name"))
        assert result is not None


# ─── FIN-03: Cost CRUD ───────────────────────────────────────────────────────

class TestCostCRUD:
    @pytest.mark.asyncio
    async def test_create_cost_returns_response(self):
        db = AsyncMock()
        user = _make_user("supervisor")

        cost = _make_cost()
        rls = MagicMock()
        get_result = MagicMock()
        get_result.scalar_one_or_none.return_value = cost
        db.execute = AsyncMock(side_effect=[rls, rls, get_result])

        async def refresh_obj(obj):
            obj.id = 1
            obj.created_at = datetime.now(timezone.utc)

        db.refresh = AsyncMock(side_effect=refresh_obj)

        service = FinanceService(db, user)
        result = await service.create_cost(
            CreateCostRequest(service_order_id=1, description="Labor", amount=150.0)
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_cost_raises_404(self):
        db = AsyncMock()
        user = _make_user("admin")

        rls = MagicMock()
        not_found = MagicMock()
        not_found.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(side_effect=[rls, rls, not_found])

        service = FinanceService(db, user)

        with pytest.raises(BusinessError) as exc:
            await service.delete_cost(999)

        assert exc.value.status_code == 404

    def test_negative_amount_returns_422(self, rsa_keys, mock_db):
        from tests.finance.conftest import make_client
        admin = UserClaims(id=1, role="admin", name="Admin")
        client = make_client(rsa_keys, current_user=admin, mock_db=mock_db)
        resp = client.post(
            "/api/v1/costs",
            json={"service_order_id": 1, "description": "X", "amount": -50.0},
        )
        assert resp.status_code == 422


# ─── FIN-04: Budget CRUD ─────────────────────────────────────────────────────

class TestBudgetCRUD:
    @pytest.mark.asyncio
    async def test_get_nonexistent_budget_raises_404(self):
        db = AsyncMock()
        user = _make_user("admin")

        rls = MagicMock()
        not_found = MagicMock()
        not_found.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(side_effect=[rls, rls, not_found])

        service = FinanceService(db, user)

        with pytest.raises(BusinessError) as exc:
            await service.get_budget(999)

        assert exc.value.status_code == 404

    def test_empty_client_name_returns_422(self, rsa_keys, mock_db):
        from tests.finance.conftest import make_client
        admin = UserClaims(id=1, role="admin", name="Admin")
        client = make_client(rsa_keys, current_user=admin, mock_db=mock_db)
        resp = client.post(
            "/api/v1/budgets",
            json={"client_name": "  "},
        )
        assert resp.status_code == 422


# ─── FIN-05: Relatório financeiro ────────────────────────────────────────────

class TestFinancialReport:
    @pytest.mark.asyncio
    async def test_report_calculates_avg_correctly(self):
        db = AsyncMock()
        user = _make_user("admin")

        rls = MagicMock()
        summary_result = MagicMock()
        summary_result.all.return_value = [("labor", Decimal("300.00")), ("material", Decimal("100.00"))]
        orders_count_result = MagicMock()
        orders_count_result.scalar_one.return_value = 4

        db.execute = AsyncMock(side_effect=[rls, rls, summary_result, orders_count_result])

        service = FinanceService(db, user)
        report = await service.get_financial_report()

        assert report.total_costs == Decimal("400.00")
        assert report.orders_count == 4
        assert report.avg_cost_per_order == Decimal("100.00")

    @pytest.mark.asyncio
    async def test_report_zero_orders(self):
        db = AsyncMock()
        user = _make_user("admin")

        rls = MagicMock()
        summary_result = MagicMock()
        summary_result.all.return_value = []
        orders_count_result = MagicMock()
        orders_count_result.scalar_one.return_value = 0

        db.execute = AsyncMock(side_effect=[rls, rls, summary_result, orders_count_result])

        service = FinanceService(db, user)
        report = await service.get_financial_report()

        assert report.total_costs == Decimal("0")
        assert report.avg_cost_per_order == Decimal("0.00")
