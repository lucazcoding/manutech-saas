from fastapi import APIRouter, Depends, Query, UploadFile, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from shared.shared.auth.dependencies import UserClaims, get_current_user, require_roles
from shared.shared.db.session import get_db
from shared.shared.redis.client import get_redis
from shared.shared.schemas.pagination import PaginatedResponse
from ..config import OrderSettings, get_order_settings
from ..dependencies import get_storage
from ..schemas.order import (
    AssignOrderRequest,
    AttachmentResponse,
    AuditLogEntry,
    CreateOrderRequest,
    OrderFilters,
    OrderResponse,
    OrderStats,
    UpdateOrderRequest,
    UpdateOrderStatusRequest,
)
from ..services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])
assets_router = APIRouter(prefix="/assets", tags=["assets"])


@router.get(
    "/stats",
    response_model=OrderStats,
    summary="Estatísticas das ordens de serviço (cache 30s)",
)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor"])),
    settings: OrderSettings = Depends(get_order_settings),
) -> OrderStats:
    return await OrderService(db, redis, current_user).get_stats(settings)


@router.get(
    "",
    response_model=PaginatedResponse[OrderResponse],
    summary="Lista ordens de serviço",
)
async def list_orders(
    filters: OrderFilters = Depends(),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor", "technician"])),
) -> PaginatedResponse[OrderResponse]:
    return await OrderService(db, redis, current_user).list_orders(filters)


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria nova ordem de serviço",
)
async def create_order(
    body: CreateOrderRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor", "attendant"])),
) -> OrderResponse:
    return await OrderService(db, redis, current_user).create_order(body)


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Retorna ordem de serviço pelo ID",
)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor", "technician"])),
) -> OrderResponse:
    return await OrderService(db, redis, current_user).get_order(order_id)


@router.put(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Atualiza ordem de serviço",
)
async def update_order(
    order_id: int,
    body: UpdateOrderRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor"])),
) -> OrderResponse:
    return await OrderService(db, redis, current_user).update_order(order_id, body)


@router.delete(
    "/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove ordem de serviço",
)
async def delete_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor"])),
) -> None:
    await OrderService(db, redis, current_user).delete_order(order_id)


@router.patch(
    "/{order_id}/status",
    response_model=OrderResponse,
    summary="Atualiza status da ordem de serviço",
)
async def update_order_status(
    order_id: int,
    body: UpdateOrderStatusRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor", "technician"])),
) -> OrderResponse:
    return await OrderService(db, redis, current_user).update_status(order_id, body)


@router.patch(
    "/{order_id}/assign",
    response_model=OrderResponse,
    summary="Atribui técnico à ordem de serviço",
)
async def assign_technician(
    order_id: int,
    body: AssignOrderRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor"])),
) -> OrderResponse:
    return await OrderService(db, redis, current_user).assign_technician(order_id, body)


@router.post(
    "/{order_id}/request-completion",
    response_model=OrderResponse,
    summary="Técnico solicita a conclusão de uma OS em andamento (notifica supervisor/admin)",
)
async def request_order_completion(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor", "technician"])),
) -> OrderResponse:
    return await OrderService(db, redis, current_user).request_completion(order_id)


@router.get(
    "/{order_id}/history",
    response_model=list[AuditLogEntry],
    summary="Histórico de auditoria da OS",
)
async def get_order_history(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor"])),
) -> list[AuditLogEntry]:
    return await OrderService(db, redis, current_user).get_history(order_id)


@router.get(
    "/{order_id}/attachments",
    response_model=list[AttachmentResponse],
    summary="Lista anexos da OS",
)
async def list_attachments(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor", "technician"])),
) -> list[AttachmentResponse]:
    return await OrderService(db, redis, current_user).list_attachments(order_id)


@router.post(
    "/{order_id}/attachments",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Faz upload de anexo para a OS",
)
async def upload_attachment(
    order_id: int,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor", "technician"])),
    storage=Depends(get_storage),
) -> AttachmentResponse:
    content = await file.read()
    return await OrderService(db, redis, current_user).upload_attachment(
        order_id=order_id,
        filename=file.filename or "attachment",
        mime_type=file.content_type or "application/octet-stream",
        content=content,
        storage=storage,
    )


# GET /assets/:id/orders — pertence ao Order Service
@assets_router.get(
    "/{asset_id}/orders",
    response_model=PaginatedResponse[OrderResponse],
    summary="Lista ordens de serviço de um equipamento",
)
async def list_orders_by_asset(
    asset_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor", "technician"])),
) -> PaginatedResponse[OrderResponse]:
    return await OrderService(db, redis, current_user).list_orders_by_asset(
        asset_id, page, page_size
    )
