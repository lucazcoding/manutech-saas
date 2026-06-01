from math import ceil

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.notification import Notification
from ..schemas.notification import NotificationFilters


class NotificationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_for_user(
        self, user_id: int, filters: NotificationFilters
    ) -> tuple[list[Notification], int]:
        base = select(Notification).where(Notification.user_id == user_id)

        if filters.read is not None:
            base = base.where(Notification.read == filters.read)

        count_result = await self._db.execute(
            select(func.count()).select_from(base.subquery())
        )
        total = count_result.scalar_one()

        offset = (filters.page - 1) * filters.page_size
        rows = await self._db.execute(
            base.order_by(Notification.created_at.desc()).offset(offset).limit(filters.page_size)
        )
        return list(rows.scalars().all()), total

    async def get_by_id(self, notification_id: int) -> Notification | None:
        result = await self._db.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        return result.scalar_one_or_none()

    async def mark_as_read(self, notification_id: int) -> Notification | None:
        await self._db.execute(
            update(Notification)
            .where(Notification.id == notification_id)
            .values(read=True)
        )
        await self._db.flush()
        return await self.get_by_id(notification_id)

    async def create(
        self,
        user_id: int,
        type_: str,
        title: str,
        message: str,
        related_id: int | None = None,
    ) -> Notification:
        notif = Notification(
            user_id=user_id,
            type=type_,
            title=title,
            message=message,
            related_id=related_id,
        )
        self._db.add(notif)
        await self._db.flush()
        await self._db.refresh(notif)
        return notif
