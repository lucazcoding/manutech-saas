from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from shared.shared.db.rls import set_rls_context
from shared.shared.exceptions.handlers import BusinessError
from shared.shared.schemas.pagination import PaginatedResponse

from ..repositories.token_repository import TokenRepository
from ..repositories.user_repository import UserRepository
from ..schemas.user import (
    CreateUserRequest,
    StatusUpdateResponse,
    UpdateStatusRequest,
    UpdateUserRequest,
    UserFilters,
    UserResponse,
)
from .auth_service import hash_password


class UserService:
    def __init__(self, db: AsyncSession, current_user_id: int, current_user_role: str) -> None:
        self._db = db
        self._user_repo = UserRepository(db)
        self._token_repo = TokenRepository(db)
        self._current_user_id = current_user_id
        self._current_user_role = current_user_role

    async def _set_rls(self) -> None:
        await set_rls_context(self._db, self._current_user_id, self._current_user_role)

    async def get_me(self, user_id: int) -> UserResponse:
        await self._set_rls()
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise BusinessError("USER_NOT_FOUND", 404, "Usuário não encontrado")
        return UserResponse.model_validate(user)

    async def list_users(self, filters: UserFilters) -> PaginatedResponse[UserResponse]:
        await self._set_rls()
        users, total = await self._user_repo.list(filters)
        items = [UserResponse.model_validate(u) for u in users]
        return PaginatedResponse.build(
            items=items,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
        )

    async def create_user(self, data: CreateUserRequest) -> UserResponse:
        await self._set_rls()
        password_hash = hash_password(data.password)
        user = await self._user_repo.create(data, password_hash)
        return UserResponse.model_validate(user)

    async def get_user(self, user_id: int) -> UserResponse:
        await self._set_rls()
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise BusinessError("USER_NOT_FOUND", 404, "Usuário não encontrado")
        return UserResponse.model_validate(user)

    async def update_user(self, user_id: int, data: UpdateUserRequest) -> UserResponse:
        await self._set_rls()
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise BusinessError("USER_NOT_FOUND", 404, "Usuário não encontrado")
        updated = await self._user_repo.update(user_id, data)
        return UserResponse.model_validate(updated)

    async def update_status(self, user_id: int, data: UpdateStatusRequest) -> StatusUpdateResponse:
        await self._set_rls()
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise BusinessError("USER_NOT_FOUND", 404, "Usuário não encontrado")

        updated = await self._user_repo.update_status(user_id, data.status)

        if data.status == "inactive":
            await self._token_repo.revoke_all_for_user(user_id)

        return StatusUpdateResponse.model_validate(updated)
