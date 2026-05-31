# Redis — Regras

## Usos permitidos no MANUTECH

| Uso | Onde | TTL |
|-----|------|-----|
| Cache de dashboard stats | `GET /orders/stats` | 30 segundos |
| Rate limiting de login | Auth Service | 15 minutos (janela) |
| Pub/Sub de eventos | Order, Inventory → Notification | Sem TTL (pub/sub) |

Redis **não** é banco de dados. Nunca armazenar dados de negócio permanentes nele.

---

## Conexão

```python
# shared/redis/client.py
import redis.asyncio as redis
from functools import lru_cache
from ..config import settings

@lru_cache
def get_redis_pool() -> redis.ConnectionPool:
    return redis.ConnectionPool.from_url(
        settings.REDIS_URL,
        max_connections=20,
        decode_responses=True,
    )

async def get_redis() -> redis.Redis:
    pool = get_redis_pool()
    return redis.Redis(connection_pool=pool)
```

---

## Cache — Padrão de Uso

```python
# Cache simples com TTL
async def get_order_stats(redis: Redis, db: AsyncSession) -> dict:
    cache_key = "cache:orders:stats"

    # Tentar cache primeiro
    cached = await redis.get(cache_key)
    if cached:
        import json
        return json.loads(cached)

    # Calcular do banco
    stats = await OrderRepository(db).get_stats()

    # Salvar no cache com TTL
    await redis.setex(cache_key, 30, json.dumps(stats))
    return stats
```

### Invalidação de cache

Quando uma OS muda de status ou é criada, invalidar o cache de stats:

```python
await redis.delete("cache:orders:stats")
```

---

## Pub/Sub — Publicação de Eventos

```python
# shared/redis/events.py
import json
import redis.asyncio as redis

async def publish_event(redis_client: redis.Redis, channel: str, payload: dict) -> None:
    """Publica evento no Redis Pub/Sub."""
    message = json.dumps(payload)
    await redis_client.publish(channel, message)
```

### Canais disponíveis (não invente novos)

| Channel | Publicado por | Payload mínimo |
|---------|--------------|----------------|
| `order.assigned` | Order Service | `{event, user_id, payload: {order_number, client_name, message}}` |
| `order.status_changed` | Order Service | `{event, user_id, payload: {order_number, new_status, message}}` |
| `stock.low_alert` | Inventory Service | `{event, user_id, payload: {material_name, quantity_in_stock, message}}` |

```python
# Exemplo de publicação após atribuir técnico
await publish_event(redis, "order.assigned", {
    "event": "order.assigned",
    "user_id": technician_id,  # destinatário da notificação
    "payload": {
        "order_number": order.order_number,
        "client_name": order.client_name,
        "message": f"Você foi atribuído à OS-{order.order_number:04d} — {order.client_name}",
    }
})
```

---

## Pub/Sub — Consumo (Notification Service)

```python
# services/notification/consumers/event_consumer.py
import asyncio
import json
import logging
import redis.asyncio as redis

CHANNELS = ["order.assigned", "order.status_changed", "stock.low_alert"]

async def start_consumer(redis_client: redis.Redis, ws_manager, notification_repo):
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(*CHANNELS)

    logger = logging.getLogger(__name__)
    logger.info(f"Subscribed to channels: {CHANNELS}")

    async for message in pubsub.listen():
        if message["type"] != "message":
            continue
        try:
            data = json.loads(message["data"])
            await handle_event(data, ws_manager, notification_repo)
        except Exception:
            logger.exception(f"Error processing event: {message}")


async def handle_event(data: dict, ws_manager, notification_repo):
    event = data.get("event")
    user_id = data.get("user_id")
    payload = data.get("payload", {})

    # 1. Persistir notificação no banco
    notification = await notification_repo.create(
        user_id=user_id,
        type=event,
        title=_get_title(event),
        message=payload.get("message", ""),
        related_id=payload.get("order_id"),
    )

    # 2. Push via WebSocket para usuário conectado
    await ws_manager.send_to_user(user_id, {
        "event": event,
        "payload": {**payload, "notification_id": notification.id},
    })


def _get_title(event: str) -> str:
    titles = {
        "order.assigned": "Nova OS atribuída",
        "order.status_changed": "Status de OS atualizado",
        "stock.low_alert": "Alerta de estoque baixo",
    }
    return titles.get(event, "Notificação")
```

---

## WebSocket Manager

```python
# services/notification/ws/manager.py
from fastapi import WebSocket
from collections import defaultdict
import json

class WebSocketManager:
    def __init__(self):
        # user_id → lista de conexões ativas (mesmo user pode ter múltiplas abas)
        self._connections: dict[int, list[WebSocket]] = defaultdict(list)

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[user_id].append(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        self._connections[user_id].discard(websocket)
        if not self._connections[user_id]:
            del self._connections[user_id]

    async def send_to_user(self, user_id: int, data: dict) -> None:
        dead = []
        for ws in self._connections.get(user_id, []):
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(user_id, ws)
```
