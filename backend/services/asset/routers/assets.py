from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.shared.auth.dependencies import UserClaims, get_current_user, require_roles
from shared.shared.db.session import get_db
from shared.shared.schemas.pagination import PaginatedResponse

from ..schemas.asset import (
    AssetFilters,
    AssetResponse,
    AssetStatusUpdateResponse,
    CreateAssetRequest,
    UpdateAssetRequest,
    UpdateAssetStatusRequest,
)
from ..services.asset_service import AssetService

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get(
    "",
    response_model=PaginatedResponse[AssetResponse],
    summary="Lista equipamentos",
)
async def list_assets(
    filters: AssetFilters = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor", "technician", "attendant"])),
) -> PaginatedResponse[AssetResponse]:
    return await AssetService(db, current_user).list_assets(filters)


@router.post(
    "",
    response_model=AssetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra novo equipamento",
)
async def create_asset(
    body: CreateAssetRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor"])),
) -> AssetResponse:
    return await AssetService(db, current_user).create_asset(body)


@router.get(
    "/{asset_id}",
    response_model=AssetResponse,
    summary="Retorna equipamento pelo ID",
)
async def get_asset(
    asset_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor", "technician", "attendant"])),
) -> AssetResponse:
    return await AssetService(db, current_user).get_asset(asset_id)


@router.put(
    "/{asset_id}",
    response_model=AssetResponse,
    summary="Atualiza equipamento",
)
async def update_asset(
    asset_id: int,
    body: UpdateAssetRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor"])),
) -> AssetResponse:
    return await AssetService(db, current_user).update_asset(asset_id, body)


@router.patch(
    "/{asset_id}/status",
    response_model=AssetStatusUpdateResponse,
    summary="Atualiza status do equipamento",
)
async def update_asset_status(
    asset_id: int,
    body: UpdateAssetStatusRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor"])),
) -> AssetStatusUpdateResponse:
    return await AssetService(db, current_user).update_asset_status(asset_id, body)
