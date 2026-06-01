from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from shared.shared.auth.dependencies import UserClaims
from shared.shared.db.rls import set_rls_context
from shared.shared.exceptions.handlers import BusinessError
from shared.shared.schemas.pagination import PaginatedResponse

from ..repositories.notification_repository import NotificationRepository
from ..schemas.notification import (
    NotificationFilters,
    NotificationReadResponse,
    NotificationResponse,
)


class NotificationService:
    def __init__(self, db: AsyncSession, current_user: UserClaims) -> None:
        self._db = db
        self._current_user = current_user
        self._repo = NotificationRepository(db)

    async def _set_rls(self) -> None:
        await set_rls_context(self._db, self._current_user.id, self._current_user.role)

    async def list_notifications(
        self, filters: NotificationFilters
    ) -> PaginatedResponse[NotificationResponse]:
        await self._set_rls()
        notifications, total = await self._repo.list_for_user(self._current_user.id, filters)
        pages = ceil(total / filters.page_size) if total > 0 else 0
        return PaginatedResponse(
            items=[NotificationResponse.model_validate(n) for n in notifications],
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            pages=pages,
        )

    async def mark_as_read(self, notification_id: int) -> NotificationReadResponse:
        await self._set_rls()
        notification = await self._repo.get_by_id(notification_id)
        if notification is None or notification.user_id != self._current_user.id:
            raise BusinessError("ORDER_NOT_FOUND", 404, "Notificação não encontrada")
        updated = await self._repo.mark_as_read(notification_id)
        return NotificationReadResponse.model_validate(updated)
