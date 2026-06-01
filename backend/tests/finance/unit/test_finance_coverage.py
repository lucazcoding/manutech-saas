"""
Testes adicionais para aumentar cobertura do Finance Service.
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from shared.shared.auth.dependencies import UserClaims
from services.finance.schemas.finance import CostFilters, BudgetFilters, CreateBudgetRequest
from services.finance.services.finance_service import FinanceService


def _make_cost(cost_id=1):
    c = MagicMock()
    c.id = cost_id
    c.service_order_id = 1
    c.description = "Labor"
    c.amount = Decimal("100.00")
    c.cost_type = "labor"
    c.created_at = datetime.now(timezone.utc)
    return c


def _make_budget(budget_id=1, status="draft"):
    b = MagicMock()
    b.id = budget_id
    b.budget_number = 1001
    b.service_order_id = None
    b.client_name = "Cliente Y"
    b.description = None
    b.total_amount = Decimal("0.00")
    b.status = status
    b.valid_until = None
    b.created_by = 1
    b.created_at = datetime.now(timezone.utc)
    b.updated_at = datetime.now(timezone.utc)
    return b


def _make_user(role="admin"):
    return UserClaims(id=1, role=role, name="Test")


class TestFinanceCoverage:

    @pytest.mark.asyncio
    async def test_list_costs_empty(self):
        db = AsyncMock()
        user = _make_user()

        rls = MagicMock()
        count_r = MagicMock()
        count_r.scalar_one.return_value = 0
        items_r = MagicMock()
        items_r.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(side_effect=[rls, rls, count_r, items_r])

        service = FinanceService(db, user)
        result = await service.list_costs(CostFilters(page=1, page_size=20))
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_list_budgets_empty(self):
        db = AsyncMock()
        user = _make_user()

        rls = MagicMock()
        count_r = MagicMock()
        count_r.scalar_one.return_value = 0
        items_r = MagicMock()
        items_r.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(side_effect=[rls, rls, count_r, items_r])

        service = FinanceService(db, user)
        result = await service.list_budgets(BudgetFilters(page=1, page_size=20))
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_delete_budget_success(self):
        db = AsyncMock()
        user = _make_user()

        budget = _make_budget()
        rls = MagicMock()
        bgt_result = MagicMock()
        bgt_result.scalar_one_or_none.return_value = budget
        del_result = MagicMock()
        db.execute = AsyncMock(side_effect=[rls, rls, bgt_result, del_result])

        service = FinanceService(db, user)
        await service.delete_budget(1)

    @pytest.mark.asyncio
    async def test_update_cost_success(self):
        db = AsyncMock()
        user = _make_user("supervisor")

        cost = _make_cost()
        rls = MagicMock()
        cost_result = MagicMock()
        cost_result.scalar_one_or_none.return_value = cost
        db.execute = AsyncMock(side_effect=[
            rls, rls, cost_result, MagicMock(), cost_result
        ])

        from services.finance.schemas.finance import UpdateCostRequest
        service = FinanceService(db, user)
        result = await service.update_cost(1, UpdateCostRequest(amount=200.0))
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_budget_with_items(self):
        db = AsyncMock()
        user = _make_user("supervisor")

        budget = _make_budget()
        rls = MagicMock()
        bgt_result = MagicMock()
        bgt_result.scalar_one_or_none.return_value = budget
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = []

        async def refresh_budget(obj):
            obj.id = 1
            obj.budget_number = 1001
            obj.total_amount = Decimal("0.00")
            obj.status = "draft"
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)

        db.execute = AsyncMock(side_effect=[
            rls, rls,      # RLS
            bgt_result,    # get_by_id in get_detail
            items_result,  # _get_items
        ])
        db.refresh = AsyncMock(side_effect=refresh_budget)

        service = FinanceService(db, user)
        result = await service.create_budget(
            CreateBudgetRequest(client_name="Cliente X")
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_budget_success(self):
        db = AsyncMock()
        user = _make_user()

        budget = _make_budget()
        rls = MagicMock()
        bgt_result = MagicMock()
        bgt_result.scalar_one_or_none.return_value = budget
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = []

        db.execute = AsyncMock(side_effect=[rls, rls, bgt_result, items_result])

        service = FinanceService(db, user)
        result = await service.get_budget(1)
        assert result is not None

    @pytest.mark.asyncio
    async def test_list_costs_with_data(self):
        db = AsyncMock()
        user = _make_user()

        cost = _make_cost()
        rls = MagicMock()
        count_r = MagicMock()
        count_r.scalar_one.return_value = 1
        items_r = MagicMock()
        items_r.scalars.return_value.all.return_value = [cost]
        db.execute = AsyncMock(side_effect=[rls, rls, count_r, items_r])

        service = FinanceService(db, user)
        result = await service.list_costs(CostFilters(page=1, page_size=20))
        assert result.total == 1
        assert len(result.items) == 1
