import logging

import jwt
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from shared.shared.auth.dependencies import UserClaims, get_current_user, require_roles
from shared.shared.auth.jwt import verify_token
from shared.shared.config import SharedSettings, get_shared_settings
from shared.shared.db.session import get_db
from shared.shared.schemas.pagination import PaginatedResponse

from ..schemas.notification import (
    NotificationFilters,
    NotificationReadResponse,
    NotificationResponse,
)
from ..services.notification_service import NotificationService
from ..services.websocket_manager import manager as ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get(
    "",
    response_model=PaginatedResponse[NotificationResponse],
    summary="Lista notificações do usuário autenticado",
)
async def list_notifications(
    filters: NotificationFilters = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor", "technician", "attendant"])),
) -> PaginatedResponse[NotificationResponse]:
    return await NotificationService(db, current_user).list_notifications(filters)


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationReadResponse,
    summary="Marca notificação como lida",
)
async def mark_as_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor", "technician", "attendant"])),
) -> NotificationReadResponse:
    return await NotificationService(db, current_user).mark_as_read(notification_id)


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str | None = None,
    settings: SharedSettings = Depends(get_shared_settings),
):
    """WebSocket para notificações em tempo real. Auth via ?token=<JWT>"""
    if not token:
        await websocket.close(code=4001)
        return

    try:
        payload = verify_token(token, settings.jwt_public_key)
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        await websocket.close(code=4001)
        return

    connected = await ws_manager.connect(user_id, websocket)
    if not connected:
        return

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(user_id, websocket)
    except Exception:
        await ws_manager.disconnect(user_id, websocket)
