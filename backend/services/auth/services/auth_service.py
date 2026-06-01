from datetime import datetime, timedelta, timezone

import bcrypt as _bcrypt_lib
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from shared.shared.auth.jwt import (
    create_access_token,
    create_refresh_token_value,
    hash_token,
)
from shared.shared.db.rls import set_rls_context
from shared.shared.exceptions.handlers import BusinessError

from ..config import AuthSettings
from ..repositories.token_repository import TokenRepository
from ..repositories.user_repository import UserRepository
from ..schemas.auth import (
    LogoutRequest,
    RefreshRequest,
    RefreshTokenResponse,
    TokenResponse,
    UserInLoginResponse,
    LoginRequest,
)
from .rate_limit import check_rate_limit, increment_attempts, reset_attempts

_BCRYPT_ROUNDS = 12


def _verify_password(password: str, password_hash: str) -> bool:
    return _bcrypt_lib.checkpw(password.encode(), password_hash.encode())


def hash_password(password: str) -> str:
    return _bcrypt_lib.hashpw(password.encode(), _bcrypt_lib.gensalt(rounds=_BCRYPT_ROUNDS)).decode()


class AuthService:
    def __init__(self, db: AsyncSession, redis: Redis) -> None:
        self._db = db
        self._redis = redis
        self._user_repo = UserRepository(db)
        self._token_repo = TokenRepository(db)

    async def login(
        self,
        body: LoginRequest,
        client_ip: str,
        settings: AuthSettings,
    ) -> TokenResponse:
        await check_rate_limit(
            client_ip,
            self._redis,
            settings.login_max_attempts,
            settings.login_window_seconds,
        )

        user = await self._user_repo.get_by_login(body.login)
        if user is None:
            await increment_attempts(client_ip, self._redis, settings.login_window_seconds)
            raise BusinessError("INVALID_CREDENTIALS", 401, "Login ou senha incorretos")

        if user.status == "inactive":
            raise BusinessError("USER_INACTIVE", 403, "Usuário inativo")

        if not _verify_password(body.password, user.password_hash):
            await increment_attempts(client_ip, self._redis, settings.login_window_seconds)
            raise BusinessError("INVALID_CREDENTIALS", 401, "Login ou senha incorretos")

        await reset_attempts(client_ip, self._redis)

        raw_refresh = create_refresh_token_value()
        refresh_hash = hash_token(raw_refresh)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
        await self._token_repo.create(user.id, refresh_hash, expires_at)

        access_token = create_access_token(
            payload={"sub": str(user.id), "role": user.role, "name": user.name},
            private_key=settings.jwt_private_key,
            expire_hours=settings.jwt_access_token_expire_hours,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            expires_in=settings.jwt_access_token_expire_hours * 3600,
            user=UserInLoginResponse.model_validate(user),
        )

    async def refresh(
        self,
        body: RefreshRequest,
        settings: AuthSettings,
    ) -> RefreshTokenResponse:
        token_hash = hash_token(body.refresh_token)
        stored = await self._token_repo.get_by_hash(token_hash)

        if stored is None or stored.revoked:
            raise BusinessError("REFRESH_TOKEN_INVALID", 401, "Refresh token inválido ou revogado")

        if stored.expires_at < datetime.now(timezone.utc):
            raise BusinessError("REFRESH_TOKEN_EXPIRED", 401, "Refresh token expirado")

        user = await self._user_repo.get_by_id(stored.user_id)
        if user is None or user.status == "inactive":
            raise BusinessError("REFRESH_TOKEN_INVALID", 401, "Refresh token inválido ou revogado")

        access_token = create_access_token(
            payload={"sub": str(user.id), "role": user.role, "name": user.name},
            private_key=settings.jwt_private_key,
            expire_hours=settings.jwt_access_token_expire_hours,
        )

        return RefreshTokenResponse(
            access_token=access_token,
            expires_in=settings.jwt_access_token_expire_hours * 3600,
        )

    async def logout(self, body: LogoutRequest, current_user_id: int, current_user_role: str) -> None:
        await set_rls_context(self._db, current_user_id, current_user_role)
        token_hash = hash_token(body.refresh_token)
        await self._token_repo.revoke_by_hash(token_hash)


