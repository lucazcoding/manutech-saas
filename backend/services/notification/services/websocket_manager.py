import asyncio
import logging
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)

_MAX_CONNECTIONS_PER_USER = 5


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[int, list[WebSocket]] = defaultdict(list)

    async def connect(self, user_id: int, websocket: WebSocket) -> bool:
        if len(self._connections[user_id]) >= _MAX_CONNECTIONS_PER_USER:
            await websocket.close(code=4001)
            return False
        await websocket.accept()
        self._connections[user_id].append(websocket)
        return True

    async def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        connections = self._connections[user_id]
        if websocket in connections:
            connections.remove(websocket)

    async def send_to_user(self, user_id: int, data: dict) -> None:
        dead: list[WebSocket] = []
        for ws in list(self._connections.get(user_id, [])):
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(user_id, ws)


manager = ConnectionManager()
