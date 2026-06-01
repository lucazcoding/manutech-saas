from fastapi import APIRouter, Depends, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from shared.shared.auth.dependencies import UserClaims, get_current_user, require_roles
from shared.shared.db.session import get_db
from shared.shared.redis.client import get_redis
from shared.shared.schemas.pagination import PaginatedResponse

from ..schemas.user import (
    CreateUserRequest,
    StatusUpdateResponse,
    UpdateStatusRequest,
    UpdateUserRequest,
    UserFilters,
    UserResponse,
)
from ..services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "",
    response_model=PaginatedResponse[UserResponse],
    summary="Lista usuários com filtros opcionais",
)
async def list_users(
    filters: UserFilters = Depends(),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin"])),
) -> PaginatedResponse[UserResponse]:
    service = UserService(db, current_user.id, current_user.role)
    return await service.list_users(filters)


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra novo usuário",
)
async def create_user(
    body: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin"])),
) -> UserResponse:
    service = UserService(db, current_user.id, current_user.role)
    return await service.create_user(body)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Retorna dados de um usuário por ID",
)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin"])),
) -> UserResponse:
    service = UserService(db, current_user.id, current_user.role)
    return await service.get_user(user_id)


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Atualiza dados cadastrais do usuário",
)
async def update_user(
    user_id: int,
    body: UpdateUserRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin"])),
) -> UserResponse:
    service = UserService(db, current_user.id, current_user.role)
    return await service.update_user(user_id, body)


@router.patch(
    "/{user_id}/status",
    response_model=StatusUpdateResponse,
    summary="Ativa ou inativa um usuário",
)
async def update_status(
    user_id: int,
    body: UpdateStatusRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin"])),
) -> StatusUpdateResponse:
    service = UserService(db, current_user.id, current_user.role)
    return await service.update_status(user_id, body)
