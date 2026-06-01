import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt


def create_access_token(payload: dict, private_key: str, expire_hours: int = 1) -> str:
    data = {
        **payload,
        "exp": datetime.now(timezone.utc) + timedelta(hours=expire_hours),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(data, private_key, algorithm="RS256")


def create_refresh_token_value() -> str:
    return secrets.token_urlsafe(64)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def verify_token(token: str, public_key: str) -> dict:
    return jwt.decode(token, public_key, algorithms=["RS256"])
