from fastapi import APIRouter, Depends, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from shared.shared.auth.dependencies import UserClaims, get_current_user, require_roles
from shared.shared.db.session import get_db
from shared.shared.redis.client import get_redis
from shared.shared.schemas.pagination import PaginatedResponse

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
from ..services.inventory_service import InventoryService

materials_router = APIRouter(prefix="/materials", tags=["materials"])
movements_router = APIRouter(prefix="/movements", tags=["movements"])
stock_router = APIRouter(prefix="/stock", tags=["stock"])


@materials_router.get(
    "",
    response_model=PaginatedResponse[MaterialResponse],
    summary="Lista materiais",
)
async def list_materials(
    filters: MaterialFilters = Depends(),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor", "technician", "attendant"])),
) -> PaginatedResponse[MaterialResponse]:
    return await InventoryService(db, redis, current_user).list_materials(filters)


@materials_router.post(
    "",
    response_model=MaterialResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra novo material",
)
async def create_material(
    body: CreateMaterialRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor"])),
) -> MaterialResponse:
    return await InventoryService(db, redis, current_user).create_material(body)


@materials_router.get(
    "/{material_id}",
    response_model=MaterialResponse,
    summary="Retorna material pelo ID",
)
async def get_material(
    material_id: int,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor", "technician", "attendant"])),
) -> MaterialResponse:
    return await InventoryService(db, redis, current_user).get_material(material_id)


@materials_router.put(
    "/{material_id}",
    response_model=MaterialResponse,
    summary="Atualiza material",
)
async def update_material(
    material_id: int,
    body: UpdateMaterialRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor"])),
) -> MaterialResponse:
    return await InventoryService(db, redis, current_user).update_material(material_id, body)


@materials_router.patch(
    "/{material_id}/status",
    response_model=MaterialStatusUpdateResponse,
    summary="Atualiza status do material",
)
async def update_material_status(
    material_id: int,
    body: UpdateMaterialStatusRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin"])),
) -> MaterialStatusUpdateResponse:
    return await InventoryService(db, redis, current_user).update_material_status(
        material_id, body
    )


@movements_router.post(
    "",
    response_model=MovementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registra movimentação de estoque",
)
async def create_movement(
    body: CreateMovementRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor", "technician"])),
) -> MovementResponse:
    return await InventoryService(db, redis, current_user).create_movement(body)


@movements_router.get(
    "",
    response_model=PaginatedResponse[MovementResponse],
    summary="Lista movimentações de estoque",
)
async def list_movements(
    filters: MovementFilters = Depends(),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor"])),
) -> PaginatedResponse[MovementResponse]:
    return await InventoryService(db, redis, current_user).list_movements(filters)


@stock_router.get(
    "/report",
    response_model=list[StockReportItem],
    summary="Relatório de estoque atual",
)
async def get_stock_report(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor"])),
) -> list[StockReportItem]:
    return await InventoryService(db, redis, current_user).get_stock_report()
