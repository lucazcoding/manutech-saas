# Contratos de API — Regras

## Fonte de Verdade

O arquivo `MANUTECH_API_Documentation_v2.md` é a especificação definitiva.  
O arquivo `MANUTECH_Rotas_Resumo_v2.md` é apenas um resumo de consulta rápida.  
Em caso de conflito entre os dois, o arquivo completo de documentação prevalece.

**Nunca invente:**
- Rotas não documentadas
- Campos de request não especificados
- Campos de response não especificados
- Códigos de erro não mapeados
- Roles não existentes

---

## Paginação — Obrigatória em todas as listagens

Toda rota `GET` que retorna múltiplos itens aceita:

```
?page=1&page_size=20
```

E responde **sempre** com o envelope:

```json
{
  "items": [...],
  "total": 120,
  "page": 1,
  "page_size": 20,
  "pages": 6
}
```

- `items` **nunca** é `null` — retorna `[]` quando vazio
- `page_size` máximo: 100
- Implementar com schema genérico `PaginatedResponse[T]`

```python
# shared/schemas/pagination.py
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int
```

---

## Envelope de Erro (sempre este formato)

```json
{
  "detail": "Mensagem legível do erro",
  "code": "SNAKE_CASE_ERROR_CODE",
  "field": "nome_do_campo"
}
```

O campo `field` só aparece em erros de validação de campo específico.

### Códigos de erro documentados (não invente novos)

| Code | HTTP | Situação |
|------|------|----------|
| `INVALID_CREDENTIALS` | 401 | Login ou senha incorretos |
| `USER_INACTIVE` | 403 | Usuário inativo tentando login |
| `RATE_LIMIT_EXCEEDED` | 429 | Brute force de login |
| `REFRESH_TOKEN_INVALID` | 401 | Token não encontrado ou revogado |
| `REFRESH_TOKEN_EXPIRED` | 401 | Token expirado |
| `LOGIN_ALREADY_EXISTS` | 409 | Login duplicado |
| `EMAIL_ALREADY_EXISTS` | 409 | Email duplicado |
| `SERIAL_NUMBER_ALREADY_EXISTS` | 409 | Serial number de asset duplicado |
| `ASSET_NOT_FOUND` | 404 | asset_id inválido na OS |
| `ASSET_INACTIVE` | 400 | Equipamento inativo vinculado a OS |
| `INVALID_STATUS_TRANSITION` | 400 | Transição de status inválida |
| `TECHNICIAN_REQUIRED` | 400 | open→in_progress sem técnico atribuído |
| `CANCELLATION_REASON_REQUIRED` | 400 | Cancelamento sem reason |
| `TECHNICIAN_NOT_FOUND` | 404 | technician_id inválido |
| `NOT_A_TECHNICIAN` | 422 | Usuário não tem role technician |
| `ORDER_CLOSED` | 400 | Operação em OS completed/cancelled |
| `SKU_ALREADY_EXISTS` | 409 | SKU de material duplicado |
| `INSUFFICIENT_STOCK` | 400 | Saldo negativo bloqueado pelo trigger |
| `MATERIAL_NOT_FOUND` | 404 | material_id inválido |
| `ORDER_NOT_FOUND` | 404 | service_order_id inválido |
| `BUDGET_NOT_EDITABLE` | 400 | Edição de budget fora do status draft |
| `FILE_TOO_LARGE` | 413 | Upload > 20 MB |
| `UNSUPPORTED_MIME_TYPE` | 422 | MIME type não permitido |
| `VALIDATION_ERROR` | 422 | Validação Pydantic genérica |

---

## Headers obrigatórios

```
Authorization: Bearer <access_token>
Content-Type: application/json
Accept: application/json
```

Exceção: upload de arquivo usa `Content-Type: multipart/form-data`.

---

## Tipos de dados — Convenções

| Tipo | Formato |
|------|---------|
| IDs | `int` (BIGINT) — nunca UUID |
| Datas | ISO 8601 com timezone UTC: `"2025-06-01T10:00:00Z"` |
| Valores monetários | `float` com 2 casas decimais: `162.50` — nunca string |
| Quantidades de estoque | `float` com 3 casas: `10.000` |
| Booleans | `true` / `false` JSON nativo |

---

## Rotas de Upload

- Content-Type: `multipart/form-data`
- Tipos MIME aceitos: `application/pdf`, `image/jpeg`, `image/png`, `image/webp`
- Limite de negócio: **20 MB** (validar na API antes do banco)
- Limite do banco: 50 MB (constraint `size_bytes <= 52428800`) — não use como referência primária
- UUID gerado server-side para o `file_path` (nunca usar nome original como path)

---

## Download de Arquivos

```python
# Response headers obrigatórios:
Content-Disposition: attachment; filename="nome-original.pdf"
Content-Type: application/pdf  # mime_type armazenado no banco
```

---

## WebSocket — Autenticação

```
ws://host/ws/notifications?token=<JWT>
```

- Conexão recusada com código `4001` se JWT ausente ou inválido
- Não usar header `Authorization` para WebSocket (não suportado pelo protocolo)

---

## Cache Redis — Rotas com TTL definido

| Rota | TTL |
|------|-----|
| `GET /orders/stats` | 30 segundos |

Invalidar cache quando dados mudarem (ex: nova OS criada, status alterado).
