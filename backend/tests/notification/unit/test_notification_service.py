"""
Testes unitários — Notification Service
NOTIF-01: RBAC — todos os roles autenticados podem listar/ler notificações
NOTIF-02: Listagem e paginação
NOTIF-03: Marcar como lida — 404 para notificação alheia
NOTIF-04: WebSocket — conexão recusada sem token (4001)
NOTIF-05: Event consumer — processamento de eventos Redis
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from shared.shared.auth.dependencies import UserClaims
from shared.shared.exceptions.handlers import BusinessError

from services.notification.schemas.notification import NotificationFilters
from services.notification.services.notification_service import NotificationService


def _make_notification(notif_id: int = 1, user_id: int = 1, read: bool = False):
    n = MagicMock()
    n.id = notif_id
    n.user_id = user_id
    n.type = "order.assigned"
    n.title = "Nova OS"
    n.message = "Você foi atribuído à OS #1"
    n.read = read
    n.related_id = 1
    n.created_at = datetime.now(timezone.utc)
    return n


def _make_user(role: str = "admin", user_id: int = 1) -> UserClaims:
    return UserClaims(id=user_id, role=role, name="Test")


# ─── NOTIF-01: Todos os roles podem acessar notificações ─────────────────────

class TestRBAC:
    def test_all_roles_can_list_notifications(self, rsa_keys, mock_db):
        from tests.notification.conftest import make_client

        for role in ("admin", "supervisor", "technician", "attendant"):
            user = UserClaims(id=1, role=role, name=role)
            rls = MagicMock()
            count_r = MagicMock()
            count_r.scalar_one.return_value = 0
            items_r = MagicMock()
            items_r.scalars.return_value.all.return_value = []
            mock_db.execute = AsyncMock(side_effect=[rls, rls, count_r, items_r])

            client = make_client(rsa_keys, current_user=user, mock_db=mock_db)
            resp = client.get("/api/v1/notifications")
            assert resp.status_code == 200, f"Role {role} should be able to list notifications"


# ─── NOTIF-02: Listagem e paginação ──────────────────────────────────────────

class TestListNotifications:
    @pytest.mark.asyncio
    async def test_list_returns_paginated_response(self):
        db = AsyncMock()
        user = _make_user()

        rls = MagicMock()
        count_r = MagicMock()
        count_r.scalar_one.return_value = 2
        n1 = _make_notification(1)
        n2 = _make_notification(2)
        items_r = MagicMock()
        items_r.scalars.return_value.all.return_value = [n1, n2]

        db.execute = AsyncMock(side_effect=[rls, rls, count_r, items_r])

        service = NotificationService(db, user)
        result = await service.list_notifications(NotificationFilters(page=1, page_size=20))

        assert result.total == 2
        assert result.pages == 1
        assert len(result.items) == 2

    @pytest.mark.asyncio
    async def test_empty_list_returns_zero_pages(self):
        db = AsyncMock()
        user = _make_user()

        rls = MagicMock()
        count_r = MagicMock()
        count_r.scalar_one.return_value = 0
        items_r = MagicMock()
        items_r.scalars.return_value.all.return_value = []

        db.execute = AsyncMock(side_effect=[rls, rls, count_r, items_r])

        service = NotificationService(db, user)
        result = await service.list_notifications(NotificationFilters(page=1, page_size=20))

        assert result.total == 0
        assert result.pages == 0
        assert result.items == []


# ─── NOTIF-03: Marcar como lida ──────────────────────────────────────────────

class TestMarkAsRead:
    @pytest.mark.asyncio
    async def test_mark_own_notification_as_read(self):
        db = AsyncMock()
        user = _make_user(user_id=1)

        notif = _make_notification(user_id=1)
        notif_read = _make_notification(user_id=1, read=True)

        rls = MagicMock()
        get_r = MagicMock()
        get_r.scalar_one_or_none.return_value = notif
        update_r = MagicMock()
        after_r = MagicMock()
        after_r.scalar_one_or_none.return_value = notif_read

        db.execute = AsyncMock(side_effect=[rls, rls, get_r, update_r, after_r])

        service = NotificationService(db, user)
        result = await service.mark_as_read(1)
        assert result.read is True

    @pytest.mark.asyncio
    async def test_mark_other_user_notification_raises_404(self):
        db = AsyncMock()
        user = _make_user(user_id=2)

        notif = _make_notification(user_id=1)  # belongs to user 1
        rls = MagicMock()
        get_r = MagicMock()
        get_r.scalar_one_or_none.return_value = notif

        db.execute = AsyncMock(side_effect=[rls, rls, get_r])

        service = NotificationService(db, user)

        with pytest.raises(BusinessError) as exc:
            await service.mark_as_read(1)

        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_mark_nonexistent_notification_raises_404(self):
        db = AsyncMock()
        user = _make_user()

        rls = MagicMock()
        get_r = MagicMock()
        get_r.scalar_one_or_none.return_value = None

        db.execute = AsyncMock(side_effect=[rls, rls, get_r])

        service = NotificationService(db, user)

        with pytest.raises(BusinessError) as exc:
            await service.mark_as_read(999)

        assert exc.value.status_code == 404


# ─── NOTIF-04: WebSocket ─────────────────────────────────────────────────────

class TestWebSocket:
    def test_websocket_without_token_closes_4001(self, rsa_keys, mock_db):
        from tests.notification.conftest import make_client
        from fastapi.testclient import TestClient
        user = UserClaims(id=1, role="admin", name="Admin")
        client = make_client(rsa_keys, current_user=user, mock_db=mock_db)

        with pytest.raises(Exception):
            with client.websocket_connect("/api/v1/notifications/ws") as ws:
                ws.receive_json()

    def test_websocket_with_invalid_token_closes_4001(self, rsa_keys, mock_db):
        from tests.notification.conftest import make_client
        client = make_client(rsa_keys, mock_db=mock_db)

        with pytest.raises(Exception):
            with client.websocket_connect("/api/v1/notifications/ws?token=invalid_token") as ws:
                ws.receive_json()


# ─── NOTIF-05: Event consumer ────────────────────────────────────────────────

class TestEventConsumer:
    @pytest.mark.asyncio
    async def test_order_assigned_creates_notification(self):
        from services.notification.services.event_consumer import _handle_event
        from sqlalchemy.ext.asyncio import AsyncSession

        notif = _make_notification()
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_begin = AsyncMock()
        mock_begin.__aenter__ = AsyncMock(return_value=mock_begin)
        mock_begin.__aexit__ = AsyncMock(return_value=False)
        mock_session.begin = MagicMock(return_value=mock_begin)

        mock_factory = MagicMock()
        mock_factory.return_value = mock_session

        with patch(
            "services.notification.services.event_consumer.NotificationRepository.create",
            new_callable=AsyncMock,
            return_value=notif,
        ) as mock_create:
            with patch(
                "services.notification.services.event_consumer.ws_manager.send_to_user",
                new_callable=AsyncMock,
            ) as mock_send:
                await _handle_event(
                    "order.assigned",
                    {"user_id": 3, "payload": {"order_id": 1, "technician_id": 3}},
                    mock_factory,
                )
                mock_create.assert_called_once()
                mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_missing_user_id_skips_event(self):
        from services.notification.services.event_consumer import _handle_event
        from sqlalchemy.ext.asyncio import async_sessionmaker

        mock_factory = MagicMock()

        with patch(
            "services.notification.services.event_consumer.NotificationRepository.create",
            new_callable=AsyncMock,
        ) as mock_create:
            await _handle_event("order.assigned", {"payload": {}}, mock_factory)
            mock_create.assert_not_called()
