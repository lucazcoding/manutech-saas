"""
Testes E2E — Inventory Service.
Requerem PostgreSQL (TEST_DATABASE_URL). Pular com: pytest -m "not e2e"
"""

import pytest

pytestmark = pytest.mark.e2e

_MAT_PAYLOAD = {
    "name": "Rolamento 6204",
    "sku": "SKU-R6204",
    "unit_price": 15.90,
    "quantity_in_stock": 50.0,
    "min_quantity": 10.0,
}


class TestCreateMaterial:
    async def test_supervisor_can_create_material_201(self, inv_client_supervisor):
        r = await inv_client_supervisor.post("/api/v1/materials", json=_MAT_PAYLOAD)
        assert r.status_code == 201
        body = r.json()
        assert body["name"] == "Rolamento 6204"
        assert body["sku"] == "SKU-R6204"
        assert body["status"] == "active"

    async def test_admin_can_create_material_201(self, inv_client_admin):
        payload = {**_MAT_PAYLOAD, "sku": "SKU-R6204-ADM"}
        r = await inv_client_admin.post("/api/v1/materials", json=payload)
        assert r.status_code == 201

    async def test_technician_cannot_create_material_403(self, inv_client_technician):
        r = await inv_client_technician.post("/api/v1/materials", json=_MAT_PAYLOAD)
        assert r.status_code == 403

    async def test_attendant_cannot_create_material_403(self, inv_client_attendant):
        r = await inv_client_attendant.post("/api/v1/materials", json=_MAT_PAYLOAD)
        assert r.status_code == 403

    async def test_duplicate_sku_returns_409(self, inv_client_supervisor, seeded_material):
        r = await inv_client_supervisor.post(
            "/api/v1/materials",
            json={**_MAT_PAYLOAD, "sku": seeded_material["sku"]},
        )
        assert r.status_code == 409
        assert r.json()["code"] == "SKU_ALREADY_EXISTS"


class TestListMaterials:
    async def test_admin_can_list_materials_200(self, inv_client_admin, seeded_material):
        r = await inv_client_admin.get("/api/v1/materials")
        assert r.status_code == 200
        body = r.json()
        assert "items" in body
        assert body["total"] >= 1

    async def test_technician_can_list_materials_200(self, inv_client_technician, seeded_material):
        r = await inv_client_technician.get("/api/v1/materials")
        assert r.status_code == 200

    async def test_attendant_can_list_materials_200(self, inv_client_attendant, seeded_material):
        r = await inv_client_attendant.get("/api/v1/materials")
        assert r.status_code == 200

    async def test_get_material_by_id_200(self, inv_client_admin, seeded_material):
        r = await inv_client_admin.get(f"/api/v1/materials/{seeded_material['id']}")
        assert r.status_code == 200
        assert r.json()["id"] == seeded_material["id"]

    async def test_get_nonexistent_material_404(self, inv_client_admin):
        r = await inv_client_admin.get("/api/v1/materials/999999")
        assert r.status_code == 404


class TestMaterialStatus:
    async def test_admin_can_deactivate_material(self, inv_client_admin, seeded_material):
        r = await inv_client_admin.patch(
            f"/api/v1/materials/{seeded_material['id']}/status",
            json={"status": "inactive"},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "inactive"

    async def test_supervisor_cannot_change_material_status_403(
        self, inv_client_supervisor, seeded_material
    ):
        r = await inv_client_supervisor.patch(
            f"/api/v1/materials/{seeded_material['id']}/status",
            json={"status": "inactive"},
        )
        assert r.status_code == 403


class TestStockMovements:
    async def test_supervisor_can_create_movement_in_201(
        self, inv_client_supervisor, seeded_material, seeded_order_for_movement
    ):
        r = await inv_client_supervisor.post(
            "/api/v1/movements",
            json={
                "material_id": seeded_material["id"],
                "service_order_id": seeded_order_for_movement["id"],
                "movement_type": "in",
                "quantity": 20.0,
                "notes": "Entrada de teste",
            },
        )
        assert r.status_code == 201
        body = r.json()
        assert body["movement_type"] == "in"
        assert float(body["quantity"]) == 20.0

    async def test_technician_can_create_movement_201(
        self, inv_client_technician, seeded_material, seeded_order_for_movement
    ):
        r = await inv_client_technician.post(
            "/api/v1/movements",
            json={
                "material_id": seeded_material["id"],
                "service_order_id": seeded_order_for_movement["id"],
                "movement_type": "out",
                "quantity": 5.0,
            },
        )
        assert r.status_code == 201

    async def test_attendant_cannot_create_movement_403(
        self, inv_client_attendant, seeded_material, seeded_order_for_movement
    ):
        r = await inv_client_attendant.post(
            "/api/v1/movements",
            json={
                "material_id": seeded_material["id"],
                "service_order_id": seeded_order_for_movement["id"],
                "movement_type": "out",
                "quantity": 5.0,
            },
        )
        assert r.status_code == 403

    async def test_out_exceeding_stock_returns_400(
        self, inv_client_supervisor, seeded_material, seeded_order_for_movement
    ):
        r = await inv_client_supervisor.post(
            "/api/v1/movements",
            json={
                "material_id": seeded_material["id"],
                "service_order_id": seeded_order_for_movement["id"],
                "movement_type": "out",
                "quantity": 9999.0,
            },
        )
        assert r.status_code == 400
        assert r.json()["code"] == "INSUFFICIENT_STOCK"

    async def test_admin_can_list_movements_200(
        self, inv_client_admin, seeded_material, seeded_order_for_movement
    ):
        r = await inv_client_admin.get("/api/v1/movements")
        assert r.status_code == 200
        assert "items" in r.json()

    async def test_technician_can_list_movements_200(self, inv_client_technician, seeded_material, seeded_order_for_movement):
        r = await inv_client_technician.get("/api/v1/movements")
        assert r.status_code == 200
        assert "items" in r.json()


class TestStockReport:
    async def test_admin_can_get_stock_report_200(self, inv_client_admin, seeded_material):
        r = await inv_client_admin.get("/api/v1/stock/report")
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, list)
        assert len(body) >= 1
        assert "is_low_stock" in body[0]

    async def test_supervisor_can_get_stock_report_200(self, inv_client_supervisor, seeded_material):
        r = await inv_client_supervisor.get("/api/v1/stock/report")
        assert r.status_code == 200

    async def test_technician_cannot_get_stock_report_403(self, inv_client_technician):
        r = await inv_client_technician.get("/api/v1/stock/report")
        assert r.status_code == 403
