from redis.asyncio import Redis

from shared.shared.exceptions.handlers import BusinessError

_KEY_TEMPLATE = "login_attempts:{ip}"


def _key(ip: str) -> str:
    return _KEY_TEMPLATE.format(ip=ip)


async def check_rate_limit(ip: str, redis: Redis, max_attempts: int, window_seconds: int) -> None:
    attempts = await redis.get(_key(ip))
    if attempts and int(attempts) >= max_attempts:
        raise BusinessError(
            "RATE_LIMIT_EXCEEDED",
            429,
            "Muitas tentativas de login. Tente novamente em 15 minutos.",
        )


async def increment_attempts(ip: str, redis: Redis, window_seconds: int) -> None:
    k = _key(ip)
    async with redis.pipeline(transaction=False) as pipe:
        pipe.incr(k)
        pipe.expire(k, window_seconds)
        await pipe.execute()


async def reset_attempts(ip: str, redis: Redis) -> None:
    await redis.delete(_key(ip))
