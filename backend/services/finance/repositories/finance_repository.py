from decimal import Decimal
from math import ceil

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.finance import Budget, BudgetItem, ServiceCost
from ..schemas.finance import (
    BudgetFilters,
    BudgetItemResponse,
    BudgetResponse,
    CostFilters,
    CreateBudgetItemRequest,
    CreateBudgetRequest,
    CreateCostRequest,
    UpdateBudgetRequest,
    UpdateCostRequest,
)


class CostRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list(self, filters: CostFilters) -> tuple[list[ServiceCost], int]:
        base = select(ServiceCost)

        if filters.service_order_id:
            base = base.where(ServiceCost.service_order_id == filters.service_order_id)
        if filters.cost_type:
            base = base.where(ServiceCost.cost_type == filters.cost_type)

        count_result = await self._db.execute(
            select(func.count()).select_from(base.subquery())
        )
        total = count_result.scalar_one()

        offset = (filters.page - 1) * filters.page_size
        rows = await self._db.execute(
            base.order_by(ServiceCost.created_at.desc()).offset(offset).limit(filters.page_size)
        )
        return list(rows.scalars().all()), total

    async def get_by_id(self, cost_id: int) -> ServiceCost | None:
        result = await self._db.execute(
            select(ServiceCost).where(ServiceCost.id == cost_id)
        )
        return result.scalar_one_or_none()

    async def create(self, data: CreateCostRequest) -> ServiceCost:
        cost = ServiceCost(
            service_order_id=data.service_order_id,
            description=data.description,
            amount=data.amount,
            cost_type=data.cost_type or "other",
        )
        self._db.add(cost)
        await self._db.flush()
        await self._db.refresh(cost)
        return cost

    async def update(self, cost_id: int, data: UpdateCostRequest) -> ServiceCost | None:
        changes = {k: v for k, v in data.model_dump().items() if v is not None}
        if changes:
            await self._db.execute(
                update(ServiceCost)
                .where(ServiceCost.id == cost_id)
                .values(**changes)
            )
            await self._db.flush()
        return await self.get_by_id(cost_id)

    async def delete(self, cost_id: int) -> None:
        await self._db.execute(delete(ServiceCost).where(ServiceCost.id == cost_id))
        await self._db.flush()

    async def get_costs_for_order(self, order_id: int) -> list[ServiceCost]:
        rows = await self._db.execute(
            select(ServiceCost)
            .where(ServiceCost.service_order_id == order_id)
            .order_by(ServiceCost.created_at.desc())
        )
        return list(rows.scalars().all())

    async def get_costs_summary(self) -> tuple[Decimal, dict[str, Decimal], int]:
        result = await self._db.execute(
            select(ServiceCost.cost_type, func.sum(ServiceCost.amount))
            .group_by(ServiceCost.cost_type)
        )
        by_type = {row[0]: Decimal(str(row[1])) for row in result.all()}
        total = sum(by_type.values(), Decimal("0"))

        orders_result = await self._db.execute(
            select(func.count(ServiceCost.service_order_id.distinct()))
        )
        orders_count = orders_result.scalar_one() or 0

        return total, by_type, orders_count


class BudgetRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def _get_items(self, budget_id: int) -> list[BudgetItemResponse]:
        rows = await self._db.execute(
            select(BudgetItem).where(BudgetItem.budget_id == budget_id)
        )
        return [BudgetItemResponse.model_validate(r) for r in rows.scalars().all()]

    async def _build_response(self, budget: Budget) -> BudgetResponse:
        items = await self._get_items(budget.id)
        return BudgetResponse(
            id=budget.id,
            budget_number=budget.budget_number,
            service_order_id=budget.service_order_id,
            client_name=budget.client_name,
            description=budget.description,
            total_amount=budget.total_amount,
            status=budget.status,
            valid_until=budget.valid_until,
            created_by=budget.created_by,
            items=items,
            created_at=budget.created_at,
            updated_at=budget.updated_at,
        )

    async def list(self, filters: BudgetFilters) -> tuple[list[BudgetResponse], int]:
        base = select(Budget)

        if filters.status:
            base = base.where(Budget.status == filters.status)
        if filters.service_order_id:
            base = base.where(Budget.service_order_id == filters.service_order_id)

        count_result = await self._db.execute(
            select(func.count()).select_from(base.subquery())
        )
        total = count_result.scalar_one()

        offset = (filters.page - 1) * filters.page_size
        rows = await self._db.execute(
            base.order_by(Budget.created_at.desc()).offset(offset).limit(filters.page_size)
        )
        budgets = list(rows.scalars().all())
        items = [await self._build_response(b) for b in budgets]
        return items, total

    async def get_by_id(self, budget_id: int) -> Budget | None:
        result = await self._db.execute(select(Budget).where(Budget.id == budget_id))
        return result.scalar_one_or_none()

    async def get_detail(self, budget_id: int) -> BudgetResponse | None:
        budget = await self.get_by_id(budget_id)
        if budget is None:
            return None
        return await self._build_response(budget)

    async def get_for_order(self, order_id: int) -> BudgetResponse | None:
        result = await self._db.execute(
            select(Budget)
            .where(Budget.service_order_id == order_id)
            .order_by(Budget.created_at.desc())
            .limit(1)
        )
        budget = result.scalar_one_or_none()
        if budget is None:
            return None
        return await self._build_response(budget)

    async def create(self, data: CreateBudgetRequest, created_by: int) -> Budget:
        budget = Budget(
            service_order_id=data.service_order_id,
            client_name=data.client_name,
            description=data.description,
            valid_until=data.valid_until,
            created_by=created_by,
        )
        self._db.add(budget)
        await self._db.flush()
        await self._db.refresh(budget)

        for item_data in data.items:
            item = BudgetItem(
                budget_id=budget.id,
                description=item_data.description,
                quantity=item_data.quantity,
                unit_price=item_data.unit_price,
            )
            self._db.add(item)

        if data.items:
            await self._db.flush()
            await self._db.refresh(budget)

        return budget

    async def update(self, budget_id: int, data: UpdateBudgetRequest) -> Budget | None:
        changes = {}
        if data.client_name is not None:
            changes["client_name"] = data.client_name
        if data.description is not None:
            changes["description"] = data.description
        if data.valid_until is not None:
            changes["valid_until"] = data.valid_until

        if changes:
            await self._db.execute(
                update(Budget)
                .where(Budget.id == budget_id)
                .values(**changes, updated_at=func.now())
            )
            await self._db.flush()

        if data.items is not None:
            await self._db.execute(delete(BudgetItem).where(BudgetItem.budget_id == budget_id))
            for item_data in data.items:
                item = BudgetItem(
                    budget_id=budget_id,
                    description=item_data.description,
                    quantity=item_data.quantity,
                    unit_price=item_data.unit_price,
                )
                self._db.add(item)
            await self._db.flush()

        return await self.get_by_id(budget_id)

    async def delete(self, budget_id: int) -> None:
        await self._db.execute(delete(Budget).where(Budget.id == budget_id))
        await self._db.flush()
