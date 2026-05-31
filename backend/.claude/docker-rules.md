# Docker — Regras

## Obrigatório por Serviço

Cada serviço deve ter:
- `Dockerfile` — imagem de produção
- `.env.example` — todas as variáveis com valores de exemplo (sem segredos reais)
- Endpoint `GET /health` — para healthcheck do Docker

---

## Dockerfile Padrão

```dockerfile
# services/order/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar shared como pacote local
COPY shared/ /shared/
RUN pip install --no-cache-dir -e /shared/

# Copiar código do serviço
COPY services/order/ .

# Usuário não-root (segurança)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8003

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003", "--workers", "1"]
```

---

## docker-compose.yml Raiz

```yaml
# docker-compose.yml
version: "3.9"

services:
  # ─── Banco de Dados ───────────────────────────────────────
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./infra/db/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ─── Redis ────────────────────────────────────────────────
  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ─── Migrations ──────────────────────────────────────────
  migrations:
    build:
      context: .
      dockerfile: infra/migrations/Dockerfile
    environment:
      DATABASE_URL: ${DATABASE_URL}
    depends_on:
      db:
        condition: service_healthy
    command: alembic upgrade head

  # ─── Auth Service ─────────────────────────────────────────
  auth:
    build:
      context: .
      dockerfile: services/auth/Dockerfile
    env_file: services/auth/.env
    ports:
      - "8001:8001"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
      migrations:
        condition: service_completed_successfully
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 5s
      retries: 3

  # ─── Asset Service ────────────────────────────────────────
  asset:
    build:
      context: .
      dockerfile: services/asset/Dockerfile
    env_file: services/asset/.env
    ports:
      - "8002:8002"
    depends_on:
      db:
        condition: service_healthy
      migrations:
        condition: service_completed_successfully

  # ─── Order Service ────────────────────────────────────────
  order:
    build:
      context: .
      dockerfile: services/order/Dockerfile
    env_file: services/order/.env
    ports:
      - "8003:8003"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
      migrations:
        condition: service_completed_successfully

  # ─── Inventory Service ────────────────────────────────────
  inventory:
    build:
      context: .
      dockerfile: services/inventory/Dockerfile
    env_file: services/inventory/.env
    ports:
      - "8004:8004"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  # ─── Finance Service ──────────────────────────────────────
  finance:
    build:
      context: .
      dockerfile: services/finance/Dockerfile
    env_file: services/finance/.env
    ports:
      - "8005:8005"
    depends_on:
      db:
        condition: service_healthy

  # ─── Notification Service ─────────────────────────────────
  notification:
    build:
      context: .
      dockerfile: services/notification/Dockerfile
    env_file: services/notification/.env
    ports:
      - "8006:8006"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  # ─── Nginx (API Gateway) ──────────────────────────────────
  nginx:
    image: nginx:1.25-alpine
    volumes:
      - ./infra/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    ports:
      - "80:80"
    depends_on:
      - auth
      - asset
      - order
      - inventory
      - finance
      - notification

volumes:
  postgres_data:
  redis_data:
```

---

## .env.example Raiz

```bash
# .env.example — raiz do projeto
# Copie para .env e preencha os valores [OPERADOR] antes de rodar.
# Valores [DEV] já têm padrão para desenvolvimento local.

# ── Banco de Dados (Supabase em produção / Docker local em dev) ──
POSTGRES_DB=manutech         # [DEV] nome do banco
POSTGRES_USER=postgres       # [DEV] usuário do banco
POSTGRES_PASSWORD=           # [OPERADOR] senha do banco — OBRIGATÓRIO
DATABASE_URL=postgresql+asyncpg://postgres:SENHA@localhost:5432/manutech  # [OPERADOR]

# ── Redis ──
REDIS_PASSWORD=              # [OPERADOR] senha do Redis — OBRIGATÓRIO
REDIS_URL=redis://:SENHA@localhost:6379/0  # [OPERADOR]
```

---

## Comandos Úteis

```bash
# Subir tudo do zero:
docker-compose up --build

# Apenas banco e Redis (desenvolvimento de um serviço isolado):
docker-compose up db redis

# Ver logs de um serviço:
docker-compose logs -f order

# Executar migration manualmente:
docker-compose run --rm migrations alembic upgrade head

# Criar nova migration:
docker-compose run --rm migrations alembic revision --autogenerate -m "descricao"
```
