import json
import logging
from collections.abc import AsyncGenerator

import redis.asyncio as aioredis

from ..config import get_shared_settings

logger = logging.getLogger(__name__)

_redis_client: aioredis.Redis | None = None


def _get_redis_client() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        settings = get_shared_settings()
        _redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    yield _get_redis_client()


async def publish_event(redis: aioredis.Redis, channel: str, payload: dict) -> None:
    try:
        await redis.publish(channel, json.dumps(payload, default=str))
    except Exception:
        logger.exception("Falha ao publicar evento Redis no channel %s", channel)
