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
    # PEM keys stored in env vars use literal '\\n' — convert to real newlines
    key = private_key.replace("\\n", "\n")
    return jwt.encode(data, key, algorithm="RS256")


def create_refresh_token_value() -> str:
    return secrets.token_urlsafe(64)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def verify_token(token: str, public_key: str) -> dict:
    key = public_key.replace("\\n", "\n")
    return jwt.decode(token, key, algorithms=["RS256"])
