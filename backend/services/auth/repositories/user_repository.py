from math import ceil
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from shared.shared.exceptions.handlers import BusinessError

from ..models.user import User
from ..schemas.user import CreateUserRequest, UpdateUserRequest, UserFilters


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_login(self, login: str) -> User | None:
        result = await self._db.execute(select(User).where(User.login == login))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self._db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def list(self, filters: UserFilters) -> tuple[list[User], int]:
        base_query = select(User)

        if filters.name:
            base_query = base_query.where(User.name.ilike(f"%{filters.name}%"))
        if filters.role:
            base_query = base_query.where(User.role == filters.role)
        if filters.status:
            base_query = base_query.where(User.status == filters.status)

        count_result = await self._db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total = count_result.scalar_one()

        offset = (filters.page - 1) * filters.page_size
        paginated = base_query.order_by(User.created_at.desc()).offset(offset).limit(filters.page_size)
        rows = await self._db.execute(paginated)
        return list(rows.scalars().all()), total

    async def create(self, data: CreateUserRequest, password_hash: str) -> User:
        user = User(
            name=data.name,
            login=data.login,
            email=data.email,
            password_hash=password_hash,
            role=data.role,
        )
        self._db.add(user)
        try:
            await self._db.flush()
            await self._db.refresh(user)
        except IntegrityError as exc:
            orig = str(exc.orig)
            if "users_login_key" in orig:
                raise BusinessError("LOGIN_ALREADY_EXISTS", 409, "Login já está em uso", "login")
            if "users_email_key" in orig:
                raise BusinessError("EMAIL_ALREADY_EXISTS", 409, "Email já está em uso", "email")
            raise
        return user

    async def update(self, user_id: int, data: UpdateUserRequest) -> User | None:
        changes = {k: v for k, v in data.model_dump().items() if v is not None}
        if not changes:
            return await self.get_by_id(user_id)

        try:
            await self._db.execute(
                update(User)
                .where(User.id == user_id)
                .values(**changes, updated_at=func.now())
                .returning(User)
            )
            await self._db.flush()
        except IntegrityError as exc:
            orig = str(exc.orig)
            if "users_email_key" in orig:
                raise BusinessError("EMAIL_ALREADY_EXISTS", 409, "Email já está em uso", "email")
            raise

        return await self.get_by_id(user_id)

    async def update_status(self, user_id: int, status: str) -> User | None:
        await self._db.execute(
            update(User)
            .where(User.id == user_id)
            .values(status=status, updated_at=func.now())
        )
        await self._db.flush()
        return await self.get_by_id(user_id)
