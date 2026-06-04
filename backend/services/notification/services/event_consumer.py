"""
Redis subscriber — consome eventos publicados pelos demais serviços:
  - order.assigned
  - order.status_changed
  - stock.low_alert
"""

import asyncio
import json
import logging

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..repositories.notification_repository import NotificationRepository
from .websocket_manager import manager as ws_manager

logger = logging.getLogger(__name__)

_CHANNELS = ["order.assigned", "order.status_changed", "stock.low_alert"]

_TITLE_MAP = {
    "order.assigned": "Nova OS atribuída",
    "order.status_changed": "Status de OS atualizado",
    "stock.low_alert": "Alerta de estoque baixo",
}


def _build_message(channel: str, payload: dict) -> str:
    if channel == "order.assigned":
        return f"Você foi atribuído à OS #{payload.get('order_id', '?')}"
    if channel == "order.status_changed":
        return (
            f"OS #{payload.get('order_id', '?')} mudou de "
            f"'{payload.get('old_status')}' para '{payload.get('new_status')}'"
        )
    if channel == "stock.low_alert":
        return (
            f"Material '{payload.get('material_name', '?')}' com estoque baixo: "
            f"{payload.get('quantity_in_stock')} unidades"
        )
    return "Nova notificação"


async def _handle_event(
    channel: str,
    data: dict,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    user_id = data.get("user_id")
    payload = data.get("payload", {})

    if not user_id:
        return

    title = _TITLE_MAP.get(channel, "Notificação")
    message = _build_message(channel, payload)

    async with session_factory() as session:
        async with session.begin():
            repo = NotificationRepository(session)
            notif = await repo.create(
                user_id=user_id,
                type_=channel,
                title=title,
                message=message,
                related_id=payload.get("order_id"),
            )

    await ws_manager.send_to_user(
        user_id,
        {
            "id": notif.id,
            "type": channel,
            "title": title,
            "message": message,
            "related_id": payload.get("order_id"),
        },
    )


async def start_subscriber(
    redis_url: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    while True:
        try:
            client = aioredis.from_url(redis_url, decode_responses=True, health_check_interval=30)
            pubsub = client.pubsub()
            await pubsub.subscribe(*_CHANNELS)
            logger.info("Redis subscriber connected — channels: %s", _CHANNELS)

            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    data = json.loads(message["data"])
                    await _handle_event(message["channel"], data, session_factory)
                except Exception:
                    logger.exception("Error handling Redis event: %s", message)
        except Exception:
            logger.exception("Redis subscriber error — reconnecting in 5s")
            await asyncio.sleep(5)
