"""
Testes E2E — Asset Service.
Requerem PostgreSQL (TEST_DATABASE_URL). Pular com: pytest -m "not e2e"
"""

import pytest

pytestmark = pytest.mark.e2e

_PAYLOAD = {"name": "Bomba Hidráulica", "serial_number": "SN-BH-001", "location": "Sala A"}


class TestCreateAsset:
    async def test_supervisor_can_create_asset_201(self, asset_client_supervisor):
        r = await asset_client_supervisor.post("/api/v1/assets", json=_PAYLOAD)
        assert r.status_code == 201
        body = r.json()
        assert body["name"] == "Bomba Hidráulica"
        assert body["status"] == "active"
        assert "id" in body

    async def test_admin_can_create_asset_201(self, asset_client_admin):
        payload = {**_PAYLOAD, "serial_number": "SN-BH-002"}
        r = await asset_client_admin.post("/api/v1/assets", json=payload)
        assert r.status_code == 201

    async def test_technician_cannot_create_asset_403(self, asset_client_technician):
        r = await asset_client_technician.post("/api/v1/assets", json=_PAYLOAD)
        assert r.status_code == 403

    async def test_attendant_cannot_create_asset_403(self, asset_client_attendant):
        r = await asset_client_attendant.post("/api/v1/assets", json=_PAYLOAD)
        assert r.status_code == 403

    async def test_duplicate_serial_number_returns_409(self, asset_client_supervisor, seeded_asset):
        r = await asset_client_supervisor.post(
            "/api/v1/assets",
            json={"name": "Outro", "serial_number": seeded_asset["serial_number"]},
        )
        assert r.status_code == 409
        assert r.json()["code"] == "SERIAL_NUMBER_ALREADY_EXISTS"

    async def test_missing_name_returns_422(self, asset_client_supervisor):
        r = await asset_client_supervisor.post("/api/v1/assets", json={})
        assert r.status_code == 422


class TestListAssets:
    async def test_admin_can_list_assets_200(self, asset_client_admin, seeded_asset):
        r = await asset_client_admin.get("/api/v1/assets")
        assert r.status_code == 200
        body = r.json()
        assert "items" in body
        assert "total" in body
        assert body["total"] >= 1

    async def test_supervisor_can_list_assets_200(self, asset_client_supervisor, seeded_asset):
        r = await asset_client_supervisor.get("/api/v1/assets")
        assert r.status_code == 200

    async def test_technician_can_list_assets_200(self, asset_client_technician, seeded_asset):
        r = await asset_client_technician.get("/api/v1/assets")
        assert r.status_code == 200

    async def test_attendant_can_list_assets_200(self, asset_client_attendant, seeded_asset):
        r = await asset_client_attendant.get("/api/v1/assets")
        assert r.status_code == 200

    async def test_pagination_returns_correct_envelope(self, asset_client_admin):
        r = await asset_client_admin.get("/api/v1/assets?page=1&page_size=5")
        assert r.status_code == 200
        body = r.json()
        assert "page" in body
        assert "page_size" in body
        assert "pages" in body


class TestGetAsset:
    async def test_get_asset_by_id_200(self, asset_client_admin, seeded_asset):
        r = await asset_client_admin.get(f"/api/v1/assets/{seeded_asset['id']}")
        assert r.status_code == 200
        body = r.json()
        assert body["id"] == seeded_asset["id"]
        assert body["name"] == seeded_asset["name"]

    async def test_get_nonexistent_asset_404(self, asset_client_admin):
        r = await asset_client_admin.get("/api/v1/assets/999999")
        assert r.status_code == 404

    async def test_technician_can_get_asset_200(self, asset_client_technician, seeded_asset):
        r = await asset_client_technician.get(f"/api/v1/assets/{seeded_asset['id']}")
        assert r.status_code == 200


class TestUpdateAsset:
    async def test_supervisor_can_update_asset_200(self, asset_client_supervisor, seeded_asset):
        r = await asset_client_supervisor.put(
            f"/api/v1/assets/{seeded_asset['id']}",
            json={"name": "Compressor Atualizado", "location": "Sala B"},
        )
        assert r.status_code == 200
        assert r.json()["name"] == "Compressor Atualizado"

    async def test_technician_cannot_update_asset_403(self, asset_client_technician, seeded_asset):
        r = await asset_client_technician.put(
            f"/api/v1/assets/{seeded_asset['id']}",
            json={"name": "Tentativa"},
        )
        assert r.status_code == 403

    async def test_admin_can_deactivate_asset(self, asset_client_admin, seeded_asset):
        r = await asset_client_admin.patch(
            f"/api/v1/assets/{seeded_asset['id']}/status",
            json={"status": "inactive"},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "inactive"

    async def test_technician_cannot_change_asset_status_403(self, asset_client_technician, seeded_asset):
        r = await asset_client_technician.patch(
            f"/api/v1/assets/{seeded_asset['id']}/status",
            json={"status": "inactive"},
        )
        assert r.status_code == 403
