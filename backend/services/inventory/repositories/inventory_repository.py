from math import ceil

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from shared.shared.exceptions.handlers import BusinessError

from ..models.inventory import Material, StockMovement
from ..schemas.inventory import (
    CreateMaterialRequest,
    CreateMovementRequest,
    MaterialFilters,
    MovementFilters,
    UpdateMaterialRequest,
)


class MaterialRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list(self, filters: MaterialFilters) -> tuple[list[Material], int]:
        base = select(Material)

        if filters.name:
            base = base.where(Material.name.ilike(f"%{filters.name}%"))
        if filters.status:
            base = base.where(Material.status == filters.status)

        count_result = await self._db.execute(
            select(func.count()).select_from(base.subquery())
        )
        total = count_result.scalar_one()

        offset = (filters.page - 1) * filters.page_size
        rows = await self._db.execute(
            base.order_by(Material.name).offset(offset).limit(filters.page_size)
        )
        return list(rows.scalars().all()), total

    async def get_by_id(self, material_id: int) -> Material | None:
        result = await self._db.execute(
            select(Material).where(Material.id == material_id)
        )
        return result.scalar_one_or_none()

    async def create(self, data: CreateMaterialRequest) -> Material:
        material = Material(
            name=data.name,
            sku=data.sku,
            unit_price=data.unit_price,
            quantity_in_stock=data.quantity_in_stock or 0,
            min_quantity=data.min_quantity or 5,
        )
        self._db.add(material)
        try:
            await self._db.flush()
            await self._db.refresh(material)
        except IntegrityError as exc:
            orig = str(exc.orig)
            if "sku" in orig:
                raise BusinessError("SKU_ALREADY_EXISTS", 409, "SKU já está em uso", "sku")
            raise
        return material

    async def update(self, material_id: int, data: UpdateMaterialRequest) -> Material | None:
        changes = {k: v for k, v in data.model_dump().items() if v is not None}
        if not changes:
            return await self.get_by_id(material_id)

        try:
            await self._db.execute(
                update(Material)
                .where(Material.id == material_id)
                .values(**changes, updated_at=func.now())
            )
            await self._db.flush()
        except IntegrityError as exc:
            orig = str(exc.orig)
            if "sku" in orig:
                raise BusinessError("SKU_ALREADY_EXISTS", 409, "SKU já está em uso", "sku")
            raise

        return await self.get_by_id(material_id)

    async def update_status(self, material_id: int, status: str) -> Material | None:
        await self._db.execute(
            update(Material)
            .where(Material.id == material_id)
            .values(status=status, updated_at=func.now())
        )
        await self._db.flush()
        return await self.get_by_id(material_id)

    async def get_all_for_report(self) -> list[Material]:
        rows = await self._db.execute(
            select(Material).order_by(Material.name)
        )
        return list(rows.scalars().all())


class MovementRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list(self, filters: MovementFilters) -> tuple[list[StockMovement], int]:
        base = select(StockMovement)

        if filters.material_id:
            base = base.where(StockMovement.material_id == filters.material_id)
        if filters.movement_type:
            base = base.where(StockMovement.movement_type == filters.movement_type)
        if filters.service_order_id:
            base = base.where(StockMovement.service_order_id == filters.service_order_id)

        count_result = await self._db.execute(
            select(func.count()).select_from(base.subquery())
        )
        total = count_result.scalar_one()

        offset = (filters.page - 1) * filters.page_size
        rows = await self._db.execute(
            base.order_by(StockMovement.created_at.desc()).offset(offset).limit(filters.page_size)
        )
        return list(rows.scalars().all()), total

    async def create(self, data: CreateMovementRequest) -> StockMovement:
        movement = StockMovement(
            material_id=data.material_id,
            service_order_id=data.service_order_id,
            movement_type=data.movement_type,
            quantity=data.quantity,
            notes=data.notes,
        )
        self._db.add(movement)
        try:
            await self._db.flush()
            await self._db.refresh(movement)
        except Exception as exc:
            orig = str(exc)
            if "Estoque insuficiente" in orig or "insufficient" in orig.lower():
                raise BusinessError(
                    "INSUFFICIENT_STOCK", 400, "Estoque insuficiente para este material"
                )
            raise
        return movement
