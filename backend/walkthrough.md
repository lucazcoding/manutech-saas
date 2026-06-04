# Migração asyncpg → psycopg3 — Walkthrough

## Resumo

Migração completa do driver de banco de dados de `asyncpg` para `psycopg3` em **todos** os arquivos do projeto MANUTECH. O grep final confirma **zero referências residuais** a `asyncpg` em código executável.

---

## Arquivos Modificados

### Infraestrutura

| Arquivo | Alteração |
|---------|-----------|
| [Dockerfile](file:///c:/Users/vinyc/manutech-saas/backend/infra/migrations/Dockerfile) | `pip install asyncpg` → `pip install "psycopg[binary]"` |

### Configuração Raiz

| Arquivo | Alteração |
|---------|-----------|
| [.env](file:///c:/Users/vinyc/manutech-saas/backend/.env) | Comentário corrigido: "asyncpg direto" → "psycopg3 direto" |
| [.env.example](file:///c:/Users/vinyc/manutech-saas/backend/.env.example) | `DATABASE_URL` dialect: `asyncpg` → `psycopg` |
| [sync_envs.py](file:///c:/Users/vinyc/manutech-saas/backend/sync_envs.py) | 2 referências de `postgresql+asyncpg` → `postgresql+psycopg` |

### Serviços (`.env` e `.env.example` de cada um)

| Serviço | Arquivos |
|---------|----------|
| **auth** | [.env](file:///c:/Users/vinyc/manutech-saas/backend/services/auth/.env), [.env.example](file:///c:/Users/vinyc/manutech-saas/backend/services/auth/.env.example) |
| **asset** | [.env](file:///c:/Users/vinyc/manutech-saas/backend/services/asset/.env), [.env.example](file:///c:/Users/vinyc/manutech-saas/backend/services/asset/.env.example) |
| **order** | [.env](file:///c:/Users/vinyc/manutech-saas/backend/services/order/.env), [.env.example](file:///c:/Users/vinyc/manutech-saas/backend/services/order/.env.example) |
| **inventory** | [.env](file:///c:/Users/vinyc/manutech-saas/backend/services/inventory/.env), [.env.example](file:///c:/Users/vinyc/manutech-saas/backend/services/inventory/.env.example) |
| **finance** | [.env](file:///c:/Users/vinyc/manutech-saas/backend/services/finance/.env), [.env.example](file:///c:/Users/vinyc/manutech-saas/backend/services/finance/.env.example) |
| **notification** | [.env](file:///c:/Users/vinyc/manutech-saas/backend/services/notification/.env), [.env.example](file:///c:/Users/vinyc/manutech-saas/backend/services/notification/.env.example) |

### Arquivos que NÃO precisaram de alteração

| Arquivo | Motivo |
|---------|--------|
| [alembic.ini](file:///c:/Users/vinyc/manutech-saas/backend/infra/migrations/alembic.ini) | Não contém `sqlalchemy.url` hardcoded — usa `env.py` |
| [env.py](file:///c:/Users/vinyc/manutech-saas/backend/infra/migrations/env.py) | Usa `create_async_engine(DATABASE_URL)` — psycopg3 suporta async nativamente com `postgresql+psycopg://` |
| [session.py](file:///c:/Users/vinyc/manutech-saas/backend/shared/shared/db/session.py) | Já ajustado em etapa anterior com `connect_args` do psycopg3 |
| [requirements.txt](file:///c:/Users/vinyc/manutech-saas/backend/requirements.txt) | Já contém `psycopg[binary,pool,async]>=3.2.0` |
| [docker-compose.yml](file:///c:/Users/vinyc/manutech-saas/backend/docker-compose.yml) | Porta `5433:5432` já configurada |
| [README.md](file:///c:/Users/vinyc/manutech-saas/backend/README.md) | Apenas documentação, referências ao asyncpg são históricas |

---

## Validação

```
grep -r "asyncpg" --include="*.py" --include="*.txt" --include="*.yml" --include="*.ini" --include="Dockerfile" .
# → Resultado: 0 matches ✅

grep -r "asyncpg" --include="*.env" --include="*.env.example" .
# → Resultado: 0 matches ✅
```

---

## Comandos para Rebuild

### 1. Parar e limpar tudo (remover containers, volumes e imagens)

```powershell
docker-compose down -v --rmi all
```

### 2. Rebuild limpo com force-recreate

```powershell
docker-compose up --build --force-recreate -d
```

### 3. Verificar que todos os containers subiram

```powershell
docker-compose ps
```

> Espere que `migrations` apareça com status `exited (0)` (execução bem-sucedida do `alembic upgrade head`) e os 6 serviços + nginx + db + redis estejam `Up (healthy)`.

### 4. Verificar logs das migrations (em caso de erro)

```powershell
docker-compose logs migrations
```

---

## Acesso ao Frontend

| URL | O que testa |
|-----|-------------|
| `http://localhost` | SPA carrega via Nginx (arquivo `tests/frontend/index.html`) |
| `http://localhost/health` | Health check global do Nginx → `{"status":"ok"}` |
| `http://localhost/api/v1/auth/login` | Proxy → Auth Service (porta 8001) |
| `http://localhost/api/v1/assets` | Proxy → Asset Service (porta 8002) |
| `http://localhost/api/v1/orders` | Proxy → Order Service (porta 8003) |
| `http://localhost/api/v1/materials` | Proxy → Inventory Service (porta 8004) |
| `http://localhost/api/v1/costs` | Proxy → Finance Service (porta 8005) |
| `http://localhost/api/v1/notifications` | Proxy → Notification Service (porta 8006) |

> [!IMPORTANT]
> O PostgreSQL local do host ocupa a porta 5432. O container `db` está mapeado em `5433:5432`, portanto ferramentas como DBeaver/pgAdmin devem se conectar via `localhost:5433`.
