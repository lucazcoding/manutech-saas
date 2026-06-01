from math import ceil

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from shared.shared.auth.dependencies import UserClaims
from shared.shared.db.rls import set_rls_context
from shared.shared.exceptions.handlers import BusinessError
from shared.shared.redis.client import publish_event
from shared.shared.schemas.pagination import PaginatedResponse

from ..repositories.inventory_repository import MaterialRepository, MovementRepository
from ..schemas.inventory import (
    CreateMaterialRequest,
    CreateMovementRequest,
    MaterialFilters,
    MaterialResponse,
    MaterialStatusUpdateResponse,
    MovementFilters,
    MovementResponse,
    StockReportItem,
    UpdateMaterialRequest,
    UpdateMaterialStatusRequest,
)


class InventoryService:
    def __init__(self, db: AsyncSession, redis: Redis, current_user: UserClaims) -> None:
        self._db = db
        self._redis = redis
        self._current_user = current_user
        self._material_repo = MaterialRepository(db)
        self._movement_repo = MovementRepository(db)

    async def _set_rls(self) -> None:
        await set_rls_context(self._db, self._current_user.id, self._current_user.role)

    async def list_materials(self, filters: MaterialFilters) -> PaginatedResponse[MaterialResponse]:
        await self._set_rls()
        materials, total = await self._material_repo.list(filters)
        pages = ceil(total / filters.page_size) if total > 0 else 0
        return PaginatedResponse(
            items=[MaterialResponse.model_validate(m) for m in materials],
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            pages=pages,
        )

    async def get_material(self, material_id: int) -> MaterialResponse:
        await self._set_rls()
        material = await self._material_repo.get_by_id(material_id)
        if material is None:
            raise BusinessError("MATERIAL_NOT_FOUND", 404, "Material não encontrado")
        return MaterialResponse.model_validate(material)

    async def create_material(self, data: CreateMaterialRequest) -> MaterialResponse:
        await self._set_rls()
        material = await self._material_repo.create(data)
        return MaterialResponse.model_validate(material)

    async def update_material(self, material_id: int, data: UpdateMaterialRequest) -> MaterialResponse:
        await self._set_rls()
        material = await self._material_repo.get_by_id(material_id)
        if material is None:
            raise BusinessError("MATERIAL_NOT_FOUND", 404, "Material não encontrado")
        updated = await self._material_repo.update(material_id, data)
        return MaterialResponse.model_validate(updated)

    async def update_material_status(
        self, material_id: int, data: UpdateMaterialStatusRequest
    ) -> MaterialStatusUpdateResponse:
        await self._set_rls()
        material = await self._material_repo.get_by_id(material_id)
        if material is None:
            raise BusinessError("MATERIAL_NOT_FOUND", 404, "Material não encontrado")
        updated = await self._material_repo.update_status(material_id, data.status)
        return MaterialStatusUpdateResponse.model_validate(updated)

    async def create_movement(self, data: CreateMovementRequest) -> MovementResponse:
        await self._set_rls()
        material = await self._material_repo.get_by_id(data.material_id)
        if material is None:
            raise BusinessError("MATERIAL_NOT_FOUND", 404, "Material não encontrado")

        movement = await self._movement_repo.create(data)

        # After trigger executes, reload to get updated quantity
        updated_material = await self._material_repo.get_by_id(data.material_id)

        if (
            data.movement_type == "out"
            and updated_material
            and updated_material.quantity_in_stock <= updated_material.min_quantity
        ):
            await publish_event(
                self._redis,
                "stock.low_alert",
                {
                    "event": "stock.low_alert",
                    "payload": {
                        "material_id": material.id,
                        "material_name": material.name,
                        "quantity_in_stock": float(updated_material.quantity_in_stock),
                        "min_quantity": float(updated_material.min_quantity),
                    },
                },
            )

        return MovementResponse.model_validate(movement)

    async def list_movements(self, filters: MovementFilters) -> PaginatedResponse[MovementResponse]:
        await self._set_rls()
        movements, total = await self._movement_repo.list(filters)
        pages = ceil(total / filters.page_size) if total > 0 else 0
        return PaginatedResponse(
            items=[MovementResponse.model_validate(m) for m in movements],
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            pages=pages,
        )

    async def get_stock_report(self) -> list[StockReportItem]:
        await self._set_rls()
        materials = await self._material_repo.get_all_for_report()
        return [
            StockReportItem(
                id=m.id,
                name=m.name,
                sku=m.sku,
                quantity_in_stock=m.quantity_in_stock,
                min_quantity=m.min_quantity,
                unit_price=m.unit_price,
                status=m.status,
                is_low_stock=m.quantity_in_stock <= m.min_quantity,
            )
            for m in materials
        ]
