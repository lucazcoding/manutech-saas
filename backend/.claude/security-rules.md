# Segurança — Regras

## Autenticação — JWT RS256

- Access Token: expiração **1 hora** (`expires_in: 3600`)
- Refresh Token: expiração **7 dias**
- Algoritmo: **RS256** (chave assimétrica — par de chaves RSA)
- Chave privada usada apenas para assinar (Auth Service)
- Chave pública usada apenas para verificar (todos os serviços)

```python
# shared/auth/jwt.py
import jwt
from datetime import datetime, timedelta, timezone

def create_access_token(payload: dict, private_key: str) -> str:
    data = {
        **payload,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(data, private_key, algorithm="RS256")

def verify_token(token: str, public_key: str) -> dict:
    return jwt.decode(token, public_key, algorithms=["RS256"])
```

### Claims obrigatórios no JWT

```json
{
  "sub": "1",           // user_id como string
  "role": "supervisor", // user_role enum
  "name": "João Silva", // nome para logs
  "exp": 1234567890,
  "iat": 1234567890
}
```

---

## Refresh Token — Armazenamento

O Refresh Token é armazenado como **hash SHA-256** na tabela `refresh_tokens`.  
Nunca armazenar o token em texto plano.

```python
import hashlib

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
```

Fluxo completo:
1. Gerar UUID aleatório seguro (`secrets.token_urlsafe(64)`) como refresh token
2. Salvar `hash_sha256(token)` na tabela com `expires_at` = now + 7 dias
3. Retornar o token bruto ao cliente
4. No refresh: receber token bruto, hashear, buscar no banco, verificar `revoked = false` e `expires_at > now()`

---

## Senhas — bcrypt

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# bcrypt custo 12 (padrão passlib)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
```

- Senha mínima: **8 caracteres** (validado no Pydantic)
- O hash é gerado no Python, **antes** de qualquer interação com o banco
- `password_hash` **jamais** aparece em qualquer schema Pydantic de response

---

## RBAC — Dependency FastAPI

```python
# shared/auth/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dataclasses import dataclass
import jwt

security = HTTPBearer()


@dataclass
class UserClaims:
    id: int
    role: str
    name: str


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UserClaims:
    token = credentials.credentials
    try:
        payload = verify_token(token, settings.JWT_PUBLIC_KEY)
        return UserClaims(
            id=int(payload["sub"]),
            role=payload["role"],
            name=payload["name"],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_roles(roles: list[str]):
    async def check(current_user: UserClaims = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissão insuficiente para este recurso",
            )
    return check
```

---

## Rate Limiting — Login Brute Force

Implementado no Auth Service com Redis:

```python
# services/auth/services/rate_limit.py
import redis.asyncio as redis

LOGIN_ATTEMPTS_KEY = "login_attempts:{ip}"
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 900  # 15 minutos

async def check_rate_limit(ip: str, redis_client: redis.Redis) -> None:
    key = LOGIN_ATTEMPTS_KEY.format(ip=ip)
    attempts = await redis_client.get(key)
    if attempts and int(attempts) >= MAX_ATTEMPTS:
        raise BusinessError("RATE_LIMIT_EXCEEDED", 429, "Muitas tentativas. Tente novamente em 15 minutos.")

async def increment_attempts(ip: str, redis_client: redis.Redis) -> None:
    key = LOGIN_ATTEMPTS_KEY.format(ip=ip)
    pipe = redis_client.pipeline()
    pipe.incr(key)
    pipe.expire(key, WINDOW_SECONDS)
    await pipe.execute()

async def reset_attempts(ip: str, redis_client: redis.Redis) -> None:
    await redis_client.delete(LOGIN_ATTEMPTS_KEY.format(ip=ip))
```

---

## Variáveis de Ambiente — Responsabilidades

### ⚠️ ATENÇÃO AO DESENVOLVEDOR

As variáveis marcadas como `[OPERADOR]` devem ser preenchidas pelo **responsável pela infraestrutura** antes do primeiro deploy.  
As marcadas como `[DEV]` têm valores padrão para desenvolvimento local e podem ser deixadas como estão.

> Nunca commite arquivos `.env` com valores reais. Apenas `.env.example` vai para o repositório.

Consulte `env-guide.md` para a lista completa de variáveis, seus tipos, valores padrão e responsabilidades.

---

## Segurança de Uploads

```python
ALLOWED_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/webp"}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB

async def validate_upload(file: UploadFile) -> None:
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise BusinessError("UNSUPPORTED_MIME_TYPE", 422, f"Tipo de arquivo não permitido: {file.content_type}")

    # Ler e verificar tamanho (sem carregar tudo na memória)
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise BusinessError("FILE_TOO_LARGE", 413, "Arquivo excede o limite de 20 MB")

    await file.seek(0)  # resetar cursor após leitura
    return content
```

O `file_path` salvo no banco é sempre um UUID gerado server-side — nunca o nome original do arquivo:

```python
import uuid
file_path = f"attachments/{uuid.uuid4()}{Path(file.filename).suffix}"
```

---

## O que JAMAIS fazer

- ❌ Expor `password_hash` em qualquer response
- ❌ Hardcodar credentials, tokens ou chaves no código
- ❌ Logar tokens, senhas ou dados sensíveis
- ❌ Expor stack trace em respostas de erro 500
- ❌ Aceitar upload sem validar MIME type
- ❌ Usar `../` em file paths (constraint no banco + validar na API)
- ❌ Assinar JWT com chave simétrica (HS256) em produção
- ❌ Retornar dados de outro usuário sem verificar RLS
