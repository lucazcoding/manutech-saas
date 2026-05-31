# Banco de Dados — Regras

## Provedor

PostgreSQL hospedado no **Supabase** (produção e staging).  
PostgreSQL local via Docker para desenvolvimento.

O código deve ser **agnóstico de provedor** — usar SQLAlchemy 2 async com driver `asyncpg`.  
Nunca usar APIs específicas do Supabase SDK no backend Python (o Supabase é acessado apenas via connection string PostgreSQL padrão).

---

## Connection String

```python
# Formato esperado nas env vars:
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname
```

A connection string **nunca** é hardcoded. Sempre via variável de ambiente.

---

## Migrations — Alembic

- **Todo** DDL é feito via migration Alembic. Nunca executar DDL manualmente no banco.
- Migrations ficam em `infra/migrations/` (centralizado, pois o banco é compartilhado).
- Nomes de migration: `{revision_id}_descricao_da_mudanca.py`
- Cada migration deve ser reversível (`downgrade` implementado).

```bash
# Criar nova migration:
alembic revision --autogenerate -m "add_asset_id_to_service_orders"

# Aplicar:
alembic upgrade head

# Reverter:
alembic downgrade -1
```

### Migrations pendentes identificadas (schema v3)

Antes de implementar o Asset Service, criar migrations para:

1. `CREATE TYPE asset_status AS ENUM ('active', 'inactive')`
2. `CREATE TABLE assets (...)` — conforme schema v3
3. `ALTER TABLE service_orders ADD COLUMN asset_id BIGINT REFERENCES assets(id) ON DELETE SET NULL`
4. `CREATE INDEX idx_orders_asset ON service_orders (asset_id)`
5. `CREATE INDEX idx_assets_status ON assets (status)`
6. `CREATE POLICY p_assets_all_read ON assets FOR SELECT USING (TRUE)`

---

## Row Level Security (RLS)

O RLS é aplicado no banco para garantir isolamento de dados por usuário/role.

### Como configurar antes de qualquer query

```python
# shared/db/rls.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

async def set_rls_context(db: AsyncSession, user_id: int, role: str) -> None:
    """Configura variáveis de sessão para o RLS do PostgreSQL."""
    await db.execute(text("SET LOCAL app.user_id = :uid"), {"uid": str(user_id)})
    await db.execute(text("SET LOCAL app.user_role = :role"), {"role": role})
```

**Chamar `set_rls_context` é obrigatório no início de cada request autenticado.**

### Políticas RLS ativas (do schema v3)

| Tabela | Política | Efeito |
|--------|----------|--------|
| `service_orders` | `p_orders_technician_select` | Technician vê apenas OS com atribuição ativa para ele |
| `refresh_tokens` | `p_refresh_owner` | Usuário acessa apenas seus próprios tokens |
| `notifications` | `p_notifications_owner` | Usuário acessa apenas suas próprias notificações |
| `assets` | `p_assets_all_read` | Qualquer usuário autenticado lê — escrita via RBAC na API |

---

## Triggers — Não replicar no Python

Os triggers abaixo já existem no banco. O código Python **não deve** recalcular seus efeitos:

| Trigger | Tabela observada | Efeito automático |
|---------|-----------------|-------------------|
| `trg_recalc_total_cost` | `service_costs` (INSERT/UPDATE/DELETE) | Atualiza `service_orders.total_cost` |
| `trg_stock_negative_check` | `stock_movements` (INSERT) | Impede saldo negativo, atualiza `materials.quantity_in_stock` |
| `trg_audit_orders` | `service_orders` (UPDATE) | Grava delta em `audit_logs` com `app.user_id` |
| `trg_recalc_budget_total` | `budget_items` (INSERT/UPDATE/DELETE) | Atualiza `budgets.total_amount` |

> ⚠️ Após operações que disparam triggers, sempre fazer `RETURNING id` e depois um `SELECT` separado para ler os valores atualizados (ex: `total_cost` após inserir custo).

### Auditoria automática via trigger

O `trg_audit_orders` lê `current_setting('app.user_id')` para identificar quem fez a mudança.  
Por isso, `set_rls_context` deve ser chamado **antes** de qualquer UPDATE em `service_orders`.

---

## Queries — Boas Práticas

### Nunca `SELECT *`

```python
# ❌ Errado
result = await db.execute(select(ServiceOrder))

# ✅ Correto
result = await db.execute(
    select(
        ServiceOrder.id,
        ServiceOrder.order_number,
        ServiceOrder.client_name,
        ServiceOrder.status,
        ServiceOrder.priority,
        ServiceOrder.total_cost,
    )
)
```

### Usar índices existentes

Os índices do schema foram criados para queries específicas — respeite-os:

| Índice | Usado em |
|--------|----------|
| `idx_orders_status_priority` | `GET /orders?status=&priority=` |
| `idx_orders_asset` | `GET /orders?asset_id=` e `GET /assets/:id/orders` |
| `idx_movements_mat_date` | `GET /movements?material_id=&created_at_from=` |
| `idx_assignments_technician` | `GET /orders?technician_id=` |
| `idx_costs_order` | `GET /costs?service_order_id=` |
| `idx_audit_table_record` | `GET /orders/:id/history` |
| `idx_notifications_user_read` | `GET /notifications?read=false` |

### Paginação eficiente

```python
# Usar LIMIT/OFFSET com COUNT separado para paginação
from sqlalchemy import func, select

async def paginate(query, count_query, page: int, page_size: int, db: AsyncSession):
    total = await db.scalar(count_query)
    items = await db.execute(
        query.limit(page_size).offset((page - 1) * page_size)
    )
    return {
        "items": items.all(),
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": ceil(total / page_size) if total > 0 else 0,
    }
```

### Soft delete — padrão do sistema

Nenhuma entidade tem exclusão física no MVP, exceto `notifications`.  
Soft delete é feito via coluna `status` (ex: `status = 'inactive'`).

| Tabela | Soft delete via |
|--------|----------------|
| `users` | `status = 'inactive'` |
| `assets` | `status = 'inactive'` |
| `materials` | `status = 'inactive'` |
| `service_orders` | `status = 'cancelled'` (via PATCH /status) |
| `notifications` | DELETE físico (exceção documentada) |

---

## Constraints — Respeitar sempre

```sql
-- Não ultrapassar no código:
chk_users_email_format    -- regex email
chk_users_login_len       -- login >= 3 chars
chk_orders_total_cost     -- total_cost >= 0
chk_movements_qty         -- quantity > 0
chk_costs_amount          -- amount >= 0
chk_attachment_size       -- 0 < size_bytes <= 52428800
chk_attachment_path       -- file_path sem ".."
chk_bitem_qty             -- quantity > 0
chk_bitem_price           -- unit_price >= 0
```

### Unique constraints

```sql
UNIQUE: users.login
UNIQUE: users.email
UNIQUE: assets.serial_number (nullable — só quando informado)
UNIQUE: materials.sku
UNIQUE: attachments.file_path
UNIQUE: service_orders.order_number (GENERATED ALWAYS AS IDENTITY)
UNIQUE: budgets.budget_number (GENERATED ALWAYS AS IDENTITY)
UNIQUE INDEX: refresh_tokens (user_id, token_hash) WHERE revoked = FALSE
UNIQUE INDEX: order_assignments (service_order_id, technician_id) WHERE active = TRUE
```
