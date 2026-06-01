from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from shared.shared.auth.dependencies import UserClaims
from shared.shared.db.rls import set_rls_context
from shared.shared.exceptions.handlers import BusinessError
from shared.shared.schemas.pagination import PaginatedResponse

from ..repositories.asset_repository import AssetRepository
from ..schemas.asset import (
    AssetFilters,
    AssetResponse,
    AssetStatusUpdateResponse,
    CreateAssetRequest,
    UpdateAssetRequest,
    UpdateAssetStatusRequest,
)


class AssetService:
    def __init__(self, db: AsyncSession, current_user: UserClaims) -> None:
        self._db = db
        self._current_user = current_user
        self._repo = AssetRepository(db)

    async def _set_rls(self) -> None:
        await set_rls_context(self._db, self._current_user.id, self._current_user.role)

    async def list_assets(self, filters: AssetFilters) -> PaginatedResponse[AssetResponse]:
        await self._set_rls()
        assets, total = await self._repo.list(filters)
        pages = ceil(total / filters.page_size) if total > 0 else 0
        return PaginatedResponse(
            items=[AssetResponse.model_validate(a) for a in assets],
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            pages=pages,
        )

    async def create_asset(self, data: CreateAssetRequest) -> AssetResponse:
        await self._set_rls()
        asset = await self._repo.create(data)
        return AssetResponse.model_validate(asset)

    async def get_asset(self, asset_id: int) -> AssetResponse:
        await self._set_rls()
        asset = await self._repo.get_by_id(asset_id)
        if asset is None:
            raise BusinessError("ASSET_NOT_FOUND", 404, "Equipamento não encontrado")
        return AssetResponse.model_validate(asset)

    async def update_asset(self, asset_id: int, data: UpdateAssetRequest) -> AssetResponse:
        await self._set_rls()
        asset = await self._repo.get_by_id(asset_id)
        if asset is None:
            raise BusinessError("ASSET_NOT_FOUND", 404, "Equipamento não encontrado")
        updated = await self._repo.update(asset_id, data)
        return AssetResponse.model_validate(updated)

    async def update_asset_status(
        self, asset_id: int, data: UpdateAssetStatusRequest
    ) -> AssetStatusUpdateResponse:
        await self._set_rls()
        asset = await self._repo.get_by_id(asset_id)
        if asset is None:
            raise BusinessError("ASSET_NOT_FOUND", 404, "Equipamento não encontrado")
        updated = await self._repo.update_status(asset_id, data.status)
        return AssetStatusUpdateResponse.model_validate(updated)
