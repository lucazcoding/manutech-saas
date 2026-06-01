from fastapi import APIRouter, Depends, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from shared.shared.auth.dependencies import UserClaims, get_current_user
from shared.shared.db.session import get_db
from shared.shared.redis.client import get_redis

from ..config import AuthSettings, get_auth_settings
from ..schemas.auth import (
    LogoutRequest,
    LoginRequest,
    RefreshRequest,
    RefreshTokenResponse,
    TokenResponse,
)
from ..schemas.user import UserResponse
from ..services.auth_service import AuthService
from ..services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Autentica usuário e retorna par de tokens JWT",
)
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    settings: AuthSettings = Depends(get_auth_settings),
) -> TokenResponse:
    client_ip = request.client.host if request.client else "unknown"
    service = AuthService(db, redis)
    return await service.login(body, client_ip, settings)


@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    summary="Renova o access token via refresh token",
)
async def refresh(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    settings: AuthSettings = Depends(get_auth_settings),
) -> RefreshTokenResponse:
    service = AuthService(db, redis)
    return await service.refresh(body, settings)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Invalida o refresh token (logout)",
)
async def logout(
    body: LogoutRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: UserClaims = Depends(get_current_user),
) -> None:
    service = AuthService(db, redis)
    await service.logout(body, current_user.id, current_user.role)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Retorna dados do usuário autenticado",
)
async def get_me(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: UserClaims = Depends(get_current_user),
) -> UserResponse:
    service = UserService(db, current_user.id, current_user.role)
    return await service.get_me(current_user.id)
