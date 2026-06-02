# Manutech SaaS — Backend Microservices

O Manutech SaaS é uma plataforma robusta e escalável para controle de ordens de serviço, manutenção preditiva, gestão de ativos/equipamentos, controle de estoque e controle financeiro (custos e orçamentos).

A API foi projetada com base em uma arquitetura de **multi-serviços desacoplados** que compartilham bibliotecas utilitárias, utilizam um **API Gateway centralizado** com Nginx, autenticação **stateless (RS256 JWT)** e comunicação orientada a eventos via **Redis Pub/Sub**.

---

## 🏗️ Arquitetura do Sistema

A arquitetura do backend é dividida em serviços independentes que rodam de forma isolada na mesma rede interna do Docker (`app-net`):

```mermaid
graph TB
    subgraph Browser / Client
        C[Cliente Frontend / Postman]
    end

    subgraph API Gateway
        N["Nginx Gateway (:80)<br/>Route Matching & Global Rate Limiting"]
    end

    subgraph Docker Internal Network
        A["Auth Service (:8001)<br/>JWT Issuing & User CRUD"]
        AS["Asset Service (:8002)<br/>Equipamentos & Localizações"]
        O["Order Service (:8003)<br/>Ordens de Serviço & Atribuições"]
        I["Inventory Service (:8004)<br/>Estoque & Movimentação"]
        F["Finance Service (:8005)<br/>Custos & Orçamentos"]
        NOT["Notification Service (:8006)<br/>Notificações REST + WebSockets"]
        
        DB[("PostgreSQL 16 (:5432)")]
        RD[("Redis 7 (:6379)")]
    end

    C -->|HTTP/WS| N
    
    N -->|/api/v1/auth & /users| A
    N -->|/api/v1/assets| AS
    N -->|/api/v1/orders| O
    N -->|/api/v1/materials & /movements| I
    N -->|/api/v1/costs & /budgets| F
    N -->|/api/v1/notifications| NOT

    A --> DB
    A --> RD
    AS --> DB
    O --> DB
    O --> RD
    I --> DB
    I --> RD
    F --> DB
    NOT --> DB
    NOT --> RD

    style N fill:#f9f,stroke:#333,stroke-width:2px
    style DB fill:#85C1E9,stroke:#2E86C1,stroke-width:2px
    style RD fill:#F1948A,stroke:#CB4335,stroke-width:2px
```

### 1. Gateway & Rate Limiting (Nginx)
O container `nginx` serve como **API Gateway** unificado exposto na porta `80`. Ele encapsula as portas internas dos microserviços e impõe regras de controle de tráfego por IP:
- **Limite Geral:** 100 requisições por minuto (`/api/v1/...`).
- **Limite de Login:** 5 tentativas por minuto para proteger contra ataques de força bruta (`/api/v1/auth/login`).

### 2. Autenticação Desacoplada (RS256 JWT)
A autenticação é totalmente stateless e utiliza criptografia assimétrica RSA (chaves privadas e públicas de 2048 bits):
- O **Auth Service** possui a chave privada (`jwt_private.pem`) e é o único que assina os tokens.
- Os **demais serviços** possuem apenas a chave pública (`jwt_public.pem`), conseguindo validar a assinatura do token e extrair as Claims (User ID, Role, Name) localmente sem precisar fazer requisições HTTP internas para o Auth Service.

```mermaid
sequenceDiagram
    participant C as Cliente
    participant N as Nginx
    participant A as Auth Service
    participant O as Outro Serviço (ex: Order)

    Note over A: Assinatura Criptográfica com Chave Privada (RS256)
    Note over O: Validação de Assinatura com Chave Pública (RS256)

    C->>N: POST /api/v1/auth/login
    N->>A: Redireciona para Auth
    A->>A: Valida credenciais e assina JWT (RS256)
    A-->>C: Retorna Token JWT + Refresh Token

    Note over C,O: Requisições protegidas subsequentes
    C->>N: GET /api/v1/orders (Authorization: Bearer token)
    N->>O: Redireciona para Order
    O->>O: Decodifica JWT localmente usando Chave Pública
    O-->>C: Retorna dados solicitados (200 OK)
```

### 3. Comunicação Baseada em Eventos (Redis Pub/Sub)
A comunicação assíncrona entre os serviços ocorre via Redis. Quando certas ações acontecem nos serviços de negócio, eventos são publicados no Redis, e o **Notification Service** (que roda um assinante em background) captura os eventos para persistir notificações no banco e empurrar via WebSockets para os técnicos conectados.

```mermaid
graph LR
    O["Order Service"] -->|Publica evento: order_assigned| R[("Redis Pub/Sub")]
    I["Inventory Service"] -->|Publica evento: material_low_stock| R
    R -->|Despacha evento| N["Notification Service<br/>(Subscriber)"]
    N -->|WS Push| C["Técnico conectado / WebSockets"]
    N -->|Insert| DB[("Tabela notifications")]
```

---

## 🛠️ Tecnologias & Escolhas de Projeto

| Camada | Tecnologia | Justificativa |
|---|---|---|
| **Linguagem Principal** | Python 3.12+ | Alta performance, suporte assíncrono nativo de alto nível e tipagem estática moderna. |
| **Framework Web** | FastAPI | Validação de dados automática com Pydantic v2, documentação Swagger interativa nativa e performance próxima a NodeJS/Go com async/await. |
| **ORM** | SQLAlchemy 2.0 (asyncpg) | ORM assíncrono avançado para PostgreSQL, permitindo queries complexas de alto desempenho. |
| **Banco de Dados** | PostgreSQL 16 | Banco relacional robusto, com triggers complexas de auditoria e suporte a Row-Level Security (RLS). |
| **Broker de Eventos** | Redis 7 | Armazenamento chave-valor ultrarrápido para controle de limites (Rate Limit), Pub/Sub de eventos de baixo acoplamento e cache. |
| **Migrations** | Alembic | Controle versionado e rastreável do banco de dados em Python. |
| **Validação** | Pydantic v2 | Serialização de schemas e validação rápida em nível de C++. |
| **Testes** | Pytest (pytest-asyncio + httpx) | Facilidade de escrita de fixtures, suporte async robusto e testes rápidos com isolamento transacional. |

---

## 📂 Estrutura de Pastas

```
backend/
├── infra/
│   ├── migrations/               # Configuração e arquivos de migração do Alembic
│   │   └── versions/             # Histórico de alterações do banco de dados (DDL)
│   └── nginx/                    # Arquivos de configuração do API Gateway Nginx
├── shared/
│   └── shared/                   # Biblioteca interna compartilhada por todos os serviços
│       ├── auth/                 # Decodificação de JWT e injeção de dependência de Usuário
│       ├── db/                   # Configuração de engine, RLS e sessão assíncrona
│       ├── redis/                # Cliente de conexão e utilitários Pub/Sub do Redis
│       ├── config.py             # Definição e leitura de variáveis de ambiente básicas
│       └── exceptions/           # Tratamento global de exceções e erros de negócio
├── services/                     # Implementação dos microserviços
│   ├── auth/                     # Serviço de Login/JWT, Cadastro e Gestão de Usuários
│   ├── asset/                    # Serviço de Equipamentos e Localizações
│   ├── order/                    # Serviço de OS, histórico e atribuições
│   ├── inventory/                # Serviço de Estoque de materiais e movimentos de entrada/saída
│   ├── finance/                  # Serviço de Controle financeiro de custos e orçamentos
│   └── notification/             # Serviço de REST API + Push WebSockets de eventos
├── tests/                        # Suite completa de testes
│   ├── auth/                     # Testes unitários do Auth Service
│   ├── asset/                    # Testes unitários do Asset Service
│   ├── ...                       # Testes unitários dos demais módulos
│   ├── e2e/                      # Testes End-to-End integrados contra o Banco e Redis
│   │   ├── conftest.py           # Configura o carregamento automático do `.env.test.docker`
│   │   └── ...                   # Cenários E2E por serviço
│   ├── conftest.py               # Fixtures globais (chaves RSA de teste, tokens de acesso)
│   └── pytest.ini                # Configuração do executor do pytest
├── docker-compose.yml            # Orquestrador local de containers
├── .env.example                  # Variáveis de ambiente de exemplo
└── README.md                     # Documentação principal (Este arquivo)
```

---

## 🚀 Como Rodar o Projeto

### Pré-requisitos
- **Docker Desktop** instalado e rodando.
- **Python 3.12+** instalado localmente (caso queira executar ferramentas locais ou testes rápidos fora de containers).

---

### Opção A: Subindo tudo via Docker (Recomendado)

O Docker Compose está configurado para levantar toda a infraestrutura física (Banco, Redis, Gateway) e todos os 6 serviços da aplicação automaticamente. As migrações do Alembic rodam sozinhas no início do processo.

1. Copie o arquivo de variáveis de ambiente:
   ```powershell
   cp .env.example .env
   ```
2. Inicie o Docker Compose:
   ```powershell
   docker compose up --build -d
   ```
3. Verifique se os serviços estão saudáveis:
   ```powershell
   docker compose ps
   ```

A partir deste momento, todos os serviços estão disponíveis de forma centralizada através da porta `80`:
- **API Gateway (Nginx):** `http://localhost/`
- **Exemplo de endpoints expostos:**
  - Login: `POST http://localhost/api/v1/auth/login`
  - Listar Ativos: `GET http://localhost/api/v1/assets`
  - Criar OS: `POST http://localhost/api/v1/orders`

---

### Opção B: Desenvolvimento Local (Hot-Reload)

Se você preferir executar os serviços diretamente na sua máquina host com hot-reload para programar:

1. **Suba apenas a infraestrutura básica (Banco e Redis) via Docker:**
   ```powershell
   docker compose up db redis -d
   ```
2. **Crie e ative seu ambiente virtual Python local:**
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1    # No Windows (PowerShell)
   source .venv/bin/activate     # No Linux/Mac
   ```
3. **Instale as dependências locais:**
   ```powershell
   pip install -r requirements.txt
   ```
4. **Execute as migrações locais para o banco:**
   ```powershell
   alembic upgrade head
   ```
5. **Rode o serviço desejado manualmente via Uvicorn:**
   *(Altere no `.env` a variável `DATABASE_URL` para apontar para `localhost:5432` em vez de `db:5432`)*
   ```powershell
   uvicorn services.auth.main:app --port 8001 --reload
   ```

---

## 🗃️ Migrações de Banco de Dados (Alembic)

O banco é versionado e gerenciado pelo Alembic. Toda alteração no modelo de dados deve possuir sua migração gerada.

- **Aplicar migrações pendentes:**
  ```powershell
  alembic upgrade head
  ```
- **Voltar a última migração aplicada (Rollback):**
  ```powershell
  alembic downgrade -1
  ```
- **Criar uma nova migração a partir de mudanças de models:**
  ```powershell
  alembic revision --autogenerate -m "nome_da_migracao"
  ```

---

## 🧪 Rodando os Testes (Pytest)

A suíte possui testes unitários (rápidos e com mocks) e testes E2E (com conexões reais ao banco de dados e Redis rodando no Docker).

> [!IMPORTANT]
> Para executar os **testes E2E**, o stack do Docker (`db` e `redis`) precisa estar rodando localmente na sua máquina (`docker compose up -d`).

### Configuração de Testes E2E (Isolação Automática)
Criamos um arquivo especial chamado `.env.test.docker`. Quando o **pytest** inicia, ele carrega automaticamente esse arquivo se ele estiver presente na raiz. Ele define as variáveis de conexão para o banco e o Redis usados nos testes:

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/manutech
REDIS_URL=redis://default:gQAAAAAAAiV5AAIgcDFjYTkxYjcwZmU2ODk0ODkwODQ3MTU0MWIyNzVjOWQzNQ@localhost:6379/0
```

#### Passo a passo para rodar os testes E2E
1. **Copie o exemplo de variáveis** para o arquivo de teste:
   ```powershell
   cp .env.example .env.test.docker
   ```
2. **Inicie apenas a infraestrutura necessária** (Banco e Redis):
   ```powershell
   docker compose up -d db redis
   ```
   > **Dica:** aguarde alguns segundos até o PostgreSQL estar pronto (`docker compose logs -f db`).
3. **Execute os testes** desejados:
   - Todos os testes (unitários + E2E):
     ```powershell
     python -m pytest
     ```
   - Apenas testes unitários (não requer Docker):
     ```powershell
     python -m pytest tests/unit
     ```
   - Apenas testes E2E (exige Docker):
     ```powershell
     python -m pytest tests/e2e
     ```
   - Testes E2E de um serviço específico:
     ```powershell
     python -m pytest tests/e2e/auth        # Autenticação e Usuários
     python -m pytest tests/e2e/asset       # Equipamentos
     python -m pytest tests/e2e/order       # Ordens de Serviço (OS)
     python -m pytest tests/e2e/inventory   # Materiais e Estoque
     python -m pytest tests/e2e/finance     # Custos e Orçamentos
     python -m pytest tests/e2e/notification # Notificações e WebSockets
     ```

### Isolamento de Banco de Dados nos Testes E2E
Cada teste é executado dentro de uma transação isolada com `SAVEPOINT` e um `ROLLBACK` é emitido ao final de cada cenário (`db_session` fixture). Dessa forma:
- Os testes não geram lixo ou interferência no seu banco de dados de desenvolvimento.
- Os quatro usuários padrão de teste (Admin ID=1, Supervisor ID=2, Técnico ID=3, Atendente ID=4) são semeados automaticamente na transação no início de cada teste, prevenindo violações de chaves estrangeiras de auditoria ou RLS.
- O rate limiter do Redis é limpo automaticamente a cada teste, prevenindo erros `429 Too Many Requests`.


A suíte possui testes unitários (rápidos e com mocks) e testes E2E (com conexões reais ao banco de dados e Redis rodando no Docker).
## 📋 Guia de Execução de Testes E2E

### Pré‑requisitos
- **Docker Desktop** (ou Docker Engine) rodando.
- **Python 3.12+** e `pip` instalados.

### Configurando o ambiente de teste
1. **Copie o exemplo de variáveis** para o arquivo de teste:
   ```powershell
   cp .env.example .env.test.docker
   ```
2. **Edite** `.env.test.docker` e garanta que os valores apontem para `localhost`:
   ```dotenv
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/manutech
   REDIS_URL=redis://default:gQAAAAAAAiV5AAIgcDFjYTkxYjcwZmU2ODk0ODkwODQ3MTU0MWIyNzVjOWQzNQ@localhost:6379/0
   ```
3. **Inicie somente a infraestrutura necessária** (Banco e Redis):
   ```powershell
   docker compose up -d db redis
   ```
   > **Dica:** aguarde até o PostgreSQL estar pronto (`docker compose logs -f db`).

### Executando os testes
- **Todos os testes (unitários + E2E):**
  ```powershell
  python -m pytest
  ```
- **Apenas testes unitários (sem Docker):**
  ```powershell
  python -m pytest tests/unit
  ```
- **Apenas testes E2E (exige Docker):**
  ```powershell
  python -m pytest tests/e2e
  ```
- **Testes E2E de um serviço específico:**
  ```powershell
  python -m pytest tests/e2e/auth        # Autenticação e Usuários
  python -m pytest tests/e2e/asset       # Equipamentos
  python -m pytest tests/e2e/order       # Ordens de Serviço
  python -m pytest tests/e2e/inventory   # Materiais e Estoque
  python -m pytest tests/e2e/finance     # Custos e Orçamentos
  python -m pytest tests/e2e/notification # Notificações e WebSockets
  ```

### Pós‑execução
Os testes E2E utilizam transações com `SAVEPOINT` e realizam `ROLLBACK` ao final de cada cenário, garantindo que **nenhum dado persista** no seu banco local. Caso queira remover os containers usados nos testes:
```powershell
docker compose down -v
```

---
> [!IMPORTANT]
> Para executar os testes E2E, o stack do Docker (`db` e `redis`) precisa estar rodando localmente na sua máquina (`docker compose up -d`).

### Configuração de Testes E2E (Isolação Automática)
Criamos um arquivo especial chamado `.env.test.docker`. Quando o pytest inicia, ele carrega automaticamente esse arquivo se ele estiver presente na raiz. Ele diz para o pytest testar contra as portas expostas no `localhost` da sua máquina host:

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/manutech
REDIS_URL=redis://default:gQAAAAAAAiV5AAIgcDFjYTkxYjcwZmU2ODk0ODkwODQ3MTU0MWIyNzVjOWQzNQ@localhost:6379/0
```

### Comandos de Teste

- **Executar TODOS os testes (Unitários + E2E):**
  ```powershell
  python -m pytest
  ```

- **Executar apenas testes UNITÁRIOS (Não precisam do Docker rodando):**
  ```powershell
  python -m pytest tests/unit
  ```

- **Executar apenas testes E2E (Exige o Docker rodando):**
  ```powershell
  python -m pytest tests/e2e
  ```

- **Executar testes E2E de um serviço específico:**
  ```powershell
  python -m pytest tests/e2e/auth        # Autenticação e Usuários
  python -m pytest tests/e2e/asset       # Equipamentos
  python -m pytest tests/e2e/order       # Ordens de Serviço (OS)
  python -m pytest tests/e2e/inventory   # Materiais e Estoque
  python -m pytest tests/e2e/finance     # Custos e Orçamentos
  python -m pytest tests/e2e/notification # Notificações e WebSockets
  ```

### Isolamento de Banco de Dados nos Testes E2E
Cada teste é executado dentro de uma transação isolada com `SAVEPOINT` e um `ROLLBACK` é emitido ao final de cada cenário (`db_session` fixture). Desse modo:
- Os testes não geram lixo ou interferência no seu banco de dados de desenvolvimento.
- Os 4 usuários padrão de teste (Admin ID=1, Supervisor ID=2, Técnico ID=3, Atendente ID=4) são semeados automaticamente na transação no início de cada teste, prevenindo violações de chaves estrangeiras de auditoria ou RLS.
- O rate limiter do Redis é limpo automaticamente a cada teste, prevenindo erros `429 Too Many Requests`.

---

## 🧠 Decisões Técnicas

- **Por que FastAPI e não Express?** Python traz um ecossistema nativo rico e performático para cálculos matemáticos e operações assíncronas. O FastAPI nos dá validação estática via Pydantic e segurança tipada imediata, diminuindo bugs em produção.
- **Por que PostgreSQL com RLS e Triggers?** O sistema de segurança exige controle rígido de acesso. Com Row-Level Security (RLS) configurado no banco e alimentado pelas variáveis locais de transação (`SET LOCAL app.user_id`), garantimos que um técnico nunca acesse dados ou ordens que não foram atribuídas a ele, mesmo se houver falha de validação lógica no backend.
- **Triggers de Auditoria:** Triggers PL/pgSQL geram automaticamente logs de alterações em `audit_logs` ao atualizar ordens de serviço, capturando o `changed_by` diretamente da sessão local do Postgres.
- **Por que Redis Pub/Sub e não RabbitMQ/Kafka?** Redis já é utilizado para gerenciar limites de requisição (Rate Limit) e cache rápido de logins. Aproveitar seu Pub/Sub nativo para a comunicação assíncrona com o microserviço de Notificações reduziu o tamanho da infraestrutura e atende perfeitamente a necessidade de baixa latência e push em tempo real via WebSockets.
