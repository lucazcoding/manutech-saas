# Guia de Variáveis de Ambiente

## Legenda de Responsabilidade

| Símbolo | Significado |
|---------|-------------|
| `[OPERADOR]` | Preenchido pelo responsável de infraestrutura/produto antes do deploy. O dev **não deve inventar** esses valores. |
| `[DEV]` | Tem valor padrão seguro para desenvolvimento local. Pode ser usado como está em dev. |
| `[GERADO]` | Gerado automaticamente (ex: par de chaves RSA). Instruções abaixo. |

> ⚠️ **NUNCA** commite arquivos `.env` com valores reais no repositório.  
> ✅ **SEMPRE** mantenha `.env.example` atualizado com todas as variáveis e seus tipos.

---

## Serviços Externos — O que vem de fora

Antes de rodar o projeto pela primeira vez, o operador precisa provisionar:

### 1. PostgreSQL — Supabase (produção/staging)

**O que é:** Banco de dados principal do projeto.  
**Quem provisiona:** Operador (criar projeto no Supabase, obter connection string).  
**Em dev local:** Usar o container Docker do `docker-compose.yml`.

Variáveis que o operador fornece:
```
DATABASE_URL=postgresql+asyncpg://...   # connection string completa do Supabase
```

### 2. Redis (produção/staging)

**O que é:** Cache + Pub/Sub de eventos.  
**Opções:** Redis Cloud (free tier disponível), Upstash, ou container Docker local.  
**Quem provisiona:** Operador.  
**Em dev local:** Usar o container Docker do `docker-compose.yml`.

Variáveis que o operador fornece:
```
REDIS_URL=redis://:senha@host:6379/0
REDIS_PASSWORD=...
```

### 3. Storage de Arquivos (uploads/anexos)

**O que é:** Onde os anexos das OS (PDFs, imagens) são armazenados fisicamente.  
**Decisão pendente:** O MVP pode usar Supabase Storage, S3, ou disco local (apenas para dev).  
**⚠️ O dev deve perguntar ao operador qual provedor usar antes de implementar o upload.**

Variáveis dependem da escolha:
```bash
# Se Supabase Storage:
STORAGE_PROVIDER=supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=...     # [OPERADOR] — nunca expor no frontend
STORAGE_BUCKET=attachments   # [DEV] nome do bucket

# Se AWS S3:
STORAGE_PROVIDER=s3
AWS_ACCESS_KEY_ID=...        # [OPERADOR]
AWS_SECRET_ACCESS_KEY=...    # [OPERADOR]
AWS_S3_BUCKET=manutech-attachments
AWS_S3_REGION=us-east-1

# Se disco local (apenas desenvolvimento):
STORAGE_PROVIDER=local
STORAGE_LOCAL_PATH=/app/uploads
```

### 4. Chaves JWT (RS256)

**O que é:** Par de chaves RSA para assinar e verificar tokens JWT.  
**Quem gera:** O dev gera UMA VEZ usando o comando abaixo e entrega ao operador para armazenar com segurança.

```bash
# Gerar par de chaves RSA 2048 bits:
openssl genrsa -out jwt_private.pem 2048
openssl rsa -in jwt_private.pem -pubout -out jwt_public.pem

# Converter para formato single-line (para uso em env var):
cat jwt_private.pem | tr '\n' '\\n'
cat jwt_public.pem | tr '\n' '\\n'
```

> ⚠️ A chave privada fica **apenas** no Auth Service.  
> A chave pública é compartilhada com todos os outros serviços para verificação.

```bash
# Auth Service:
JWT_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"

# Todos os serviços (inclusive Auth):
JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
```

---

## Variáveis por Serviço

### Auth Service (porta 8001)

```bash
# services/auth/.env.example

# ── Servidor ────────────────────────────────────────
SERVICE_PORT=8001                    # [DEV]
ENVIRONMENT=development              # [DEV] development | staging | production

# ── Banco de Dados ──────────────────────────────────
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/manutech  # [OPERADOR em prod / DEV local]

# ── Redis ───────────────────────────────────────────
REDIS_URL=redis://:senha@redis:6379/0    # [OPERADOR em prod / DEV local]
REDIS_PASSWORD=                           # [OPERADOR]

# ── JWT ─────────────────────────────────────────────
JWT_PRIVATE_KEY=                     # [OPERADOR] — chave privada RSA, apenas no Auth Service
JWT_PUBLIC_KEY=                      # [OPERADOR] — chave pública RSA
JWT_ACCESS_TOKEN_EXPIRE_HOURS=1      # [DEV]
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7      # [DEV]

# ── Rate Limiting ────────────────────────────────────
LOGIN_MAX_ATTEMPTS=5                 # [DEV]
LOGIN_WINDOW_SECONDS=900             # [DEV] 15 minutos
```

### Asset Service (porta 8002)

```bash
# services/asset/.env.example

SERVICE_PORT=8002                    # [DEV]
ENVIRONMENT=development              # [DEV]

DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/manutech  # [OPERADOR em prod]
JWT_PUBLIC_KEY=                      # [OPERADOR]
```

### Order Service (porta 8003)

```bash
# services/order/.env.example

SERVICE_PORT=8003                    # [DEV]
ENVIRONMENT=development              # [DEV]

DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/manutech  # [OPERADOR em prod]
REDIS_URL=redis://:senha@redis:6379/0    # [OPERADOR em prod]
JWT_PUBLIC_KEY=                      # [OPERADOR]

# ── Storage (para anexos) ────────────────────────────
STORAGE_PROVIDER=local               # [OPERADOR] local | supabase | s3
STORAGE_LOCAL_PATH=/app/uploads      # [DEV] apenas se STORAGE_PROVIDER=local
# Demais variáveis de storage: ver seção "Storage de Arquivos" acima

# ── Cache ────────────────────────────────────────────
STATS_CACHE_TTL_SECONDS=30           # [DEV]
```

### Inventory Service (porta 8004)

```bash
# services/inventory/.env.example

SERVICE_PORT=8004                    # [DEV]
ENVIRONMENT=development              # [DEV]

DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/manutech  # [OPERADOR em prod]
REDIS_URL=redis://:senha@redis:6379/0    # [OPERADOR em prod]
JWT_PUBLIC_KEY=                      # [OPERADOR]
```

### Finance Service (porta 8005)

```bash
# services/finance/.env.example

SERVICE_PORT=8005                    # [DEV]
ENVIRONMENT=development              # [DEV]

DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/manutech  # [OPERADOR em prod]
JWT_PUBLIC_KEY=                      # [OPERADOR]

# ── Exportação de relatórios ─────────────────────────
# (sem dependências externas no MVP — geração local com openpyxl/reportlab)
```

### Notification Service (porta 8006)

```bash
# services/notification/.env.example

SERVICE_PORT=8006                    # [DEV]
ENVIRONMENT=development              # [DEV]

DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/manutech  # [OPERADOR em prod]
REDIS_URL=redis://:senha@redis:6379/0    # [OPERADOR em prod]
JWT_PUBLIC_KEY=                      # [OPERADOR]

# ── WebSocket ────────────────────────────────────────
WS_MAX_CONNECTIONS_PER_USER=5        # [DEV] máx. conexões simultâneas por usuário
```

---

## Checklist — Antes do Primeiro Deploy

O operador deve confirmar:

- [ ] `DATABASE_URL` aponta para Supabase (não para container local)
- [ ] `REDIS_URL` aponta para Redis Cloud ou similar (não container local)
- [ ] `JWT_PRIVATE_KEY` está configurada **apenas** no Auth Service
- [ ] `JWT_PUBLIC_KEY` está configurada em **todos** os serviços
- [ ] `STORAGE_PROVIDER` e variáveis de storage definidas para o serviço escolhido
- [ ] `REDIS_PASSWORD` definida (Redis sem senha não deve ir para produção)
- [ ] `ENVIRONMENT=production` em todos os serviços em produção
- [ ] Nenhum `.env` real foi commitado no repositório (verificar `.gitignore`)

---

## .gitignore Mínimo

```gitignore
# .gitignore
.env
.env.*
!.env.example
*.pem
jwt_private.pem
jwt_public.pem
__pycache__/
*.pyc
.coverage
htmlcov/
uploads/
```
