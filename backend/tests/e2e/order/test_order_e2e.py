"""
Testes E2E — Order Service.
Requerem PostgreSQL (TEST_DATABASE_URL). Pular com: pytest -m "not e2e"
"""

import pytest

pytestmark = pytest.mark.e2e

_ORDER_PAYLOAD = {"client_name": "Empresa Teste", "location": "Rua A, 100", "priority": "high"}


class TestCreateOrder:
    async def test_supervisor_can_create_order_201(self, order_client_supervisor):
        r = await order_client_supervisor.post("/api/v1/orders", json=_ORDER_PAYLOAD)
        assert r.status_code == 201
        body = r.json()
        assert body["client_name"] == "Empresa Teste"
        assert body["status"] == "open"
        assert body["priority"] == "high"
        assert body["assigned_technician"] is None

    async def test_attendant_can_create_order_201(self, order_client_attendant):
        r = await order_client_attendant.post("/api/v1/orders", json=_ORDER_PAYLOAD)
        assert r.status_code == 201

    async def test_admin_can_create_order_201(self, order_client_admin):
        r = await order_client_admin.post("/api/v1/orders", json=_ORDER_PAYLOAD)
        assert r.status_code == 201
        body = r.json()
        assert body["client_name"] == "Empresa Teste"
        assert body["status"] == "open"

    async def test_technician_cannot_create_order_403(self, order_client_technician):
        r = await order_client_technician.post("/api/v1/orders", json=_ORDER_PAYLOAD)
        assert r.status_code == 403

    async def test_missing_client_name_returns_422(self, order_client_supervisor):
        r = await order_client_supervisor.post("/api/v1/orders", json={"location": "Rua X"})
        assert r.status_code == 422

    async def test_invalid_priority_returns_422(self, order_client_supervisor):
        r = await order_client_supervisor.post(
            "/api/v1/orders",
            json={**_ORDER_PAYLOAD, "priority": "critical"},
        )
        assert r.status_code == 422


class TestListOrders:
    async def test_admin_can_list_orders_200(self, order_client_admin, seeded_order):
        r = await order_client_admin.get("/api/v1/orders")
        assert r.status_code == 200
        body = r.json()
        assert "items" in body
        assert body["total"] >= 1

    async def test_supervisor_can_list_orders_200(self, order_client_supervisor, seeded_order):
        r = await order_client_supervisor.get("/api/v1/orders")
        assert r.status_code == 200

    async def test_attendant_cannot_list_orders_403(self, order_client_attendant):
        r = await order_client_attendant.get("/api/v1/orders")
        assert r.status_code == 403

    async def test_get_order_by_id_200(self, order_client_admin, seeded_order):
        r = await order_client_admin.get(f"/api/v1/orders/{seeded_order['id']}")
        assert r.status_code == 200
        assert r.json()["id"] == seeded_order["id"]

    async def test_get_nonexistent_order_404(self, order_client_admin):
        r = await order_client_admin.get("/api/v1/orders/999999")
        assert r.status_code == 404


class TestOrderStats:
    async def test_admin_can_get_stats_200(self, order_client_admin, seeded_order):
        r = await order_client_admin.get("/api/v1/orders/stats")
        assert r.status_code == 200
        body = r.json()
        assert "total" in body
        assert "by_status" in body

    async def test_supervisor_can_get_stats_200(self, order_client_supervisor, seeded_order):
        r = await order_client_supervisor.get("/api/v1/orders/stats")
        assert r.status_code == 200

    async def test_technician_cannot_get_stats_403(self, order_client_technician):
        r = await order_client_technician.get("/api/v1/orders/stats")
        assert r.status_code == 403

    async def test_attendant_cannot_get_stats_403(self, order_client_attendant):
        r = await order_client_attendant.get("/api/v1/orders/stats")
        assert r.status_code == 403


class TestAssignTechnician:
    async def test_supervisor_can_assign_technician(
        self, order_client_supervisor, seeded_order, seeded_technician_user
    ):
        r = await order_client_supervisor.patch(
            f"/api/v1/orders/{seeded_order['id']}/assign",
            json={"technician_id": seeded_technician_user["id"]},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["assigned_technician"] is not None
        assert body["assigned_technician"]["id"] == seeded_technician_user["id"]

    async def test_admin_can_assign_technician_200(
        self, order_client_admin, seeded_order, seeded_technician_user
    ):
        r = await order_client_admin.patch(
            f"/api/v1/orders/{seeded_order['id']}/assign",
            json={"technician_id": seeded_technician_user["id"]},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["assigned_technician"] is not None
        assert body["assigned_technician"]["id"] == seeded_technician_user["id"]


class TestStatusTransitions:
    async def test_supervisor_can_cancel_open_order_with_reason(
        self, order_client_supervisor, seeded_order
    ):
        r = await order_client_supervisor.patch(
            f"/api/v1/orders/{seeded_order['id']}/status",
            json={"status": "cancelled", "reason": "Cliente desistiu"},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "cancelled"

    async def test_cancel_without_reason_returns_400(
        self, order_client_supervisor, seeded_order
    ):
        r = await order_client_supervisor.patch(
            f"/api/v1/orders/{seeded_order['id']}/status",
            json={"status": "cancelled"},
        )
        assert r.status_code == 400
        assert r.json()["code"] == "CANCELLATION_REASON_REQUIRED"

    async def test_open_to_in_progress_without_technician_returns_400(
        self, order_client_supervisor, seeded_order
    ):
        r = await order_client_supervisor.patch(
            f"/api/v1/orders/{seeded_order['id']}/status",
            json={"status": "in_progress"},
        )
        assert r.status_code == 400
        assert r.json()["code"] == "TECHNICIAN_REQUIRED"

    async def test_in_progress_to_completed(
        self, order_client_supervisor, seeded_in_progress_order
    ):
        r = await order_client_supervisor.patch(
            f"/api/v1/orders/{seeded_in_progress_order['id']}/status",
            json={"status": "completed"},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "completed"

    async def test_invalid_transition_open_to_completed_returns_400(
        self, order_client_supervisor, seeded_order
    ):
        r = await order_client_supervisor.patch(
            f"/api/v1/orders/{seeded_order['id']}/status",
            json={"status": "completed"},
        )
        assert r.status_code == 400
        assert r.json()["code"] == "INVALID_STATUS_TRANSITION"

    async def test_attendant_cannot_change_status_403(
        self, order_client_attendant, seeded_order
    ):
        r = await order_client_attendant.patch(
            f"/api/v1/orders/{seeded_order['id']}/status",
            json={"status": "cancelled", "reason": "Teste"},
        )
        assert r.status_code == 403


class TestDeleteOrder:
    async def test_admin_can_delete_open_order_204(
        self, order_client_admin, seeded_order
    ):
        r = await order_client_admin.delete(f"/api/v1/orders/{seeded_order['id']}")
        assert r.status_code == 204

    async def test_technician_cannot_delete_order_403(
        self, order_client_technician, seeded_order
    ):
        r = await order_client_technician.delete(f"/api/v1/orders/{seeded_order['id']}")
        assert r.status_code == 403
