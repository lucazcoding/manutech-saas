# Arquitetura — MANUTECH

## Visão Geral

O MANUTECH é uma API de microsserviços. Cada serviço é um processo FastAPI independente, com seu próprio processo uvicorn, rodando em porta dedicada. Eles compartilham o **mesmo banco PostgreSQL** (schemas isolados por prefixo de tabela não são necessários no MVP — as tabelas são compartilhadas via mesmo banco), mas têm acesso ao banco via connection pool próprio.

A comunicação entre serviços é **assíncrona via Redis Pub/Sub** — nunca chamadas HTTP diretas entre serviços no MVP.

---

## Serviços e Portas

| Serviço | Porta | Responsabilidade |
|---------|-------|-----------------|
| Auth Service | 8001 | Autenticação, tokens, gestão de usuários |
| Asset Service | 8002 | Cadastro e gestão de equipamentos |
| Order Service | 8003 | Ordens de serviço, atribuições, anexos |
| Inventory Service | 8004 | Materiais, movimentações de estoque |
| Finance Service | 8005 | Custos, orçamentos, relatórios financeiros |
| Notification Service | 8006 | Notificações push (REST + WebSocket) |

O **Nginx** (porta 80/443) atua como API Gateway, fazendo proxy reverso para cada serviço com base no path prefix e aplicando rate limiting global.

---

## Camadas por Serviço (Clean Architecture)

```
Router (Controller)
    │  Validação de input via Pydantic
    │  Verificação de RBAC (dependency)
    ▼
Service (Caso de Uso)
    │  Lógica de negócio pura
    │  Orquestra repositórios
    │  Publica eventos Redis quando necessário
    ▼
Repository (Acesso a Dados)
    │  SQLAlchemy 2 (async)
    │  Queries explícitas (sem SELECT *)
    │  Configura RLS na sessão antes de qualquer query
    ▼
Database (PostgreSQL via Supabase)
    │  Triggers executam recálculos automáticos
    │  RLS aplica restrições por usuário/role
```

### Regras de camada (invioláveis)

- **Router** não acessa banco diretamente. Nunca.
- **Router** não contém lógica de negócio. Nunca.
- **Service** não conhece FastAPI (sem `Request`, sem `Response`). Recebe tipos Python puros.
- **Repository** não conhece regras de negócio. Só lê e escreve dados.
- **Service** pode chamar múltiplos repositories.
- **Service** pode publicar eventos Redis.
- **Service** nunca chama outro Service de outro microsserviço via HTTP.

---

## Shared — Código Compartilhado

O diretório `shared/` contém código reutilizável entre serviços. Deve ser instalado como pacote local (`pip install -e ./shared`).

```
shared/
├── auth/
│   ├── jwt.py          # decode/verify JWT, extrair claims
│   └── dependencies.py # get_current_user, require_roles
├── db/
│   ├── session.py      # engine async, get_db dependency
│   └── rls.py          # set_rls_context(db, user_id, role)
├── redis/
│   └── client.py       # get_redis, publish_event
├── schemas/
│   ├── pagination.py   # PaginatedResponse[T]
│   └── errors.py       # ErrorResponse, error codes
└── exceptions/
    └── handlers.py     # exception_handler global FastAPI
```

---

## Padrão de Injeção de Dependência

```python
# Em cada router, as dependências chegam via Depends():
@router.get("/orders")
async def list_orders(
    filters: OrderFilters = Depends(),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: UserClaims = Depends(get_current_user),
    _: None = Depends(require_roles(["admin", "supervisor", "technician"])),
):
    return await OrderService(db, redis).list_orders(filters, current_user)
```

---

## Comunicação entre Serviços

### Redis Pub/Sub (único meio de comunicação entre serviços no MVP)

Produtores:
- `Order Service` publica em `order.assigned` e `order.status_changed`
- `Inventory Service` publica em `stock.low_alert`

Consumidor:
- `Notification Service` subscreve todos os channels, persiste notificação no banco e faz fan-out via WebSocket

### WebSocket
- Apenas o `Notification Service` expõe WebSocket
- Autenticação via query param `?token=<JWT>`
- Conexão recusada com código `4001` se JWT inválido

---

## Nginx — API Gateway

O Nginx não conhece a lógica de negócio. Apenas:
- Proxy reverso por path prefix (`/api/v1/auth` → `auth:8001`, etc.)
- Rate limiting global: 100 req/min por IP
- Headers de segurança (HSTS, X-Frame-Options, etc.)
- Terminação TLS (em produção)

---

## Princípios SOLID aplicados

| Princípio | Como aplicamos |
|-----------|---------------|
| **S** — Single Responsibility | Router = I/O, Service = negócio, Repository = dados |
| **O** — Open/Closed | Novos filtros via herança de schema, não modificando service existente |
| **L** — Liskov | Repositories implementam interface/protocolo base |
| **I** — Interface Segregation | Dependencies FastAPI granulares (require_roles, get_db, get_redis separados) |
| **D** — Dependency Inversion | Services recebem repositórios por injeção, nunca instanciam |
