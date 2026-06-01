from decimal import Decimal
from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from shared.shared.auth.dependencies import UserClaims
from shared.shared.db.rls import set_rls_context
from shared.shared.exceptions.handlers import BusinessError
from shared.shared.schemas.pagination import PaginatedResponse

from ..repositories.finance_repository import BudgetRepository, CostRepository
from ..schemas.finance import (
    BudgetFilters,
    BudgetResponse,
    CostFilters,
    CostResponse,
    CreateBudgetRequest,
    CreateCostRequest,
    FinancialReport,
    UpdateBudgetRequest,
    UpdateCostRequest,
)

# Budget state machine transitions
_BUDGET_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"sent", "expired"},
    "sent": {"approved", "rejected"},
    "approved": set(),
    "rejected": set(),
    "expired": set(),
}


class FinanceService:
    def __init__(self, db: AsyncSession, current_user: UserClaims) -> None:
        self._db = db
        self._current_user = current_user
        self._cost_repo = CostRepository(db)
        self._budget_repo = BudgetRepository(db)

    async def _set_rls(self) -> None:
        await set_rls_context(self._db, self._current_user.id, self._current_user.role)

    # ── Costs ──────────────────────────────────────────────────────────────

    async def list_costs(self, filters: CostFilters) -> PaginatedResponse[CostResponse]:
        await self._set_rls()
        costs, total = await self._cost_repo.list(filters)
        pages = ceil(total / filters.page_size) if total > 0 else 0
        return PaginatedResponse(
            items=[CostResponse.model_validate(c) for c in costs],
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            pages=pages,
        )

    async def create_cost(self, data: CreateCostRequest) -> CostResponse:
        await self._set_rls()
        cost = await self._cost_repo.create(data)
        return CostResponse.model_validate(cost)

    async def update_cost(self, cost_id: int, data: UpdateCostRequest) -> CostResponse:
        await self._set_rls()
        cost = await self._cost_repo.get_by_id(cost_id)
        if cost is None:
            raise BusinessError("ORDER_NOT_FOUND", 404, "Custo não encontrado")
        updated = await self._cost_repo.update(cost_id, data)
        return CostResponse.model_validate(updated)

    async def delete_cost(self, cost_id: int) -> None:
        await self._set_rls()
        cost = await self._cost_repo.get_by_id(cost_id)
        if cost is None:
            raise BusinessError("ORDER_NOT_FOUND", 404, "Custo não encontrado")
        await self._cost_repo.delete(cost_id)

    async def get_order_budget(self, order_id: int) -> BudgetResponse | None:
        await self._set_rls()
        result = await self._budget_repo.get_for_order(order_id)
        if result is None:
            raise BusinessError("ORDER_NOT_FOUND", 404, "Orçamento não encontrado para esta OS")
        return result

    # ── Budgets ────────────────────────────────────────────────────────────

    async def list_budgets(self, filters: BudgetFilters) -> PaginatedResponse[BudgetResponse]:
        await self._set_rls()
        items, total = await self._budget_repo.list(filters)
        pages = ceil(total / filters.page_size) if total > 0 else 0
        return PaginatedResponse(
            items=items,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            pages=pages,
        )

    async def create_budget(self, data: CreateBudgetRequest) -> BudgetResponse:
        await self._set_rls()
        budget = await self._budget_repo.create(data, self._current_user.id)
        detail = await self._budget_repo.get_detail(budget.id)
        return detail

    async def get_budget(self, budget_id: int) -> BudgetResponse:
        await self._set_rls()
        detail = await self._budget_repo.get_detail(budget_id)
        if detail is None:
            raise BusinessError("ORDER_NOT_FOUND", 404, "Orçamento não encontrado")
        return detail

    async def update_budget(self, budget_id: int, data: UpdateBudgetRequest) -> BudgetResponse:
        await self._set_rls()
        budget = await self._budget_repo.get_by_id(budget_id)
        if budget is None:
            raise BusinessError("ORDER_NOT_FOUND", 404, "Orçamento não encontrado")
        if budget.status != "draft":
            raise BusinessError(
                "BUDGET_NOT_EDITABLE", 400, "Orçamento só pode ser editado em status draft"
            )
        await self._budget_repo.update(budget_id, data)
        return await self._budget_repo.get_detail(budget_id)

    async def delete_budget(self, budget_id: int) -> None:
        await self._set_rls()
        budget = await self._budget_repo.get_by_id(budget_id)
        if budget is None:
            raise BusinessError("ORDER_NOT_FOUND", 404, "Orçamento não encontrado")
        await self._budget_repo.delete(budget_id)

    # ── Reports ────────────────────────────────────────────────────────────

    async def get_financial_report(self) -> FinancialReport:
        await self._set_rls()
        total, by_type, orders_count = await self._cost_repo.get_costs_summary()
        avg = total / Decimal(orders_count) if orders_count > 0 else Decimal("0")
        return FinancialReport(
            total_costs=total,
            costs_by_type=by_type,
            orders_count=orders_count,
            avg_cost_per_order=avg.quantize(Decimal("0.01")),
        )
