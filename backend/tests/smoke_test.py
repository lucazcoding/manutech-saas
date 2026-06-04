#!/usr/bin/env python3
"""
MANUTECH Smoke Test — valida os endpoints críticos de todos os 6 microserviços.

Uso:
    python tests/smoke_test.py
    # ou, com .venv:
    .venv\\Scripts\\python.exe tests\\smoke_test.py
    # ou via pytest:
    pytest tests/smoke_test.py -v
"""
import sys
import time

import httpx

# Força UTF-8 no stdout do Windows (evita UnicodeEncodeError com ✅/❌/═)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ── Configuração ───────────────────────────────────────────────────────────────
BASE_URL = "http://localhost"
ADMIN_LOGIN = "admin"
ADMIN_PASSWORD = "admin123"


def section(title: str) -> None:
    print(f"\n{'═'*55}")
    print(f"  {title}")
    print(f"{'═'*55}")


def run_smoke() -> int:
    """Executa todos os checks e retorna o número de falhas."""
    results: list[tuple[str, bool, int, int]] = []

    def check(label: str, method: str, path: str, expected: int, **kwargs) -> dict | None:
        url = f"{BASE_URL}{path}"
        try:
            r = httpx.request(method, url, timeout=15, **kwargs)
            ok = r.status_code == expected
            icon = "✅" if ok else "❌"
            print(f"  {icon} [{r.status_code:3d}] {label}")
            if not ok:
                try:
                    body = r.json()
                except Exception:
                    body = r.text[:300]
                print(f"         → {body}")
            results.append((label, ok, r.status_code, expected))
            if not ok:
                return None
            try:
                return r.json()
            except Exception:
                return {}
        except Exception as exc:
            print(f"  ❌ [ERR] {label}")
            print(f"         → {exc}")
            results.append((label, False, 0, expected))
            return None

    def skip(label: str, reason: str) -> None:
        print(f"  ⏭  [ -- ] {label}  ({reason})")

    # ══════════════════════════════════════════════════════════════════════════
    # SETUP — login + criação do supervisor
    # ══════════════════════════════════════════════════════════════════════════
    ts = int(time.time())
    sup_login = f"sup_smoke_{ts}"

    # ─── AUTH ─────────────────────────────────────────────────────────────────
    section("AUTH SERVICE  (porta 8001)")

    data = check("POST /api/v1/auth/login", "POST", "/api/v1/auth/login", 200,
                 json={"login": ADMIN_LOGIN, "password": ADMIN_PASSWORD})
    admin_token = (data or {}).get("access_token", "")
    admin_h = {"Authorization": f"Bearer {admin_token}"}

    check("GET  /api/v1/auth/me", "GET", "/api/v1/auth/me", 200, headers=admin_h)

    data = check("POST /api/v1/users  (criar supervisor)", "POST", "/api/v1/users", 201,
                 headers=admin_h,
                 json={"name": "Supervisor Smoke", "login": sup_login,
                       "email": f"{sup_login}@smoke.test",
                       "password": "Smoke@1234", "role": "supervisor"})
    _sup_created = data is not None

    check("GET  /api/v1/users", "GET", "/api/v1/users", 200, headers=admin_h)

    sup_token = ""
    if _sup_created:
        r2 = httpx.post(f"{BASE_URL}/api/v1/auth/login",
                        json={"login": sup_login, "password": "Smoke@1234"}, timeout=10)
        sup_token = r2.json().get("access_token", "") if r2.status_code == 200 else ""

    sup_h = {"Authorization": f"Bearer {sup_token}"} if sup_token else admin_h

    # ─── ASSETS ───────────────────────────────────────────────────────────────
    section("ASSET SERVICE  (porta 8002)")

    check("GET  /api/v1/assets", "GET", "/api/v1/assets", 200, headers=admin_h)

    data = check("POST /api/v1/assets", "POST", "/api/v1/assets", 201,
                 headers=admin_h,
                 json={"name": f"Equipamento Smoke {ts}", "model": "SM-100",
                       "manufacturer": "ACME Ltda", "location": "Galpão A"})
    asset_id: int | None = (data or {}).get("id")

    if asset_id:
        check(f"GET  /api/v1/assets/{{id}}  (id={asset_id})",
              "GET", f"/api/v1/assets/{asset_id}", 200, headers=admin_h)

        check(f"PATCH /api/v1/assets/{{id}}/status  → inactive",
              "PATCH", f"/api/v1/assets/{asset_id}/status", 200,
              headers=admin_h, json={"status": "inactive"})

        httpx.patch(f"{BASE_URL}/api/v1/assets/{asset_id}/status",
                    headers=admin_h, json={"status": "active"}, timeout=10)
    else:
        skip("GET  /api/v1/assets/{id}", "asset não criado")
        skip("PATCH /api/v1/assets/{id}/status", "asset não criado")

    # ─── ORDERS ───────────────────────────────────────────────────────────────
    section("ORDER SERVICE  (porta 8003)")

    check("GET  /api/v1/orders", "GET", "/api/v1/orders", 200, headers=admin_h)
    check("GET  /api/v1/orders/stats", "GET", "/api/v1/orders/stats", 200, headers=admin_h)

    data = check("POST /api/v1/orders  (supervisor)", "POST", "/api/v1/orders", 201,
                 headers=sup_h,
                 json={"client_name": "Cliente Smoke", "location": "Rua Smoke, 42",
                       "description": "OS criada pelo smoke test", "priority": "medium",
                       "asset_id": asset_id})
    order_id: int | None = (data or {}).get("id")

    if order_id:
        check(f"GET  /api/v1/orders/{{id}}  (id={order_id})",
              "GET", f"/api/v1/orders/{order_id}", 200, headers=admin_h)
    else:
        skip("GET  /api/v1/orders/{id}", "OS não criada")

    # ─── INVENTORY ────────────────────────────────────────────────────────────
    section("INVENTORY SERVICE  (porta 8004)")

    check("GET  /api/v1/materials", "GET", "/api/v1/materials", 200, headers=admin_h)

    data = check("POST /api/v1/materials", "POST", "/api/v1/materials", 201,
                 headers=admin_h,
                 json={"name": f"Material Smoke {ts}", "sku": f"SKU-SMOKE-{ts}",
                       "unit_price": 25.50, "quantity_in_stock": 100.0, "min_quantity": 5.0})
    material_id: int | None = (data or {}).get("id")

    if material_id:
        check(f"GET  /api/v1/materials/{{id}}  (id={material_id})",
              "GET", f"/api/v1/materials/{material_id}", 200, headers=admin_h)
    else:
        skip("GET  /api/v1/materials/{id}", "material não criado")

    # ─── FINANCE ──────────────────────────────────────────────────────────────
    section("FINANCE SERVICE  (porta 8005)")

    check("GET  /api/v1/costs", "GET", "/api/v1/costs", 200, headers=admin_h)

    if order_id:
        check("POST /api/v1/costs  (supervisor)", "POST", "/api/v1/costs", 201,
              headers=sup_h,
              json={"service_order_id": order_id, "description": "Mão de obra smoke",
                    "amount": 99.99, "cost_type": "labor"})
    else:
        skip("POST /api/v1/costs", "OS não criada")

    check("GET  /api/v1/budgets", "GET", "/api/v1/budgets", 200, headers=admin_h)

    if order_id:
        check("POST /api/v1/budgets  (supervisor)", "POST", "/api/v1/budgets", 201,
              headers=sup_h,
              json={"client_name": "Cliente Smoke", "service_order_id": order_id,
                    "description": "Orçamento smoke test", "valid_until": "2026-12-31",
                    "items": []})
    else:
        skip("POST /api/v1/budgets", "OS não criada")

    check("GET  /api/v1/reports/financial", "GET", "/api/v1/reports/financial", 200,
          headers=admin_h)

    # ─── ORDER STATUS (após Finance — evita ORDER_CLOSED em costs/budgets) ────
    section("ORDER SERVICE  → mudança de status")

    if order_id:
        check(f"PATCH /api/v1/orders/{{id}}/status  → cancelled  (supervisor)",
              "PATCH", f"/api/v1/orders/{order_id}/status", 200,
              headers=sup_h,
              json={"status": "cancelled", "reason": "Cancelado pelo smoke test"})
    else:
        skip("PATCH /api/v1/orders/{id}/status", "OS não criada")

    # ─── NOTIFICATIONS ────────────────────────────────────────────────────────
    section("NOTIFICATION SERVICE  (porta 8006)")

    check("GET  /api/v1/notifications", "GET", "/api/v1/notifications", 200, headers=admin_h)

    # ── Sumário ───────────────────────────────────────────────────────────────
    total_ok = sum(1 for _, ok, _, _ in results if ok)
    total = len(results)
    failures = [(lbl, got, exp) for lbl, ok, got, exp in results if not ok]

    print(f"\n{'═'*55}")
    print(f"  RESULTADO FINAL: {total_ok}/{total} testes passaram")

    if failures:
        print(f"\n  Falhas ({len(failures)}):")
        for lbl, got, exp in failures:
            print(f"    ❌ {lbl}")
            print(f"       esperado={exp}  recebido={got}")

    print(f"{'═'*55}\n")

    return len(failures)


def main() -> None:
    failures = run_smoke()
    sys.exit(0 if failures == 0 else 1)


# ── Ponto de entrada pytest ────────────────────────────────────────────────────
def test_smoke() -> None:
    failures = run_smoke()
    assert failures == 0, f"{failures} endpoint(s) falharam no smoke test"


if __name__ == "__main__":
    main()
