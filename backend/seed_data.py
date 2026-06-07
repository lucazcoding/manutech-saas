"""Seed: dados demo coerentes para a primeira execução do sistema.

Cria usuários, equipamentos, materiais, movimentações de estoque, ordens de
serviço, custos, orçamentos e notificações — todos com IDs/valores cruzados
de forma realista.

Uso:
    # dentro do container (já configurado pelo docker-compose)
    python seed_data.py

    # ou manualmente, exportando a DATABASE_URL do .env
    set DATABASE_URL=postgresql+psycopg://postgres:senha@localhost:5433/manutech
    python seed_data.py

Idempotência: se o usuário 'joao.silva' já existir, o script encerra sem
inserir nada. Para semear do zero: docker compose down -v.
"""
import asyncio
import os
from datetime import date, datetime, timedelta, timezone

import bcrypt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = os.environ["DATABASE_URL"]

DEFAULT_PASSWORD = "tecnico123"
BCRYPT_ROUNDS = 12

# ─── Dados seed ──────────────────────────────────────────────────────────────
USERS_SEED = [
    {
        "login": "carlos.mendes",
        "name": "Carlos Mendes",
        "email": "carlos.mendes@manutech.com",
        "role": "supervisor",
    },
    {
        "login": "joao.silva",
        "name": "João Silva",
        "email": "joao.silva@manutech.com",
        "role": "technician",
    },
    {
        "login": "marcos.pereira",
        "name": "Marcos Pereira",
        "email": "marcos.pereira@manutech.com",
        "role": "technician",
    },
    {
        "login": "ana.costa",
        "name": "Ana Costa",
        "email": "ana.costa@manutech.com",
        "role": "attendant",
    },
]

ASSETS_SEED = [
    {
        "name": "Compressor Atlas Copco GA30",
        "model": "GA30",
        "manufacturer": "Atlas Copco",
        "serial_number": "AC-GA30-2024-0184",
        "location": "Galpão A — Linha 1, São Paulo/SP",
    },
    {
        "name": "Bomba Grundfos CR5-12",
        "model": "CR5-12",
        "manufacturer": "Grundfos",
        "serial_number": "GF-CR5-2023-0912",
        "location": "Setor de utilidades, Sorocaba/SP",
    },
    {
        "name": "Torno CNC Mazak QT-200",
        "model": "QT-200",
        "manufacturer": "Mazak",
        "serial_number": "MZ-QT200-2022-0045",
        "location": "Galpão B — Usinagem, Jundiaí/SP",
    },
    {
        "name": "Serra Fita Bosch GCO 14-24",
        "model": "GCO 14-24",
        "manufacturer": "Bosch",
        "serial_number": "BS-GCO14-2024-0023",
        "location": "Galpão A — Serralheria, Barueri/SP",
    },
    {
        "name": "Soldadora Inversora ESAB Rogue 200",
        "model": "Rogue 200",
        "manufacturer": "ESAB",
        "serial_number": "ES-RG200-2024-0156",
        "location": "Galpão A — Solda, Guarulhos/SP",
    },
    {
        "name": "Empilhadeira Hyster H50XT",
        "model": "H50XT",
        "manufacturer": "Hyster",
        "serial_number": "HS-H50XT-2023-0301",
        "location": "Pátio externo, Cajamar/SP",
    },
    {
        "name": "Caldeira Cleaver-Brooks CB-100",
        "model": "CB-100",
        "manufacturer": "Cleaver-Brooks",
        "serial_number": "CB-CB100-2021-0089",
        "location": "Casa de força, Osasco/SP",
    },
    {
        "name": "Forno Industrial Bertello B120",
        "model": "B120",
        "manufacturer": "Bertello",
        "serial_number": "BE-B120-2023-0078",
        "location": "Galpão C — Fundição, Cotia/SP",
    },
]

MATERIALS_SEED = [
    # (name, sku, unit_price, initial_in, min_quantity)
    ("Óleo Lubrificante ISO 68 (20L)", "OIL-ISO68-20L", 189.90, 25, 8),
    ("Filtro de Ar Mann C25 114",      "FLT-MN-C25114",  87.50, 12, 6),
    ("Filtro de Óleo Fram PH8A",       "FLT-FR-PH8A",    42.00, 12, 8),
    ("Correia em V A-42",              "BLT-VA-42",      31.75, 18, 10),
    ("Rolamento SKF 6205-2RS",         "BRG-SKF-6205",   67.90, 22, 12),
    ("Graxa Lithium MP-3 (1kg)",       "GRS-LI-MP3-1KG", 54.30, 9,  5),
    ("Disco de Corte 7\" Norton",      "DSC-NR-7IN",     14.80, 45, 20),
    ("Eletrodo E6013 2,5mm (1kg)",     "WLD-E6013-25",   38.50, 14, 10),
    ("Mangueira Hidráulica 1/2\"",     "HOS-HY-12IN",    89.00, 6,  4),
    ("Aditivo Radiador Mobil (1L)",    "ADT-MOB-1L",     72.40, 11, 6),
]

# (material_sku, order_number (FK to service_orders.order_number) ou None, qty, notes)
STOCK_OUTS = [
    # OS #1 — Compressor (já concluída)
    ("OIL-ISO68-20L",   1, 2, "OS-001 — Troca de óleo do compressor"),
    ("FLT-MN-C25114",   1, 1, "OS-001 — Substituição do filtro de ar"),
    # OS #2 — Bomba (já concluída)
    ("OIL-ISO68-20L",   2, 1, "OS-002 — Troca de óleo da bomba"),
    ("FLT-FR-PH8A",     2, 1, "OS-002 — Substituição do filtro de óleo"),
    ("BLT-VA-42",       2, 2, "OS-002 — Troca de correias"),
    # OS #3 — Empilhadeira (em andamento)
    ("HOS-HY-12IN",     3, 1, "OS-003 — Reparo do sistema hidráulico"),
    ("GRS-LI-MP3-1KG",  3, 1, "OS-003 — Lubrificação geral"),
    # OS #4 — Torno CNC (em andamento)
    ("BRG-SKF-6205",    4, 1, "OS-004 — Troca de rolamento do eixo"),
    # Consumo interno (sem OS)
    ("FLT-FR-PH8A",  None, 7, "Consumo interno — manutenção preventiva"),
    ("GRS-LI-MP3-1KG", None, 2, "Consumo interno — lubrificação de rotina"),
    ("DSC-NR-7IN",   None, 5, "Consumo interno — serralheria"),
    ("WLD-E6013-25", None, 2, "Consumo interno — solda"),
    ("HOS-HY-12IN",  None, 1, "Consumo interno — teste de bancada"),
    ("ADT-MOB-1L",   None, 1, "Consumo interno — reposição radiador"),
    ("BLT-VA-42",    None, 1, "Consumo interno — corretivo"),
]

SERVICE_ORDERS_SEED = [
    # (client, location, description, status, priority, start_date, asset_serial)
    (
        "Metalúrgica São José",
        "Av. Industrial, 1500 — São Paulo/SP",
        "Manutenção corretiva do compressor: vazamento de óleo e ruído anormal no cabeçote.",
        "completed", "high", date(2026, 4, 12), "AC-GA30-2024-0184",
    ),
    (
        "Indústria Brasileira de Plásticos",
        "Rua das Indústrias, 200 — Sorocaba/SP",
        "Troca programada de filtros, óleo e correias da bomba de transferência.",
        "completed", "medium", date(2026, 5, 3), "GF-CR5-2023-0912",
    ),
    (
        "Metalúrgica São José",
        "Av. Industrial, 1500 — São Paulo/SP",
        "Reparo no sistema hidráulico da empilhadeira: vazamento na mangueira principal.",
        "in_progress", "high", date(2026, 5, 20), "HS-H50XT-2023-0301",
    ),
    (
        "Plásticos do Brasil Ltda",
        "Rod. Anhanguera, km 42 — Jundiaí/SP",
        "Calibração do CNC após troca de spindle e ajuste de backlash.",
        "in_progress", "medium", date(2026, 5, 28), "MZ-QT200-2022-0045",
    ),
    (
        "Siderúrgica ABC",
        "Av. do Aço, 800 — Osasco/SP",
        "Manutenção preventiva da caldeira: limpeza de tubos e teste de segurança.",
        "open", "urgent", date(2026, 6, 5), "CB-CB100-2021-0089",
    ),
    (
        "Logística Express SP",
        "R. Carga Pesada, 320 — Guarulhos/SP",
        "Reparo na soldadora inversora que não está acendendo arco. Cliente cancelou antes do atendimento.",
        "cancelled", "low", date(2026, 5, 15), "ES-RG200-2024-0156",
    ),
]

# (order_number, technician_login)
ORDER_ASSIGNMENTS_SEED = [
    (1, "marcos.pereira"),
    (2, "joao.silva"),
    (3, "marcos.pereira"),
    (4, "joao.silva"),
]

# (order_number, description, amount, cost_type)
SERVICE_COSTS_SEED = [
    # OS #1 — total: 1240,50
    (1, "Óleo Lubrificante ISO 68 (2× R$ 189,90)", 379.80, "material"),
    (1, "Filtro de Ar Mann C25 114",                87.50,  "material"),
    (1, "Mão de obra — 4h técnicas",                320.00, "labor"),
    (1, "Alinhamento de eixo e balanceamento",      453.20, "service"),
    # OS #2 — total: 678,00
    (2, "Óleo Lubrificante ISO 68 (1× R$ 189,90)", 189.90, "material"),
    (2, "Filtro de Óleo Fram PH8A",                 42.00,  "material"),
    (2, "Correias em V (2× R$ 31,75)",              63.50,  "material"),
    (2, "Mão de obra — 2h técnicas",                160.00, "labor"),
    (2, "Teste de pressão e estanqueidade",         222.60, "service"),
    # OS #3 — total: 845,00 (em andamento)
    (3, "Mangueira Hidráulica 1/2\"",               89.00,  "material"),
    (3, "Graxa Lithium MP-3",                       54.30,  "material"),
    (3, "Mão de obra — 3h técnicas",                240.00, "labor"),
    (3, "Sangria do sistema e teste de carga",      461.70, "service"),
    # OS #4 — total: 510,00 (em andamento)
    (4, "Rolamento SKF 6205-2RS",                   67.90,  "material"),
    (4, "Mão de obra — 4h técnicas (calibração)",   320.00, "labor"),
    (4, "Calibração CNC com paquímetro digital",    122.10, "service"),
    # OS #6 — cancelada (taxa de visita)
    (6, "Taxa de visita técnica",                   80.00,  "other"),
]

# (client, description, status, valid_until, order_number_or_none, items)
BUDGETS_SEED = [
    (
        "Siderúrgica ABC",
        "Proposta de manutenção preditiva anual da caldeira CB-100.",
        "draft",
        date(2026, 7, 15),
        None,
        [
            ("Troca completa de tubos da caldeira", 2, 1250.00),
            ("Teste hidrostático",                   1, 450.00),
            ("Limpeza química dos tubos",            1, 680.00),
        ],
    ),
    (
        "Metalúrgica São José",
        "Contrato anual de manutenção preventiva do compressor GA30.",
        "sent",
        date(2026, 6, 20),
        1,
        [
            ("Manutenção mensal preventiva (12 meses)", 12, 850.00),
            ("Visita técnica extra sob demanda",         2, 180.00),
        ],
    ),
    (
        "Logística Express SP",
        "Reparo completo da soldadora inversora ESAB Rogue 200.",
        "approved",
        date(2026, 8, 30),
        6,
        [
            ("Reparo completo da placa inversora",   1, 1850.00),
            ("Substituição de cabos e garras",       3, 95.00),
            ("Teste de soldagem e amperagem",        1, 120.00),
        ],
    ),
]

# (user_login, type, title, message, related_id, days_ago)
NOTIFICATIONS_SEED = [
    ("joao.silva",     "order_assigned",      "Nova OS atribuída",
        "Você foi designado para a OS #004. Prazo: 7 dias.", 4, 0),
    ("marcos.pereira", "order_assigned",      "Nova OS atribuída",
        "Você foi designado para a OS #003. Prioridade alta.", 3, 0),
    ("marcos.pereira", "order_status_changed", "OS em andamento",
        "Você iniciou a execução da OS #003. Não esqueça de solicitar a conclusão ao final.", 3, 1),
    ("carlos.mendes",  "low_stock",            "Estoque baixo",
        "Material 'Filtro de Óleo Fram PH8A' abaixo do mínimo (4 un / mínimo 8 un).", 3, 0),
    ("carlos.mendes",  "budget_sent",          "Orçamento enviado",
        "Orçamento #002 enviado para Metalúrgica São José. Aguardando retorno.", 2, 0),
]


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode()


async def already_seeded(conn) -> bool:
    result = await conn.execute(
        text("SELECT 1 FROM users WHERE login = :login"),
        {"login": "joao.silva"},
    )
    return result.fetchone() is not None


async def main():
    engine = create_async_engine(DATABASE_URL)

    async with engine.begin() as conn:
        if await already_seeded(conn):
            print("=" * 60)
            print("Seed já aplicado (joao.silva já existe). Nada a fazer.")
            print("Para semear do zero, derrube o volume do banco:")
            print("  docker compose down -v")
            print("=" * 60)
            await engine.dispose()
            return

        print("Iniciando seed de dados demo...")
        password_hash = hash_password(DEFAULT_PASSWORD)

        # ── 1) Usuários ──────────────────────────────────────────────────────
        user_ids: dict[str, int] = {}
        for u in USERS_SEED:
            res = await conn.execute(
                text(
                    """
                    INSERT INTO users (login, name, email, password_hash, role, status)
                    VALUES (:login, :name, :email, :hash, :role, 'active')
                    RETURNING id
                    """
                ),
                {**u, "hash": password_hash},
            )
            user_ids[u["login"]] = res.scalar_one()
        print(f"  [OK] {len(USERS_SEED)} usuários criados")

        # ── 2) Equipamentos ──────────────────────────────────────────────────
        asset_ids: dict[str, int] = {}
        for a in ASSETS_SEED:
            res = await conn.execute(
                text(
                    """
                    INSERT INTO assets (name, model, manufacturer, serial_number, location, status)
                    VALUES (:name, :model, :manufacturer, :serial_number, :location, 'active')
                    RETURNING id
                    """
                ),
                a,
            )
            asset_ids[a["serial_number"]] = res.scalar_one()
        print(f"  [OK] {len(ASSETS_SEED)} equipamentos criados")

        # ── 3) Materiais ─────────────────────────────────────────────────────
        material_ids: dict[str, int] = {}
        material_data: dict[str, dict] = {}
        for name, sku, unit_price, initial_in, min_qty in MATERIALS_SEED:
            res = await conn.execute(
                text(
                    """
                    INSERT INTO materials (name, sku, unit_price, quantity_in_stock, min_quantity, status)
                    VALUES (:name, :sku, :unit_price, 0, :min_quantity, 'active')
                    RETURNING id
                    """
                ),
                {"name": name, "sku": sku, "unit_price": unit_price, "min_quantity": min_qty},
            )
            material_ids[sku] = res.scalar_one()
            material_data[sku] = {
                "initial_in": initial_in,
                "name": name,
                "min": min_qty,
            }
        print(f"  [OK] {len(MATERIALS_SEED)} materiais criados")

        # ── 4) Ordens de serviço ─────────────────────────────────────────────
        order_ids: dict[int, int] = {}
        for i, (client, location, description, status, priority, start_date, serial) in enumerate(
            SERVICE_ORDERS_SEED, start=1
        ):
            res = await conn.execute(
                text(
                    """
                    INSERT INTO service_orders
                        (client_name, location, description, status, priority, start_date, asset_id, total_cost)
                    VALUES
                        (:client_name, :location, :description, CAST(:status AS order_status),
                         CAST(:priority AS order_priority), :start_date, :asset_id, 0)
                    RETURNING id, order_number
                    """
                ),
                {
                    "client_name": client,
                    "location": location,
                    "description": description,
                    "status": status,
                    "priority": priority,
                    "start_date": start_date,
                    "asset_id": asset_ids[serial],
                },
            )
            row = res.fetchone()
            order_ids[i] = row[0]
        print(f"  [OK] {len(SERVICE_ORDERS_SEED)} ordens de serviço criadas")

        # ── 5) Movimentações de estoque ──────────────────────────────────────
        # 5a) Entradas iniciais (inventário)
        for sku, mid in material_data.items():
            mat_id = material_ids[sku]
            await conn.execute(
                text(
                    """
                    INSERT INTO stock_movements (material_id, service_order_id, movement_type, quantity, notes)
                    VALUES (:material_id, NULL, 'in', :quantity, :notes)
                    """
                ),
                {
                    "material_id": mat_id,
                    "quantity": mid["initial_in"],
                    "notes": "Inventário inicial — carga de estoque do sistema",
                },
            )

        # 5b) Saídas (consumo por OS ou interno)
        for sku, order_num, qty, notes in STOCK_OUTS:
            await conn.execute(
                text(
                    """
                    INSERT INTO stock_movements (material_id, service_order_id, movement_type, quantity, notes)
                    VALUES (:material_id, :service_order_id, 'out', :quantity, :notes)
                    """
                ),
                {
                    "material_id": material_ids[sku],
                    "service_order_id": order_ids[order_num] if order_num else None,
                    "quantity": qty,
                    "notes": notes,
                },
            )
        print(f"  [OK] {len(material_data)} entradas + {len(STOCK_OUTS)} saídas de estoque")

        # ── 6) Atribuições de técnicos ───────────────────────────────────────
        for order_num, tech_login in ORDER_ASSIGNMENTS_SEED:
            await conn.execute(
                text(
                    """
                    INSERT INTO order_assignments (service_order_id, technician_id, active)
                    VALUES (:so_id, :tech_id, TRUE)
                    """
                ),
                {"so_id": order_ids[order_num], "tech_id": user_ids[tech_login]},
            )
        print(f"  [OK] {len(ORDER_ASSIGNMENTS_SEED)} atribuições de técnicos")

        # ── 7) Custos de serviço (trigger recalcula total_cost) ─────────────
        for order_num, desc, amount, ctype in SERVICE_COSTS_SEED:
            await conn.execute(
                text(
                    """
                    INSERT INTO service_costs (service_order_id, description, amount, cost_type)
                    VALUES (:so_id, :desc, :amount, CAST(:ctype AS cost_type))
                    """
                ),
                {
                    "so_id": order_ids[order_num],
                    "desc": desc,
                    "amount": amount,
                    "ctype": ctype,
                },
            )
        print(f"  [OK] {len(SERVICE_COSTS_SEED)} custos registrados (totais recalculados via trigger)")

        # ── 8) Orçamentos + itens (trigger recalcula total_amount) ──────────
        budget_count = 0
        budget_item_count = 0
        for client, desc, status, valid_until, order_num, items in BUDGETS_SEED:
            res = await conn.execute(
                text(
                    """
                    INSERT INTO budgets
                        (client_name, description, status, valid_until, service_order_id, created_by, total_amount)
                    VALUES
                        (:client_name, :description, CAST(:status AS budget_status), :valid_until,
                         :so_id, :created_by, 0)
                    RETURNING id
                    """
                ),
                {
                    "client_name": client,
                    "description": desc,
                    "status": status,
                    "valid_until": valid_until,
                    "so_id": order_ids[order_num] if order_num else None,
                    "created_by": user_ids["carlos.mendes"],
                },
            )
            budget_id = res.scalar_one()
            budget_count += 1
            for item_desc, qty, price in items:
                await conn.execute(
                    text(
                        """
                        INSERT INTO budget_items (budget_id, description, quantity, unit_price)
                        VALUES (:budget_id, :desc, :qty, :price)
                        """
                    ),
                    {
                        "budget_id": budget_id,
                        "desc": item_desc,
                        "qty": qty,
                        "price": price,
                    },
                )
                budget_item_count += 1
        print(f"  [OK] {budget_count} orçamentos com {budget_item_count} itens (totais recalculados via trigger)")

        # ── 9) Notificações ──────────────────────────────────────────────────
        for user_login, ntype, title, message, related_id, days_ago in NOTIFICATIONS_SEED:
            created_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
            await conn.execute(
                text(
                    """
                    INSERT INTO notifications (user_id, type, title, message, related_id, read, created_at)
                    VALUES (:user_id, :type, :title, :message, :related_id, FALSE, :created_at)
                    """
                ),
                {
                    "user_id": user_ids[user_login],
                    "type": ntype,
                    "title": title,
                    "message": message,
                    "related_id": related_id,
                    "created_at": created_at,
                },
            )
        print(f"  [OK] {len(NOTIFICATIONS_SEED)} notificações criadas")

    await engine.dispose()
    print()
    print("=" * 60)
    print("SEED CONCLUÍDO COM SUCESSO")
    print("=" * 60)
    print()
    print("Credenciais (todos com a mesma senha):")
    print(f"  Login:    carlos.mendes | joao.silva | marcos.pereira | ana.costa")
    print(f"  Senha:    {DEFAULT_PASSWORD}")
    print()
    print("  admin / admin123  (criado pelo seed_admin.py)")
    print()
    print("Resumo do ambiente:")
    print(f"  • {len(USERS_SEED)}    usuários (1 supervisor, 2 técnicos, 1 atendente)")
    print(f"  • {len(ASSETS_SEED)}    equipamentos cadastrados")
    print(f"  • {len(MATERIALS_SEED)}    materiais com movimentações (1 abaixo do mínimo)")
    print(f"  • {len(SERVICE_ORDERS_SEED)}    ordens de serviço (2 concluídas, 2 em andamento, 1 aberta, 1 cancelada)")
    print(f"  • {len(SERVICE_COSTS_SEED)}    lançamentos de custo (totais calculados via trigger)")
    print(f"  • {budget_count}    orçamentos com {budget_item_count} itens (totais calculados via trigger)")
    print(f"  • {len(NOTIFICATIONS_SEED)}    notificações para testar o sino")
    print()
    print("Acesse:  http://localhost   (frontend)")
    print()


if __name__ == "__main__":
    asyncio.run(main())
