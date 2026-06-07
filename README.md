# MANUTECH — Plataforma de Gestao de Manutencao Industrial

Sistema SaaS completo para centralizar o ciclo de vida da manutencao industrial: do atendimento inicial (atendente recebe o chamado) ate a execucao tecnica, passando pela coordenacao (supervisor) e administracao do sistema (admin).

---

## Sumario

- [Visao Geral](#visao-geral)
- [Arquitetura do Sistema](#arquitetura-do-sistema)
- [Stack Tecnologica](#stack-tecnologica)
- [Pre-requisitos](#pre-requisitos)
- [Instalacao do Zero](#instalacao-do-zero)
- [Credenciais](#credenciais)
- [Estrutura do Repositorio](#estrutura-do-repositorio)
- [Perfis de Usuario e RBAC](#perfis-de-usuario-e-rbac)
- [Fluxo de Trabalho](#fluxo-de-trabalho)
- [Variaveis de Ambiente](#variaveis-de-ambiente)
- [Testes](#testes)
- [Troubleshooting](#troubleshooting)
- [Aviso](#aviso)

---

## Visao Geral

O MANUTECH e uma plataforma web para gestao de manutencao preditiva e corretiva em ambientes industriais. Ele integra:

- **Ordens de Servico (OS)** — criacao, atribuicao, execucao, conclusao e cancelamento com controle de status via state machine.
- **Equipamentos/Ativos** — cadastro, localizacao e historico de manutencao por equipamento.
- **Estoque e Materiais** — controle de materiais com estoque minimo, movimentacoes de entrada/saida e alertas de estoque baixo.
- **Financeiro** — custos por OS, orcamentos com status (rascunho/enviado/aprovado), relatorios consolidados e exportacao em Excel/PDF.
- **Notificacoes em tempo real** — WebSocket para alertas de atribuicao, solicitacao de conclusao e estoque baixo.
- **Auditoria** — logs de alteracoes em OS com tracabilidade de quem fez o que e quando.
- **RBAC (Role-Based Access Control)** — 4 perfis com permissoes distintas, incluindo RLS (Row-Level Security) no banco para garantir que tecnicos so vejam suas proprias OS.

---

## Arquitetura do Sistema

O backend segue uma arquitetura de **microservicos desacoplados** que compartilham bibliotecas utilitarias, comunicam-se via **Redis Pub/Sub** e sao expostos por um **API Gateway centralizado (Nginx)**.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Browser / Cliente                              │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │ HTTP / WebSocket
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      API Gateway — Nginx (:80)                         │
│              Route Matching · Rate Limiting · SPA Static Files          │
└───┬──────────┬──────────┬──────────┬──────────┬──────────┬─────────────┘
    │          │          │          │          │          │
    ▼          ▼          ▼          ▼          ▼          ▼
┌────────┐┌────────┐┌────────┐┌────────┐┌────────┐┌────────────┐
│ Auth   ││ Asset  ││ Order  ││Invent. ││Finance ││Notification│
│ :8001  ││ :8002  ││ :8003  ││ :8004  ││ :8005  ││   :8006    │
│JWT/User││Equipam.││  OS    ││Estoque ││Custos  ││REST + WS   │
└───┬────┘└───┬────┘└───┬────┘└───┬────┘└───┬────┘└──┬───────┘
    │         │         │         │         │        │
    └─────────┴─────────┴────┬────┴─────────┴────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
               ┌────▼────┐     ┌─────▼─────┐
               │PostgreSQL│     │   Redis   │
               │  16      │     │    7      │
               │ (:5432)  │     │  (:6379)  │
               └─────────┘     └───────────┘
```

### Servicos

| Servico | Porta | Responsabilidade |
|---------|:-----:|------------------|
| **Auth Service** | 8001 | Login, JWT (RS256), CRUD de usuarios |
| **Asset Service** | 8002 | Cadastro de equipamentos e localizacoes |
| **Order Service** | 8003 | Ordens de servico, atribuicoes, historico |
| **Inventory Service** | 8004 | Materiais, movimentacoes de estoque |
| **Finance Service** | 8005 | Custos, orcamentos, relatorios |
| **Notification Service** | 8006 | Notificacoes REST + WebSockets |
| **Nginx Gateway** | 80 | API Gateway, rate limiting, arquivos estaticos |
| **PostgreSQL** | 5432 | Banco de dados relacional |
| **Redis** | 6379 | Rate limit, pub/sub, cache |

### Decisoes de Arquitetura

- **Autenticacao stateless (RS256 JWT):** O Auth Service assina tokens com chave privada RSA (2048 bits). Os demais servicos validam localmente com a chave publica, sem chamadas HTTP internas.
- **Redis Pub/Sub:** Eventos como `order_assigned` e `material_low_stock` sao publicados no Redis. O Notification Service assina e persiste notificacoes, empurrando via WebSocket.
- **RLS (Row-Level Security):** Técnicos so acessam OS atribuidas a eles, garantido no nivel do banco de dados via `SET LOCAL app.user_id`.
- **Triggers de Auditoria:** Triggers PL/pgSQL geram logs automaticos em `audit_logs` ao atualizar OS.
- **Rate Limiting:** Nginx limita 100 req/min global e 5 req/min para login.

---

## Stack Tecnologica

### Backend

| Camada | Tecnologia | Versao |
|--------|-----------|:------:|
| Linguagem | Python | 3.12+ |
| Framework Web | FastAPI | latest |
| ORM | SQLAlchemy (asyncpg) | 2.0 |
| Banco de Dados | PostgreSQL | 16 |
| Cache / Broker | Redis | 7 |
| Migrations | Alembic | latest |
| Validacao | Pydantic | v2 |
| Testes | Pytest + httpx | latest |
| Container | Docker Compose | 3.9 |
| API Gateway | Nginx | latest |

### Frontend

| Camada | Tecnologia | Versao |
|--------|-----------|:------:|
| Framework | React | 18 |
| Linguagem | TypeScript | 5.7+ |
| Build Tool | Vite | 6 |
| Icones | lucide-react | 0.468+ |
| HTTP | fetch nativo + Bearer JWT | — |
| Realtime | WebSocket nativo | — |
| Estilos | CSS puro (sem framework) | — |

### Infraestrutura

| Componente | Tecnologia |
|------------|-----------|
| Orquestracao | Docker Compose |
| Banco de dados | PostgreSQL 16 Alpine |
| Cache / Pub-Sub | Redis 7 Alpine |
| Gateway | Nginx (route matching + rate limiting) |
| Migrations | Alembic (Docker init container) |
| Seeds | Scripts Python (idempotentes) |

---

## Pre-requisitos

Para executar o projeto em outra maquina, voce precisa ter instalado:

| Software | Versao Minima | Como verificar |
|----------|:------------:|----------------|
| **Docker Desktop** | 4.x | `docker --version` |
| **Docker Compose** | v2.x | `docker compose version` |
| **Git** | 2.x | `git --version` |

> **Opcional (para desenvolvimento local):**
> - Node.js 20+ e npm 9+ (para rodar o frontend fora do Docker)
> - Python 3.12+ (para rodar testes localmente)

### Docker Desktop

1. Baixe e instale o [Docker Desktop](https://www.docker.com/products/docker-desktop/).
2. Abra o Docker Desktop e aguarde o icone ficar verde (engine rodando).
3. No Windows, certifique-se de que o WSL 2 esta habilitado (Docker Desktop usa WSL 2 por padrao).

---

## Instalacao do Zero

### Passo 1 — Clone o repositorio

```bash
git clone https://github.com/seu-usuario/manutech-saas.git
cd manutech-saas
```

### Passo 2 — Acesse o diretorio do backend

```bash
cd backend
```

### Passo 3 — Copie o arquivo de variaveis de ambiente

```bash
cp .env.example .env
```

> O `.env` ja esta configurado para funcionar com o Docker Compose. Nao e necessario alterar nada.

### Passo 4 — Suba toda a stack

```bash
docker compose up --build -d
```

Esse comando unico:

1. Constoi as imagens Docker de todos os servicos.
2. Sobe o PostgreSQL, Redis e Nginx.
3. Roda as migracoes do Alembic automaticamente.
4. Sobe os 6 microsserviços (auth, asset, order, inventory, finance, notification).
5. Executa o seed do admin (`admin / admin123`).
6. Executa o seed de dados demo (4 usuarios, 8 ativos, 10 materiais, 15 movimentacoes, 6 OS, 17 custos, 3 orcamentos).

### Passo 5 — Aguarde os containers ficarem saudaveis

```bash
docker compose ps
```

A coluna `STATUS` deve mostrar `Up (healthy)` para todos os servicos. Se algum estiver `Up` sem `(healthy)`, aguarde alguns segundos e execute novamente.

### Passo 6 — Acesse o sistema

Abra no navegador:

```
http://localhost/
```

> **IMPORTANTE:** Acesse `http://localhost/` (porta 80 via Nginx). NAO abra o arquivo HTML diretamente no navegador, pois as requisicoes serao bloqueadas por CORS.

### Passo 7 — Faca login

Use as credenciais do seed:

| Login | Senha | Perfil |
|-------|-------|--------|
| `admin` | `admin123` | admin |

---

## Credenciais

O seed automatico cria 5 usuarios para teste. Todos usam a senha `senha123456` (exceto o admin que usa `admin123`):

| Login | Senha | Perfil | Descricao |
|-------|-------|--------|-----------|
| `admin` | `admin123` | admin | Acesso total, gerencia usuarios |
| `carlos.mendes` | `senha123456` | supervisor | Gera OS, custos, orcamentos, atribui |
| `joao.silva` | `senha123456` | technician | Executa OS, registra movimentacoes |
| `marcos.pereira` | `senha123456` | technician | Executa OS, registra movimentacoes |
| `ana.costa` | `senha123456` | attendant | Registra OS, consulta equipamentos |

### Re-semear do zero

Se precisar resetar todos os dados demo:

```bash
docker compose down -v
docker compose up --build -d
```

O seed e idempotente — se os usuarios ja existirem, nao insere nada.

---

## Estrutura do Repositorio

```
manutech-saas/
├── backend/
│   ├── docker-compose.yml          # Orquestrador de containers
│   ├── .env.example                # Template de variaveis de ambiente
│   ├── seed_admin.py               # Seed do usuario admin
│   ├── seed_data.py                # Seed de dados demo
│   ├── requirements.txt            # Dependencias Python
│   ├── infra/
│   │   ├── migrations/             # Alembic + Dockerfile de migracoes
│   │   │   └── versions/           # Historico de alteracoes do banco
│   │   ├── nginx/                  # Configuracao do API Gateway
│   │   └── seed/                   # Dockerfile para seeds
│   ├── shared/                     # Biblioteca compartilhada
│   │   └── shared/
│   │       ├── auth/               # JWT decoding + dependencia de usuario
│   │       ├── db/                 # Engine, RLS, sessao assincrona
│   │       ├── redis/              # Cliente Redis + utilitarios Pub/Sub
│   │       ├── config.py           # Leitura de variaveis de ambiente
│   │       └── exceptions/         # Tratamento global de erros
│   ├── services/
│   │   ├── auth/                   # Servico de autenticacao e usuarios
│   │   ├── asset/                  # Servico de equipamentos
│   │   ├── order/                  # Servico de ordens de servico
│   │   ├── inventory/              # Servico de estoque
│   │   ├── finance/                # Servico financeiro
│   │   └── notification/           # Servico de notificacoes + WebSocket
│   └── tests/
│       ├── unit/                   # Testes unitarios
│       ├── e2e/                    # Testes End-to-End
│       ├── conftest.py             # Fixtures globais
│       └── Doc_teste.md            # Documentacao completa de testes
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts              # Proxy /api -> localhost:80
│   ├── .env                        # Variaveis de ambiente (versionado)
│   ├── .env.example
│   └── src/
│       ├── App.tsx                 # Roteamento, bootstrap, WebSocket
│       ├── styles.css              # Tema e componentes (CSS puro)
│       ├── types.ts                # Contratos compartilhados com a API
│       ├── utils.ts                # Utilitarios (formatCurrency, can(), etc.)
│       ├── services/
│       │   └── api.ts              # Cliente HTTP + refresh de token
│       ├── components/             # Componentes reutilizaveis
│       │   ├── Layout.tsx          # Sidebar, topbar, sino
│       │   ├── Modal.tsx
│       │   ├── Table.tsx
│       │   ├── StatCard.tsx
│       │   ├── Toast.tsx
│       │   └── Pagination.tsx
│       └── pages/                  # Paginas da aplicacao
│           ├── LoginPage.tsx
│           ├── DashboardPage.tsx
│           ├── OrdersPage.tsx
│           ├── AssetsPage.tsx
│           ├── InventoryPage.tsx
│           ├── MovementsPage.tsx
│           ├── FinancePage.tsx
│           ├── UsersPage.tsx
│           └── AuditPage.tsx
└── README.md                       # Este arquivo
```

---

## Perfis de Usuario e RBAC

### Matriz de Permissoes

| Funcao | Admin | Supervisor | Tecnico | Atendente |
|--------|:-----:|:----------:|:-------:|:---------:|
| **Dashboard** | Sim | Sim | Sim | Sim |
| **Criar OS** | Nao | Sim | Nao | Sim |
| **Editar OS** | Sim | Sim | Nao | Nao |
| **Atribuir tecnico** | Sim | Sim | Nao | Nao |
| **Iniciar OS** | Sim | Sim | Sim (proprias) | Nao |
| **Solicitar conclusao** | Sim | Sim | Sim (proprias) | Nao |
| **Concluir OS** | Sim | Sim | Nao | Nao |
| **Cancelar OS** | Sim | Sim | Nao | Nao |
| **Remover OS** | Sim | Sim | Nao | Nao |
| **Anexos** | Sim | Sim | Sim | Nao |
| **Equipamentos (CRUD)** | Sim | Sim | Nao | Nao |
| **Materiais (CRUD)** | Sim | Sim | Nao | Nao |
| **Registrar movimentacao** | Sim | Sim | Sim | Nao |
| **Listar movimentacoes** | Sim | Sim | Sim | Nao |
| **Custos e orcamentos** | Sim | Sim | Nao | Nao |
| **Relatorios e exportacao** | Sim | Sim | Nao | Nao |
| **Gerenciar usuarios** | Sim | Nao | Nao | Nao |
| **Auditoria (logs)** | Sim | Sim | Nao | Nao |
| **Notificacoes + WebSocket** | Sim | Sim | Sim | Sim |

> **Regra de hierarquia:** o admin tem todas as permissoes do supervisor. A diferenca esta apenas em "Gerenciar usuarios", que e exclusividade do admin.

### Descricao dos Perfis

- **Admin** — superusuario com acesso total ao sistema, inclusive gestao de usuarios.
- **Supervisor** — gestor operacional: cria e gerencia OS, atribui tecnicos, controla custos e orcamentos.
- **Tecnico** — executa OS atribuidas, registra movimentacoes de estoque, solicita conclusao. So ve proprias OS (RLS).
- **Atendente** — front desk: recebe chamados, cria OS, consulta equipamentos e materiais. Nao edita, nao atribui, nao cancela.

---

## Fluxo de Trabalho

### Ciclo de vida de uma OS

```
[Atendente]     ──cria──>  OS (Aberta)
                              │
[Supervisor]    ──atribui──>  OS (Aberta + Tecnico)
                              │
[Tecnico]       ──inicia──>   OS (Em andamento)
                              │
[Tecnico]       ──solicita conclusao──>  Notificacao para Supervisor/Admin
                              │
[Supervisor]    ──conclui──>  OS (Concluida)
```

### Transicoes de status

| Transicao | Quem pode |
|-----------|-----------|
| Aberta → Em andamento | Tecnico atribuido, supervisor ou admin |
| Em andamento → Concluida | Apenas supervisor ou admin |
| Qualquer → Cancelada | Supervisor ou admin (exige motivo) |

> O tecnico nunca finaliza diretamente — ele clica em "Solicitar conclusao", que envia uma notificacao ao supervisor/admin, quem decide concluir ou solicitar ajuste.

### Notificacoes em tempo real

Quando o supervisor atribui uma OS a um tecnico:
1. O evento `order_assigned` e publicado no Redis.
2. O Notification Service captura e persiste a notificacao.
3. O WebSocket empurra a notificacao para o tecnico conectado.
4. O sino no canto superior direito mostra o contador de nao lidas.

---

## Variaveis de Ambiente

### Backend (`backend/.env`)

O arquivo `.env` ja esta versionado no repositorio (projeto academico). O template e:

| Variavel | Descricao |
|----------|-----------|
| `POSTGRES_DB` | Nome do banco de dados |
| `POSTGRES_USER` | Usuario do PostgreSQL |
| `POSTGRES_PASSWORD` | Senha do PostgreSQL |
| `DATABASE_URL` | URL de conexao com o banco (container `db`) |
| `REDIS_PASSWORD` | Senha do Redis |
| `REDIS_URL` | URL de conexao com o Redis |
| `JWT_PRIVATE_KEY` | Chave privada RSA para assinatura de JWT |
| `JWT_PUBLIC_KEY` | Chave publica RSA para validacao de JWT |

### Frontend (`frontend/.env`)

| Variavel | Default | Descricao |
|----------|---------|-----------|
| `VITE_API_BASE_URL` | `/api/v1` | Prefixo HTTP para a API |
| `VITE_WS_BASE_URL` | (vazio) | URL do WebSocket (vazio = mesmo host) |

---

## Testes

### Executar testes

```bash
cd backend
python -m pytest
```

### Tipos de teste

| Tipo | Comando | Requisito |
|------|---------|-----------|
| Todos (unit + E2E) | `python -m pytest` | Docker rodando |
| Apenas unitarios | `python -m pytest tests/unit` | Nenhum |
| Apenas E2E | `python -m pytest tests/e2e` | Docker rodando |
| E2E de um servico | `python -m pytest tests/e2e/auth` | Docker rodando |

### Cobertura

A suite cobre:
- Autenticacao e controle de acesso (RBAC por papel)
- Fluxo completo de OS (criacao → atribuicao → execucao → conclusao/cancelamento)
- Ciclo de vida de movimentacoes de estoque
- Transicoes de status de orcamentos
- Validacao de campos e conflitos de unicidade
- Exportacao de relatorios

### Isolamento

Cada teste E2E roda dentro de uma transacao isolada com `SAVEPOINT` + `ROLLBACK`, garantindo que nenhum dado persista no banco. O rate limiter do Redis e limpo automaticamente entre testes.

---

## Troubleshooting

| Sintoma | Causa provavel | Solucao |
|---------|---------------|---------|
| `502 Bad Gateway` ao logar | Nginx cacheou IP de container reiniciado | `docker restart backend-nginx-1` |
| `Login ou senha incorretos` | Seeds nao rodaram | `docker compose logs seed-admin seed-data` |
| CORS / erro de rede no console | Abriu `index.html` direto no explorer | Acesse `http://localhost/` |
| Pagina em branco | Nginx nao subiu ou volume nao montou | `docker compose logs nginx` |
| Seed ja aplicado | Dados demo ja existem | `docker compose down -v && docker compose up --build -d` |
| WebSocket nao atualiza | Proxy sem `ws: true` | Verificar `vite.config.ts` |
| Container nao fica healthy | PostgreSQL ou Redis demorando | Aguarde 30s e rode `docker compose ps` novamente |

### Comandos uteis

```bash
# Ver status dos containers
docker compose ps

# Ver logs de um servico especifico
docker compose logs -f auth
docker compose logs -f order
docker compose logs -f nginx

# Reiniciar um servico
docker compose restart auth

# Parar tudo e limpar volumes
docker compose down -v

# Rebuild completo
docker compose down -v && docker compose up --build -d
```

---

## Aviso

Este projeto e um **MVP academico** sem dados reais. Senhas padrao, secrets e URLs no `.env` sao de desenvolvimento. O `.env` esta versionado porque se trata de ambiente academico, sem riscos de vazamento de dados reais.

Em ambiente de producao, mova o `.env` para o `.gitignore` e utilize um cofre de segredos (HashiCorp Vault, AWS SSM, Azure Key Vault, etc).

---

*MANUTECH SaaS — MVP Academico*
