from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..config import SharedSettings, get_shared_settings
from .jwt import verify_token

security = HTTPBearer()


@dataclass
class UserClaims:
    id: int
    role: str
    name: str


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: SharedSettings = Depends(get_shared_settings),
) -> UserClaims:
    try:
        payload = verify_token(credentials.credentials, settings.jwt_public_key)
        return UserClaims(
            id=int(payload["sub"]),
            role=payload["role"],
            name=payload["name"],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_roles(roles: list[str]):
    async def check(current_user: UserClaims = Depends(get_current_user)) -> None:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissão insuficiente para este recurso",
            )
    return check
