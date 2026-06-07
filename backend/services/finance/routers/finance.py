from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from shared.shared.auth.dependencies import UserClaims, get_current_user, require_roles
from shared.shared.db.session import get_db
from shared.shared.schemas.pagination import PaginatedResponse

from ..schemas.finance import (
    BudgetFilters,
    BudgetResponse,
    CostFilters,
    CostResponse,
    CreateBudgetRequest,
    CreateCostRequest,
    FinancialReport,
    UpdateBudgetRequest,
    UpdateBudgetStatusRequest,
    UpdateCostRequest,
)
from ..services.finance_service import FinanceService

costs_router = APIRouter(prefix="/costs", tags=["costs"])
budgets_router = APIRouter(prefix="/budgets", tags=["budgets"])
reports_router = APIRouter(prefix="/reports", tags=["reports"])
orders_router = APIRouter(prefix="/orders", tags=["orders"])


@costs_router.get(
    "",
    response_model=PaginatedResponse[CostResponse],
    summary="Lista custos",
)
async def list_costs(
    filters: CostFilters = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor"])),
) -> PaginatedResponse[CostResponse]:
    return await FinanceService(db, current_user).list_costs(filters)


@costs_router.post(
    "",
    response_model=CostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registra custo em uma OS",
)
async def create_cost(
    body: CreateCostRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor", "technician"])),
) -> CostResponse:
    return await FinanceService(db, current_user).create_cost(body)


@costs_router.put(
    "/{cost_id}",
    response_model=CostResponse,
    summary="Atualiza custo",
)
async def update_cost(
    cost_id: int,
    body: UpdateCostRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor"])),
) -> CostResponse:
    return await FinanceService(db, current_user).update_cost(cost_id, body)


@costs_router.delete(
    "/{cost_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove custo",
)
async def delete_cost(
    cost_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor"])),
) -> None:
    await FinanceService(db, current_user).delete_cost(cost_id)


@orders_router.get(
    "/{order_id}/budget",
    response_model=BudgetResponse,
    summary="Retorna orçamento associado à OS",
)
async def get_order_budget(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor", "technician"])),
) -> BudgetResponse:
    return await FinanceService(db, current_user).get_order_budget(order_id)


@budgets_router.get(
    "",
    response_model=PaginatedResponse[BudgetResponse],
    summary="Lista orçamentos",
)
async def list_budgets(
    filters: BudgetFilters = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor"])),
) -> PaginatedResponse[BudgetResponse]:
    return await FinanceService(db, current_user).list_budgets(filters)


@budgets_router.post(
    "",
    response_model=BudgetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria novo orçamento",
)
async def create_budget(
    body: CreateBudgetRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor"])),
) -> BudgetResponse:
    return await FinanceService(db, current_user).create_budget(body)


@budgets_router.get(
    "/{budget_id}",
    response_model=BudgetResponse,
    summary="Retorna orçamento pelo ID",
)
async def get_budget(
    budget_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor"])),
) -> BudgetResponse:
    return await FinanceService(db, current_user).get_budget(budget_id)


@budgets_router.put(
    "/{budget_id}",
    response_model=BudgetResponse,
    summary="Atualiza orçamento (apenas em status draft)",
)
async def update_budget(
    budget_id: int,
    body: UpdateBudgetRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor"])),
) -> BudgetResponse:
    return await FinanceService(db, current_user).update_budget(budget_id, body)


@budgets_router.delete(
    "/{budget_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove orçamento",
)
async def delete_budget(
    budget_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor"])),
) -> None:
    await FinanceService(db, current_user).delete_budget(budget_id)


@budgets_router.patch(
    "/{budget_id}/status",
    response_model=BudgetResponse,
    summary="Avança o status do orçamento pela state machine",
)
async def update_budget_status(
    budget_id: int,
    body: UpdateBudgetStatusRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor"])),
) -> BudgetResponse:
    return await FinanceService(db, current_user).update_budget_status(budget_id, body.status)


@reports_router.get(
    "/financial",
    response_model=FinancialReport,
    summary="Relatório financeiro consolidado",
)
async def get_financial_report(
    db: AsyncSession = Depends(get_db),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor"])),
) -> FinancialReport:
    return await FinanceService(db, current_user).get_financial_report()


@reports_router.get(
    "/financial/export",
    summary="Exporta o relatório financeiro em Excel (CSV) ou PDF (TXT)",
    response_class=Response,
)
async def export_financial_report(
    format: str = Query(default="excel", pattern="^(excel|pdf)$"),
    db: AsyncSession = Depends(get_db),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor"])),
) -> Response:
    payload, content_type, filename = await FinanceService(
        db, current_user
    ).export_financial_report(format)
    return Response(
        content=payload,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
