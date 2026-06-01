from math import ceil

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from shared.shared.exceptions.handlers import BusinessError

from ..models.asset import Asset
from ..schemas.asset import AssetFilters, CreateAssetRequest, UpdateAssetRequest


class AssetRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list(self, filters: AssetFilters) -> tuple[list[Asset], int]:
        base = select(Asset)

        if filters.name:
            base = base.where(Asset.name.ilike(f"%{filters.name}%"))
        if filters.status:
            base = base.where(Asset.status == filters.status)
        if filters.location:
            base = base.where(Asset.location.ilike(f"%{filters.location}%"))

        count_result = await self._db.execute(
            select(func.count()).select_from(base.subquery())
        )
        total = count_result.scalar_one()

        offset = (filters.page - 1) * filters.page_size
        rows = await self._db.execute(
            base.order_by(Asset.created_at.desc()).offset(offset).limit(filters.page_size)
        )
        return list(rows.scalars().all()), total

    async def get_by_id(self, asset_id: int) -> Asset | None:
        result = await self._db.execute(select(Asset).where(Asset.id == asset_id))
        return result.scalar_one_or_none()

    async def create(self, data: CreateAssetRequest) -> Asset:
        asset = Asset(
            name=data.name,
            model=data.model,
            manufacturer=data.manufacturer,
            serial_number=data.serial_number,
            location=data.location,
        )
        self._db.add(asset)
        try:
            await self._db.flush()
            await self._db.refresh(asset)
        except IntegrityError as exc:
            orig = str(exc.orig)
            if "serial_number" in orig:
                raise BusinessError(
                    "SERIAL_NUMBER_ALREADY_EXISTS",
                    409,
                    "Serial number já está em uso",
                    "serial_number",
                )
            raise
        return asset

    async def update(self, asset_id: int, data: UpdateAssetRequest) -> Asset | None:
        changes = {k: v for k, v in data.model_dump().items() if v is not None}
        if not changes:
            return await self.get_by_id(asset_id)

        try:
            await self._db.execute(
                update(Asset)
                .where(Asset.id == asset_id)
                .values(**changes, updated_at=func.now())
            )
            await self._db.flush()
        except IntegrityError as exc:
            orig = str(exc.orig)
            if "serial_number" in orig:
                raise BusinessError(
                    "SERIAL_NUMBER_ALREADY_EXISTS",
                    409,
                    "Serial number já está em uso",
                    "serial_number",
                )
            raise

        return await self.get_by_id(asset_id)

    async def update_status(self, asset_id: int, status: str) -> Asset | None:
        await self._db.execute(
            update(Asset)
            .where(Asset.id == asset_id)
            .values(status=status, updated_at=func.now())
        )
        await self._db.flush()
        return await self.get_by_id(asset_id)
