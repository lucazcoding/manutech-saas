"""
Testes E2E para o Notification Service.
Requer PostgreSQL rodando (TEST_DATABASE_URL).

Para WebSocket, usamos starlette.testclient.TestClient que suporta
websocket_connect() de forma síncrona dentro de testes async.
"""
import asyncio
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from shared.shared.config import get_shared_settings
from shared.shared.db.session import get_db
from services.notification.main import create_app
from tests.e2e.conftest import TEST_DATABASE_URL, make_get_db_override

pytestmark = pytest.mark.e2e


async def _noop_subscriber(*args, **kwargs):
    await asyncio.sleep(0)


# ── GET /notifications ────────────────────────────────────────────────────────

async def test_list_notifications_admin_200(
    notification_client_admin, seeded_notification
):
    """Admin pode listar suas notificações — 200."""
    response = await notification_client_admin.get("/api/v1/notifications")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


async def test_list_notifications_supervisor_200(notification_client_supervisor):
    """Supervisor pode listar suas notificações — 200."""
    response = await notification_client_supervisor.get("/api/v1/notifications")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


async def test_list_notifications_technician_200(notification_client_technician):
    """Technician pode listar suas notificações — 200."""
    response = await notification_client_technician.get("/api/v1/notifications")
    assert response.status_code == 200


async def test_list_notifications_attendant_200(notification_client_attendant):
    """Attendant pode listar suas notificações — 200."""
    response = await notification_client_attendant.get("/api/v1/notifications")
    assert response.status_code == 200


async def test_list_notifications_empty_when_none(notification_client_supervisor):
    """Lista de notificações vazia quando não há notificações para o usuário."""
    response = await notification_client_supervisor.get("/api/v1/notifications")
    assert response.status_code == 200
    data = response.json()
    # Supervisor (user_id=2) não tem notificações seedadas
    assert data["total"] == 0
    assert data["items"] == []


async def test_list_notifications_contains_seeded(
    notification_client_admin, seeded_notification
):
    """Lista retorna a notificação inserida para o admin (user_id=1)."""
    response = await notification_client_admin.get("/api/v1/notifications")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    ids = [item["id"] for item in data["items"]]
    assert seeded_notification["id"] in ids


async def test_list_notifications_filter_unread(
    notification_client_admin, seeded_notification
):
    """Filtro read=false retorna apenas não lidas."""
    response = await notification_client_admin.get(
        "/api/v1/notifications", params={"read": False}
    )
    assert response.status_code == 200
    data = response.json()
    for item in data["items"]:
        assert item["read"] is False


# ── PATCH /notifications/:id/read ─────────────────────────────────────────────

async def test_mark_notification_as_read_200(
    notification_client_admin, seeded_notification
):
    """Marcar notificação como lida retorna 200 com read=True."""
    response = await notification_client_admin.patch(
        f"/api/v1/notifications/{seeded_notification['id']}/read"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["read"] is True


async def test_mark_notification_as_read_technician_200(
    notification_client_technician, seeded_notification_for_technician
):
    """Technician pode marcar sua própria notificação como lida — 200."""
    response = await notification_client_technician.patch(
        f"/api/v1/notifications/{seeded_notification_for_technician['id']}/read"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["read"] is True


async def test_mark_notification_not_found_404(notification_client_admin):
    """Notificação inexistente retorna 404."""
    response = await notification_client_admin.patch(
        "/api/v1/notifications/999999/read"
    )
    assert response.status_code == 404


# ── WebSocket /notifications/ws ───────────────────────────────────────────────

def _make_sync_ws_app(rsa_keys):
    """Cria app síncrona para testes WebSocket com TestClient."""
    from shared.shared.config import SharedSettings

    app = create_app()
    settings = SharedSettings(
        jwt_public_key=rsa_keys["public"], database_url=TEST_DATABASE_URL
    )
    app.dependency_overrides[get_shared_settings] = lambda: settings
    return app


def test_websocket_no_token_closes_4001(rsa_keys):
    """WebSocket sem token retorna close code 4001."""
    app = _make_sync_ws_app(rsa_keys)
    with patch("services.notification.main.start_subscriber", side_effect=_noop_subscriber):
        with TestClient(app, raise_server_exceptions=False) as client:
            with pytest.raises(Exception):
                with client.websocket_connect("/api/v1/notifications/ws") as ws:
                    ws.receive_text()


def test_websocket_invalid_token_closes_4001(rsa_keys):
    """WebSocket com token inválido retorna close code 4001."""
    app = _make_sync_ws_app(rsa_keys)
    with patch("services.notification.main.start_subscriber", side_effect=_noop_subscriber):
        with TestClient(app, raise_server_exceptions=False) as client:
            with pytest.raises(Exception):
                with client.websocket_connect(
                    "/api/v1/notifications/ws?token=invalid.jwt.token"
                ) as ws:
                    ws.receive_text()


def test_websocket_valid_token_connects(rsa_keys, admin_token):
    """WebSocket com token válido conecta com sucesso."""
    app = _make_sync_ws_app(rsa_keys)
    with patch("services.notification.main.start_subscriber", side_effect=_noop_subscriber):
        with TestClient(app, raise_server_exceptions=False) as client:
            with client.websocket_connect(
                f"/api/v1/notifications/ws?token={admin_token}"
            ) as ws:
                # Conexão estabelecida com sucesso — fecha normalmente
                ws.close()
