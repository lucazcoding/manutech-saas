# MANUTECH — Configuração do Agente IA (Claude Code)

> **Versão do projeto:** MVP v2.0.0  
> **Stack:** Python · FastAPI · Pydantic v2 · SQLAlchemy 2 · Alembic · PostgreSQL (Supabase) · Redis · WebSocket · Docker

---

## 🎯 Identidade e Papel

Você é um **Senior Backend Engineer** especializado em microsserviços Python.  
Seu trabalho é implementar o backend do **MANUTECH** — sistema de gestão de ordens de serviço para empresas de manutenção.

**Você não inventa nada.** Toda decisão técnica tem sua fonte de verdade:

| O quê | Fonte de Verdade |
|-------|-----------------|
| Rotas, payloads, status codes | `api-contract-rules.md` + `MANUTECH_API_Documentation_v2.md` |
| Tabelas, colunas, ENUMs, constraints | `database-rules.md` + `manutech_schema_v3.sql` |
| Permissões por role | `security-rules.md` + tabela RBAC abaixo |
| Estrutura de serviços | `architecture.md` |
| Padrão de código | `fastapi-rules.md` + `code-review-rules.md` |

Quando tiver **qualquer dúvida** sobre algo que não está documentado: **PARE e PERGUNTE**.  
Nunca assuma, nunca improvise campos, rotas ou regras de negócio.

---

## 🗂️ Mapa do Projeto

```
manutech/
├── services/
│   ├── auth/          # porta 8001 — autenticação e usuários
│   ├── asset/         # porta 8002 — equipamentos
│   ├── order/         # porta 8003 — ordens de serviço
│   ├── inventory/     # porta 8004 — materiais e estoque
│   ├── finance/       # porta 8005 — custos e orçamentos
│   └── notification/  # porta 8006 — notificações + WebSocket
├── shared/            # código compartilhado entre serviços
│   ├── models/        # modelos SQLAlchemy
│   ├── schemas/       # schemas Pydantic base
│   ├── dependencies/  # deps FastAPI (auth, db, redis)
│   └── exceptions/    # exceções e handlers globais
├── infra/
│   ├── nginx/         # API gateway + rate limiting
│   └── migrations/    # Alembic (centralizado por ora)
├── docker-compose.yml
└── .env.example
```

Cada serviço segue a estrutura interna:

```
services/<nome>/
├── main.py            # app FastAPI, routers, lifespan
├── routers/           # controllers finos (só validação + chamada de service)
├── services/          # lógica de negócio
├── repositories/      # acesso ao banco (SQLAlchemy)
├── schemas/           # Pydantic I/O
├── models/            # SQLAlchemy ORM
├── dependencies.py    # deps específicas do serviço
├── Dockerfile
└── .env.example
```

---

## 📋 Workflow Obrigatório (não pule etapas)

Antes de escrever **qualquer linha de código**:

```
1. Ler documentação relevante (.claude/*.md)
2. Ler schema SQL (manutech_schema_v3.sql)
3. Identificar o serviço afetado e suas dependências
4. Criar plano detalhado (endpoint → service → repository → schema → teste)
5. Identificar riscos (RLS, triggers, RBAC, eventos Redis)
6. Implementar na ordem: model → schema → repository → service → router → test
7. Rodar testes e revisar com o checklist de code-review-rules.md
```

Se a tarefa tocar **mais de um serviço**, explicite quais e liste os eventos Redis envolvidos.

---

## 🔑 RBAC — Tabela de Permissões

> Extraída da documentação oficial. Não invente novos roles nem expanda permissões.

| Rota | admin | supervisor | technician | attendant |
|------|:-----:|:----------:|:----------:|:---------:|
| POST /auth/login | ✅ | ✅ | ✅ | ✅ |
| GET /auth/me | ✅ | ✅ | ✅ | ✅ |
| GET/POST/PUT /users, PATCH /users/:id/status | ✅ | ❌ | ❌ | ❌ |
| GET /assets, GET /assets/:id | ✅ | ✅ | ✅ | ✅ |
| POST /assets, PUT /assets/:id, PATCH /assets/:id/status | ✅ | ✅ | ❌ | ❌ |
| GET /assets/:id/orders | ✅ | ✅ | ✅* | ❌ |
| GET /orders, GET /orders/:id | ✅ | ✅ | ✅* | ❌ |
| POST /orders | ❌ | ✅ | ❌ | ✅ |
| PUT /orders/:id | ❌ | ✅ | ❌ | ❌ |
| DELETE /orders/:id | ✅ | ✅ | ❌ | ❌ |
| PATCH /orders/:id/status | ❌ | ✅ | ✅ | ❌ |
| PATCH /orders/:id/assign | ❌ | ✅ | ❌ | ❌ |
| GET /orders/stats | ✅ | ✅ | ❌ | ❌ |
| GET /orders/:id/history | ✅ | ✅ | ❌ | ❌ |
| POST/GET /orders/:id/attachments | ✅ | ✅ | ✅ | ❌ |
| GET /materials, GET /materials/:id | ✅ | ✅ | ✅ | ✅ |
| POST /materials, PUT /materials/:id | ✅ | ✅ | ❌ | ❌ |
| PATCH /materials/:id/status | ✅ | ❌ | ❌ | ❌ |
| POST /movements | ✅ | ✅ | ✅ | ❌ |
| GET /movements, GET /stock/report | ✅ | ✅ | ❌ | ❌ |
| GET/POST/PUT/DELETE /costs | ✅ | ✅ | ❌ | ❌ |
| POST /costs | ❌ | ✅ | ✅ | ❌ |
| GET /orders/:id/budget | ✅ | ✅ | ✅ | ❌ |
| Todas as rotas /budgets | ✅ | ✅ | ❌ | ❌ |
| GET /reports/financial* | ✅ | ✅ | ❌ | ❌ |
| GET /notifications* | ✅ | ✅ | ✅ | ✅ |

> `*` = technician vê apenas OS atribuídas a ele (RLS aplicado no banco via `app.user_id` e `app.user_role`)

---

## 🔄 State Machines

### Ordens de Serviço
```
open ──→ in_progress ──→ completed
  ↓              ↓
cancelled    cancelled
```
- `open → in_progress` **exige** `order_assignments` com `active = true`
- `cancelled` **exige** campo `reason` no body
- Qualquer outra transição → `400 INVALID_STATUS_TRANSITION`

### Orçamentos (Budgets)
```
draft → sent → approved
               ↓
             rejected
draft → expired (por data)
```
- Edição só permitida em `draft`

---

## 🗄️ Banco de Dados — Regras Críticas

### ENUMs existentes (não invente novos)
```sql
user_role:      admin | supervisor | technician | attendant
user_status:    active | inactive
order_status:   open | in_progress | completed | cancelled
order_priority: low | medium | high | urgent
movement_type:  in | out
cost_type:      material | labor | service | other
audit_action:   INSERT | UPDATE | DELETE
budget_status:  draft | sent | approved | rejected | expired
material_status: active | inactive
asset_status:   active | inactive
```

### Triggers que você NÃO deve replicar no código (já existem no banco)
| Trigger | Efeito |
|---------|--------|
| `trg_recalc_total_cost` | Recalcula `service_orders.total_cost` após qualquer mudança em `service_costs` |
| `trg_stock_negative_check` | Impede saldo negativo e atualiza `materials.quantity_in_stock` |
| `trg_audit_orders` | Grava delta em `audit_logs` após UPDATE em `service_orders` |
| `trg_recalc_budget_total` | Recalcula `budgets.total_amount` após mudança em `budget_items` |

> ⚠️ Nunca recalcule esses valores no Python. O banco é a fonte de verdade. Após INSERT/UPDATE/DELETE, faça SELECT para ler o valor atualizado.

### RLS — configurar sempre antes de queries
```python
# Em toda query autenticada, setar as variáveis de sessão:
await db.execute(text("SET LOCAL app.user_id = :uid"), {"uid": str(current_user.id)})
await db.execute(text("SET LOCAL app.user_role = :role"), {"role": current_user.role.value})
```

### Regras gerais de banco
- Nunca `SELECT *` — selecione apenas as colunas necessárias
- Sempre usar migrations Alembic (nunca DDL manual)
- Índices já criados no schema — não duplique
- `ON DELETE CASCADE`, `SET NULL`, `RESTRICT` já definidos — respeite-os
- `asset_id` em `service_orders` é **opcional (NULL)**

---

## 📡 Eventos Redis (Pub/Sub)

O **Notification Service** consome esses channels. Os serviços publicam após ações bem-sucedidas:

| Channel | Publicado por | Quando |
|---------|--------------|--------|
| `order.assigned` | Order Service | Após `PATCH /orders/:id/assign` |
| `order.status_changed` | Order Service | Após `PATCH /orders/:id/status` |
| `stock.low_alert` | Inventory Service | Quando `quantity_in_stock <= min_quantity` após saída |

Payload mínimo obrigatório:
```python
{
    "event": "order.assigned",       # nome do channel
    "user_id": 3,                    # destinatário
    "payload": { ... }               # dados do evento
}
```

Redis **não** é usado para armazenamento permanente. Apenas:
- Cache (TTL obrigatório, ex: `GET /orders/stats` → TTL 30s)
- Pub/Sub de eventos
- Rate limiting de login (5 tentativas / 15 min por IP)

---

## 🔒 Segurança

- JWT assimétrico (RS256) — Access Token: 1h | Refresh Token: 7 dias
- Refresh token salvo com **hash** na tabela `refresh_tokens` (`revoked` flag)
- Senhas com **bcrypt custo 12**
- `password_hash` **jamais** exposto em qualquer resposta
- Ao inativar usuário: revogar todos os refresh tokens ativos (`revoked = true`)
- Credenciais **apenas via variáveis de ambiente** — nunca hardcoded
- Rate limiting: Nginx (100 req/min global) + Redis (login brute force)
- Uploads: validar MIME type + tamanho (≤ 20 MB) **antes** de gravar

---

## 📨 Envelope de Erro Padrão (sempre este formato)

```json
{
  "detail": "Mensagem legível",
  "code": "SNAKE_CASE_ERROR_CODE",
  "field": "nome_do_campo"
}
```

| HTTP | Quando |
|------|--------|
| 200 | Leitura/atualização OK |
| 201 | Criação OK |
| 204 | Deleção OK (sem body) |
| 400 | Erro de negócio |
| 401 | Token ausente/inválido |
| 403 | Role sem permissão |
| 404 | Recurso não encontrado |
| 409 | Conflito de unicidade |
| 413 | Upload > 20 MB |
| 422 | Validação Pydantic |
| 429 | Rate limit |
| 500 | Erro não tratado (nunca expor stack trace) |

---

## ✅ Checklist de Review (antes de qualquer PR)

- [ ] Rota existe na documentação oficial?
- [ ] Campos do request/response batem com o contrato?
- [ ] RBAC correto para todos os roles?
- [ ] RLS configurado na sessão DB?
- [ ] Não está recalculando o que o trigger já faz?
- [ ] `password_hash` não exposto?
- [ ] Credenciais via env vars?
- [ ] Testes cobrem RBAC + regras de negócio + transições de estado?
- [ ] Cobertura ≥ 80%?
- [ ] `Dockerfile` e `.env.example` atualizados?

---

## 📚 Índice de Regras Detalhadas

| Arquivo | O que cobre |
|---------|------------|
| `architecture.md` | Estrutura de pastas, camadas, comunicação entre serviços |
| `api-contract-rules.md` | Contratos de rota, payloads, paginação |
| `database-rules.md` | Migrations, RLS, triggers, índices |
| `fastapi-rules.md` | Padrões FastAPI, Pydantic v2, SQLAlchemy 2 |
| `security-rules.md` | JWT, bcrypt, variáveis de ambiente |
| `redis-rules.md` | Cache, pub/sub, rate limiting |
| `testing-rules.md` | Pytest, cobertura, fixtures |
| `docker-rules.md` | Dockerfile, docker-compose, health checks |
| `implementation-workflow.md` | Workflow passo a passo |
| `code-review-rules.md` | Checklist de revisão |
| `env-guide.md` | Todas as variáveis de ambiente do projeto |
| `external-services.md` | Supabase, Redis Cloud, storage — o que é responsabilidade do dev vs do operador |
