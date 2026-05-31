# Serviços Externos — Referência

Este arquivo documenta todos os serviços de terceiros que o MANUTECH usa ou pode usar, deixando claro o que é responsabilidade do desenvolvedor vs. do operador de infraestrutura.

---

## Mapa de Serviços

| Serviço | Uso | Provedor Atual | Status |
|---------|-----|---------------|--------|
| PostgreSQL | Banco principal | Supabase (prod) / Docker (dev) | ✅ Definido |
| Redis | Cache + Pub/Sub | Redis Cloud / Docker (dev) | ✅ Definido |
| Storage de arquivos | Anexos de OS | **A definir** ⚠️ | 🔴 Pendente |
| Email/SMTP | Notificações por email | Não no MVP | ❌ Fora do escopo |
| Push mobile | Notificações mobile | Não no MVP | ❌ Fora do escopo |

---

## Supabase (PostgreSQL)

**O que usamos:** Apenas o PostgreSQL hospedado. Não usamos o SDK do Supabase no backend Python.

**Responsabilidade do Operador:**
- Criar o projeto no Supabase
- Copiar a connection string (`postgresql+asyncpg://...`)
- Habilitar extensões necessárias (`pgcrypto` se necessário)
- Configurar backups automáticos

**Responsabilidade do Dev:**
- Usar a `DATABASE_URL` fornecida pelo operador
- Escrever migrations Alembic que funcionem em PostgreSQL padrão (agnóstico de Supabase)
- Nunca usar APIs específicas do Supabase SDK

**RLS no Supabase:**  
As policies RLS do schema são criadas via migration Alembic. O Supabase respeita policies PostgreSQL padrão — não é necessário usar o painel do Supabase para isso.

**Supabase Storage (se escolhido para uploads):**  
Se o operador escolher Supabase Storage para os anexos, o dev precisará:
- Usar a biblioteca `storage3` ou `supabase-py` para upload/download
- A variável `SUPABASE_SERVICE_KEY` é necessária (nunca expor no frontend)
- Configurar bucket `attachments` como privado (acesso apenas via service key)

```python
# Exemplo de upload para Supabase Storage
from supabase import create_client, Client

supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

def upload_file(path: str, content: bytes, mime_type: str) -> str:
    supabase.storage.from_("attachments").upload(
        path=path,
        file=content,
        file_options={"content-type": mime_type}
    )
    return path
```

---

## Redis

**Versão:** Redis 7+

**Usos no projeto:**
1. Rate limiting de login (TTL 15 min por IP)
2. Cache de `GET /orders/stats` (TTL 30s)
3. Pub/Sub: `order.assigned`, `order.status_changed`, `stock.low_alert`

**Responsabilidade do Operador:**
- Provisionar instância Redis (Redis Cloud free tier, Upstash, ou Railway)
- Configurar senha obrigatória
- Fornecer `REDIS_URL` e `REDIS_PASSWORD`

**Responsabilidade do Dev:**
- Usar o client async (`redis.asyncio`) com as variáveis fornecidas
- Garantir que falhas no Redis não quebrem o response principal (try/except + log)
- Nunca armazenar dados de negócio permanentes no Redis

**Biblioteca:**
```
redis[asyncio]>=5.0.0
```

---

## Storage de Arquivos — Decisão Pendente ⚠️

**O dev deve perguntar ao operador/produto antes de implementar a rota de upload:**  
> "Onde os anexos das OS serão armazenados? Supabase Storage, AWS S3, ou disco local (apenas dev)?"

### Opção A — Supabase Storage

- Integrado ao banco já existente
- Free tier generoso (1 GB)
- Requer `SUPABASE_URL` e `SUPABASE_SERVICE_KEY`

### Opção B — AWS S3 (ou compatível: Cloudflare R2, MinIO)

- Mais escalável
- Requer `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_BUCKET`, `AWS_S3_REGION`

### Opção C — Disco Local

- Apenas para desenvolvimento
- Não usar em produção
- Configurar volume Docker para persistência

**Implementação:**  
Independentemente da opção escolhida, criar uma interface `StorageBackend` para que a troca de provedor não quebre o código:

```python
# shared/storage/base.py
from abc import ABC, abstractmethod

class StorageBackend(ABC):
    @abstractmethod
    async def upload(self, path: str, content: bytes, mime_type: str) -> str:
        """Retorna o file_path para salvar no banco."""
        ...

    @abstractmethod
    async def get_download_url(self, file_path: str) -> str:
        """Retorna URL ou stream para download."""
        ...

    @abstractmethod
    async def delete(self, file_path: str) -> None:
        ...
```

---

## Serviços Fora do Escopo do MVP

### Email
- Notificações por email **não fazem parte do MVP**
- O sistema de notificação é WebSocket + banco (tabela `notifications`)
- Se necessário no futuro: Resend, SendGrid ou AWS SES

### Push Notifications Mobile
- **Não no MVP** — apenas WebSocket para web
- Se necessário no futuro: Firebase Cloud Messaging (FCM)

### Monitoramento/APM
- **Não configurado no MVP** — mas o dev deve garantir logs estruturados em JSON para facilitar futura integração
- Opções futuras: Sentry, Datadog, Grafana + Loki

```python
# Logging estruturado mínimo (já implementar assim)
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "level": record.levelname,
            "message": record.getMessage(),
            "service": record.name,
            "timestamp": self.formatTime(record),
        })
```
