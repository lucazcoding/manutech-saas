"""
Testes E2E para o Finance Service.
Requer PostgreSQL rodando (TEST_DATABASE_URL).
"""
import pytest

pytestmark = pytest.mark.e2e


# ── POST /costs ───────────────────────────────────────────────────────────────

async def test_create_cost_supervisor_201(finance_client_supervisor, seeded_order):
    """Supervisor pode criar custo — 201."""
    response = await finance_client_supervisor.post(
        "/api/v1/costs",
        json={
            "service_order_id": seeded_order["id"],
            "description": "Mão de obra E2E",
            "amount": 200.00,
            "cost_type": "labor",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["description"] == "Mão de obra E2E"
    assert data["service_order_id"] == seeded_order["id"]


async def test_create_cost_technician_201(finance_client_technician, seeded_order):
    """Technician pode criar custo — 201."""
    response = await finance_client_technician.post(
        "/api/v1/costs",
        json={
            "service_order_id": seeded_order["id"],
            "description": "Material usado",
            "amount": 50.00,
            "cost_type": "material",
        },
    )
    assert response.status_code == 201


async def test_create_cost_attendant_403(finance_client_attendant, seeded_order):
    """Attendant não pode criar custo — 403."""
    response = await finance_client_attendant.post(
        "/api/v1/costs",
        json={
            "service_order_id": seeded_order["id"],
            "description": "Tentativa",
            "amount": 10.00,
        },
    )
    assert response.status_code == 403


async def test_create_cost_admin_201(finance_client_admin, seeded_order):
    """Admin pode criar custo — 201."""
    response = await finance_client_admin.post(
        "/api/v1/costs",
        json={
            "service_order_id": seeded_order["id"],
            "description": "Custo Admin",
            "amount": 100.00,
        },
    )
    assert response.status_code == 201


# ── GET /costs ────────────────────────────────────────────────────────────────

async def test_list_costs_admin_200(finance_client_admin, seeded_cost):
    """Admin pode listar custos — 200."""
    response = await finance_client_admin.get("/api/v1/costs")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


async def test_list_costs_supervisor_200(finance_client_supervisor, seeded_cost):
    """Supervisor pode listar custos — 200."""
    response = await finance_client_supervisor.get("/api/v1/costs")
    assert response.status_code == 200


async def test_list_costs_technician_403(finance_client_technician):
    """Technician não pode listar custos — 403."""
    response = await finance_client_technician.get("/api/v1/costs")
    assert response.status_code == 403


# ── PUT /costs/:id ────────────────────────────────────────────────────────────

async def test_update_cost_admin_200(finance_client_admin, seeded_cost):
    """Admin pode atualizar custo — 200."""
    response = await finance_client_admin.put(
        f"/api/v1/costs/{seeded_cost['id']}",
        json={"description": "Custo Atualizado E2E", "amount": 300.00},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Custo Atualizado E2E"


async def test_update_cost_supervisor_200(finance_client_supervisor, seeded_cost):
    """Supervisor pode atualizar custo — 200."""
    response = await finance_client_supervisor.put(
        f"/api/v1/costs/{seeded_cost['id']}",
        json={"amount": 250.00},
    )
    assert response.status_code == 200


async def test_update_cost_technician_403(finance_client_technician, seeded_cost):
    """Technician não pode atualizar custo — 403."""
    response = await finance_client_technician.put(
        f"/api/v1/costs/{seeded_cost['id']}",
        json={"amount": 1.00},
    )
    assert response.status_code == 403


async def test_update_cost_not_found_404(finance_client_admin):
    """Custo inexistente retorna 404."""
    response = await finance_client_admin.put(
        "/api/v1/costs/999999",
        json={"description": "Inexistente"},
    )
    assert response.status_code == 404


# ── DELETE /costs/:id ─────────────────────────────────────────────────────────

async def test_delete_cost_admin_204(finance_client_admin, seeded_cost):
    """Admin pode deletar custo — 204."""
    response = await finance_client_admin.delete(f"/api/v1/costs/{seeded_cost['id']}")
    assert response.status_code == 204


async def test_delete_cost_supervisor_204(finance_client_supervisor, seeded_order):
    """Supervisor pode deletar custo — 204."""
    # Cria custo para deletar
    create_resp = await finance_client_supervisor.post(
        "/api/v1/costs",
        json={
            "service_order_id": seeded_order["id"],
            "description": "Custo para deletar",
            "amount": 10.00,
        },
    )
    assert create_resp.status_code == 201
    cost_id = create_resp.json()["id"]

    response = await finance_client_supervisor.delete(f"/api/v1/costs/{cost_id}")
    assert response.status_code == 204


# ── POST /budgets ─────────────────────────────────────────────────────────────

async def test_create_budget_supervisor_201(finance_client_supervisor, seeded_order):
    """Supervisor pode criar orçamento — 201."""
    response = await finance_client_supervisor.post(
        "/api/v1/budgets",
        json={
            "service_order_id": seeded_order["id"],
            "client_name": "Cliente Orçamento E2E",
            "description": "Orçamento para manutenção",
            "items": [
                {"description": "Peça 1", "quantity": 2.0, "unit_price": 50.00},
                {"description": "Mão de obra", "quantity": 1.0, "unit_price": 150.00},
            ],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "draft"
    assert data["client_name"] == "Cliente Orçamento E2E"
    assert len(data["items"]) == 2


async def test_create_budget_admin_201(finance_client_admin, seeded_order):
    """Admin pode criar orçamento — 201."""
    response = await finance_client_admin.post(
        "/api/v1/budgets",
        json={
            "client_name": "Admin Budget",
            "items": [],
        },
    )
    assert response.status_code == 201


async def test_create_budget_technician_403(finance_client_technician, seeded_order):
    """Technician não pode criar orçamento — 403."""
    response = await finance_client_technician.post(
        "/api/v1/budgets",
        json={"client_name": "Proibido", "items": []},
    )
    assert response.status_code == 403


# ── GET /budgets ──────────────────────────────────────────────────────────────

async def test_list_budgets_admin_200(finance_client_admin, seeded_budget_draft):
    """Admin pode listar orçamentos — 200."""
    response = await finance_client_admin.get("/api/v1/budgets")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


async def test_list_budgets_supervisor_200(finance_client_supervisor, seeded_budget_draft):
    """Supervisor pode listar orçamentos — 200."""
    response = await finance_client_supervisor.get("/api/v1/budgets")
    assert response.status_code == 200


async def test_list_budgets_technician_403(finance_client_technician):
    """Technician não pode listar orçamentos — 403."""
    response = await finance_client_technician.get("/api/v1/budgets")
    assert response.status_code == 403


# ── PUT /budgets/:id ──────────────────────────────────────────────────────────

async def test_update_budget_draft_supervisor_200(
    finance_client_supervisor, seeded_budget_draft
):
    """Supervisor pode editar orçamento em draft — 200."""
    response = await finance_client_supervisor.put(
        f"/api/v1/budgets/{seeded_budget_draft['id']}",
        json={"client_name": "Cliente Budget Atualizado"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["client_name"] == "Cliente Budget Atualizado"


async def test_update_budget_not_draft_400(finance_client_supervisor, seeded_budget_sent):
    """Editar orçamento em status 'sent' retorna 400 BUDGET_NOT_EDITABLE."""
    response = await finance_client_supervisor.put(
        f"/api/v1/budgets/{seeded_budget_sent['id']}",
        json={"client_name": "Tentativa de Edição"},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["code"] == "BUDGET_NOT_EDITABLE"


async def test_update_budget_technician_403(finance_client_technician, seeded_budget_draft):
    """Technician não pode editar orçamento — 403."""
    response = await finance_client_technician.put(
        f"/api/v1/budgets/{seeded_budget_draft['id']}",
        json={"client_name": "Proibido"},
    )
    assert response.status_code == 403


# ── GET /orders/:id/budget ────────────────────────────────────────────────────

async def test_get_order_budget_admin_200(
    finance_client_admin, seeded_budget_draft, seeded_order
):
    """Admin pode ver orçamento da OS — 200."""
    response = await finance_client_admin.get(
        f"/api/v1/orders/{seeded_order['id']}/budget"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["service_order_id"] == seeded_order["id"]


async def test_get_order_budget_supervisor_200(
    finance_client_supervisor, seeded_budget_draft, seeded_order
):
    """Supervisor pode ver orçamento da OS — 200."""
    response = await finance_client_supervisor.get(
        f"/api/v1/orders/{seeded_order['id']}/budget"
    )
    assert response.status_code == 200


async def test_get_order_budget_technician_200(
    finance_client_technician, seeded_budget_draft, seeded_order
):
    """Technician pode ver orçamento da OS — 200."""
    response = await finance_client_technician.get(
        f"/api/v1/orders/{seeded_order['id']}/budget"
    )
    assert response.status_code == 200


async def test_get_order_budget_attendant_403(
    finance_client_attendant, seeded_budget_draft, seeded_order
):
    """Attendant não pode ver orçamento da OS — 403."""
    response = await finance_client_attendant.get(
        f"/api/v1/orders/{seeded_order['id']}/budget"
    )
    assert response.status_code == 403


async def test_get_order_budget_not_found_404(finance_client_admin):
    """OS sem orçamento retorna 404."""
    # Inserir OS sem budget
    response = await finance_client_admin.get("/api/v1/orders/999999/budget")
    assert response.status_code == 404


# ── GET /reports/financial ────────────────────────────────────────────────────

async def test_financial_report_admin_200(finance_client_admin, seeded_cost):
    """Admin pode ver relatório financeiro — 200."""
    response = await finance_client_admin.get("/api/v1/reports/financial")
    assert response.status_code == 200
    data = response.json()
    assert "total_costs" in data
    assert "costs_by_type" in data
    assert "orders_count" in data
    assert "avg_cost_per_order" in data


async def test_financial_report_supervisor_200(finance_client_supervisor):
    """Supervisor pode ver relatório financeiro — 200."""
    response = await finance_client_supervisor.get("/api/v1/reports/financial")
    assert response.status_code == 200


async def test_financial_report_technician_403(finance_client_technician):
    """Technician não pode ver relatório financeiro — 403."""
    response = await finance_client_technician.get("/api/v1/reports/financial")
    assert response.status_code == 403
