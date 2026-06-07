# MANUTECH — Frontend

SPA em **React + TypeScript + Vite** que consome a API REST do MANUTECH.
Este projeto é a camada de apresentação do MVP acadêmico — todos os dados
reais vivem no backend (`/backend`) que sobe via Docker (PostgreSQL + Redis +
Nginx + 6 microsserviços FastAPI).

---

## 1. Stack

| Camada | Tecnologia |
| --- | --- |
| Build / dev server | Vite 6 |
| Framework | React 18 + TypeScript 5 |
| Ícones | lucide-react |
| HTTP | `fetch` nativo + `Bearer` JWT em `localStorage` |
| Realtime | WebSocket nativo (sino de notificações) |
| Estilo | CSS puro em `src/styles.css` (sem Tailwind, sem libs de UI) |

> Nenhuma dependência de UI pesada foi proposital — o protótipo é HTML semântico + classes utilitárias.

---

## 2. Pré‑requisitos

| O que | Versão |
| --- | --- |
| Node.js | **20.x LTS** (recomendado) ou 18.18+ |
| npm | 9+ (vem com o Node 20) |
| Backend MANUTECH | rodando e acessível (ver `../backend/README.md`) |

> Não é necessário subir banco de dados nem Redis localmente — tudo é
> responsabilidade do backend via `docker-compose up`.

---

## 3. Variáveis de ambiente

O arquivo `.env.example` é versionado. Copie para `.env` e ajuste se necessário:

```ini
VITE_API_BASE_URL=/api/v1
VITE_WS_BASE_URL=
```

| Variável | Default | Significado |
| --- | --- | --- |
| `VITE_API_BASE_URL` | `/api/v1` | Prefixo HTTP. Em dev o Vite faz proxy de tudo que começa com `/api` para `http://localhost:80` (o Nginx do docker‑compose). Em produção o mesmo prefixo é resolvido pelo Nginx no mesmo host. |
| `VITE_WS_BASE_URL` | `""` (vazio) | URL do WebSocket. **Deixe vazio** para que o frontend use o mesmo host da página (`ws(s)://<host>/api/v1/notifications/ws`). Preencha apenas se o WS estiver em host/porta diferentes (ex.: `ws://notif.example.com`). |

> ⚠️ O arquivo `.env` está versionado **apenas porque o projeto é acadêmico
> e não há dados reais** (ver aviso no rodapé do `../README.md` raiz).
> Em projeto real, adicione `.env` ao `.gitignore`.

---

## 4. Subir o backend (pré‑requisito)

Em outro terminal, dentro de `../backend`:

```bash
docker-compose up --build -d
docker-compose ps   # espere todos os serviços com status "Up (healthy)"
```

Credenciais semeadas pelo `seed_admin.py` (criado automaticamente no primeiro
`up` se o usuário admin ainda não existir):

| Login | Senha | Perfil |
| --- | --- | --- |
| `admin` | `admin123` | `admin` |

---

## 5. Instalação e execução do frontend

```bash
cd frontend
npm install
npm run dev
```

O Vite sobe em <http://localhost:5173>.

O proxy (`vite.config.ts`) já encaminha tudo que começa com `/api` (HTTP **e
WebSocket**, graças ao `ws: true`) para `http://localhost:80` (Nginx do
docker‑compose). Portanto não há CORS nem mistura de portas.

### Build de produção

```bash
npm run build      # gera ./dist
npm run preview    # serve ./dist localmente em http://localhost:4173
```

> O conteúdo de `dist/` é estático — pode ser servido por qualquer CDN ou
> copiado para o Nginx do backend (o `docker-compose.yml` do backend já
> está preparado para servir `./tests/frontend` como placeholder; troque
> para `./dist` em produção real).

---

## 6. Smoke test (passo a passo para validar o MVP)

1. **Login**
   - Abra <http://localhost:5173>
   - Login: `admin` / Senha: `admin123`
   - Você verá o **Dashboard operacional** com cards de OS e tabela de ordens críticas

2. **Equipamentos** (módulo `Equipamentos`)
   - Clique em **Cadastrar equipamento** → preencha `Nome = Bomba d'água 01` → Salvar
   - Confirme o registro na tabela (status `Ativo`)

3. **Materiais** (módulo `Materiais`)
   - Cadastre `Parafuso M10` com preço `R$ 0,50` e mínimo `10`
   - Use os botões `+` / `–` da linha para registrar uma entrada e uma saída rápida (1 un. cada)

4. **Movimentações** (módulo `Movimentações`)
   - Filtre por `Tipo: Saída` — a saída que você acabou de fazer deve aparecer

5. **Ordens de serviço** (módulo `Ordens de serviço`)
   - Clique em **Nova ordem de serviço**
   - Cliente: `Indústria XPTO`, Localização: `Galpão 3`, escolha o equipamento cadastrado
   - Salve → a OS aparece com status `Aberta` e código `OS-001`
   - Edite a OS → atribua um técnico (crie um usuário técnico antes em **Usuários** se ainda não existir) → mude o status para `Em andamento`
   - Anexe um PDF/imagem (≤ 20 MB) na seção **Anexo técnico** → salve → reabra a OS → o anexo aparece na seção **Anexos da OS** com botão de download
   - Cancele a OS pelo ícone `🚫` → modal pede o **motivo** (obrigatório pelo backend) → confirme

6. **Histórico por equipamento** (módulo `Equipamentos`)
   - Clique no ícone de lista na linha do equipamento → veja todas as OS vinculadas

7. **Custos e finanças** (módulo `Custos e finanças`)
   - **Lançar custo** → escolha a OS, preencha descrição e valor → Salvar
   - **Novo orçamento** → preencha cliente, adicione 2 itens → Salvar
   - Status do orçamento começa em `Rascunho`; clique no botão de envio (`✉`) → vai para `Enviado`; depois em `✓` → `Aprovado`
   - **Exportar Excel / PDF** baixa um arquivo com o resumo financeiro

8. **Usuários** (módulo `Usuários`, só visível para `admin`)
   - Cadastre um usuário `Técnico` para atribuir OS no passo 5
   - Edite o perfil e ative/desative

9. **Auditoria** (módulo `Auditoria`)
   - Selecione uma OS → veja o histórico persistido vindo do backend (`GET /orders/:id/history`)
   - Mais abaixo aparecem os eventos sintéticos da sessão atual (criação, atualização, cancelamento, etc.)

10. **Sino de notificações** (canto superior direito)
    - Dispare qualquer mudança de status — uma notificação é publicada via Redis no backend e empurrada por WebSocket (`/api/v1/notifications/ws?token=…`)
    - O contador de não lidas deve subir

11. **Logout**
    - Botão **Sair** na barra inferior do sidebar

---

## 7. Papéis (RBAC)

A matriz abaixo é a fonte de verdade **do frontend**. O backend enforça
listas de papéis idênticas em `require_roles([...])`.

| Módulo / ação | `admin` | `supervisor` | `attendant` | `technician` |
| --- | :---: | :---: | :---: | :---: |
| Dashboard | ✓ | ✓ | ✓ | ✓ |
| **Listar** ordens | ✓ | ✓ | ✓ (todas) | só as dele (RLS) |
| **Criar** ordem de serviço | ✓ | ✓ | ✓ | ✗ |
| **Editar** OS / atribuir técnico | ✓ | ✓ | ✗ | ✗ |
| **Cancelar** OS (com motivo) | ✓ | ✓ | ✗ | ✗ |
| **Remover** OS (soft delete) | ✓ | ✓ | ✗ | ✗ |
| **Mudar status** na state machine | ✓ | ✓ | ✗ | ✓ (próprias) |
| **Anexar** arquivo à OS | ✓ | ✓ | ✗ | ✓ |
| Listar equipamentos | ✓ | ✓ | ✓ | ✓ |
| **CRUD** de equipamentos | ✓ | ✓ | ✗ | ✗ |
| Listar materiais | ✓ | ✓ | ✓ | ✓ |
| **CRUD** de materiais | ✓ | ✓ | ✗ | ✗ |
| **Registrar** movimentação de estoque | ✓ | ✓ | ✗ | ✓ |
| **Listar** movimentações | ✓ | ✓ | ✗ | ✓ |
| Relatório consolidado / exportar | ✓ | ✓ | ✗ | ✗ |
| **Lançar / editar / remover** custo | ✓ | ✓ | ✗ | ✓ (lança) |
| **CRUD** de orçamentos | ✓ | ✓ | ✗ | ✗ |
| **Listar / cadastrar / editar / ativar‑inativar** usuários | ✓ | ✗ | ✗ | ✗ |
| **Auditoria (logs)** | ✓ | ✓ | ✗ | ✗ |
| Notificações + WebSocket | ✓ | ✓ | ✓ | ✓ |

> **Atendente** é o "front desk" da operação: recebe a chamada, abre a OS,
> consulta o catálogo de equipamentos e materiais. Ele **não edita, não
> atribui técnico, não cancela, não vê custos nem orçamento** — isso é
> responsabilidade do supervisor. Justificativa: separar claramente o
> registro da OS da gestão da OS.

> **Supervisor** é o gestor operacional. Pode tudo, **exceto** mexer em
> usuários e em perfis acima do seu. **Admin** é o superusuário — pode
> tudo, inclusive promover alguém a supervisor/admin.

---

## 8. Estrutura de pastas

```
frontend/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts          # proxy /api → http://localhost com ws: true
├── .env / .env.example
├── README.md               # este arquivo
└── src/
    ├── main.tsx
    ├── App.tsx             # roteamento por módulo, bootstrap, WebSocket
    ├── styles.css          # tema e componentes (CSS puro)
    ├── types.ts            # contratos compartilhados com a API
    ├── utils.ts            # formatCurrency, formatDate, can(), labels PT‑BR
    ├── services/
    │   └── api.ts          # cliente HTTP + download de arquivo + refresh de token
    ├── components/
    │   ├── Layout.tsx      # sidebar, topbar, sino
    │   ├── Modal.tsx
    │   ├── Table.tsx
    │   ├── StatCard.tsx
    │   ├── Toast.tsx
    │   ├── LoadingState.tsx
    │   └── EmptyState.tsx
    └── pages/
        ├── LoginPage.tsx
        ├── DashboardPage.tsx
        ├── OrdersPage.tsx       # OS + cancelar com motivo + anexos
        ├── AssetsPage.tsx       # equipamentos + histórico de OS por equipamento
        ├── InventoryPage.tsx    # materiais
        ├── MovementsPage.tsx    # movimentações de estoque
        ├── FinancePage.tsx      # custos + orçamentos + exportar
        ├── UsersPage.tsx        # admin only
        └── AuditPage.tsx        # histórico por OS + eventos da sessão
```

---

## 9. Endpoints consumidos (referência rápida)

Cobertura por tela:

| Tela | Rotas que alimentam |
| --- | --- |
| Login | `POST /auth/login` |
| Dashboard | `GET /orders/stats` · `GET /notifications/unread-count` (via WS) |
| Ordens de serviço | `GET /orders` · `POST /orders` · `PUT /orders/:id` · `PATCH /orders/:id/status` · `PATCH /orders/:id/assign` · `DELETE /orders/:id` · `GET /orders/:id/history` · `GET /orders/:id/attachments` · `POST /orders/:id/attachments` · `GET /orders/:id/attachments/:aid/download` |
| Equipamentos | `GET /assets` · `POST /assets` · `PUT /assets/:id` · `PATCH /assets/:id/status` · `GET /assets/:id/orders` |
| Histórico de OS | `GET /orders/:id/history` (na tela de Auditoria) |
| Materiais | `GET /materials` · `POST /materials` · `PUT /materials/:id` · `PATCH /materials/:id/status` |
| Movimentações | `POST /movements` · `GET /movements` |
| Custos | `GET /costs` · `POST /costs` · `PUT /costs/:id` · `DELETE /costs/:id` |
| Orçamentos | `GET /budgets` · `POST /budgets` · `GET /budgets/:id` · `PUT /budgets/:id` · `PATCH /budgets/:id/status` |
| Relatórios | `GET /reports/financial` · `GET /reports/financial/export?format=excel|pdf` |
| Usuários | `GET /users` · `POST /users` · `PUT /users/:id` · `PATCH /users/:id/status` |
| Sino | `GET /notifications` · `GET /notifications/unread-count` (via WS) · `WS /api/v1/notifications/ws?token=…` |

---

## 10. Padrões de código

- **Sem comentários** no código (regra do projeto — código deve se explicar).
- Estilo: 2 espaços, aspas duplas, sem `;` em ponto‑e‑vírgula final, `function` declarada com `function`, `import` em ordem alfabética por bloco.
- Componentes funcionais com hooks. Sem classes, sem Redux, sem Context API global — estado vive em `App.tsx` e é passado por props (proposital, dado o tamanho do MVP).
- Erros do backend (4xx/5xx) são convertidos em `Error(message)` e caem no toast vermelho do `App.tsx:onToast`.
- Acessibilidade mínima: `aria-label` em todos os `icon-button`, foco visível via `:focus` no `styles.css`.

---

## 11. Troubleshooting

| Sintoma | Causa provável | Solução |
| --- | --- | --- |
| Login retorna `401` | Backend não está rodando ou `.env` errado | `docker-compose ps` no diretório `backend` e revise `VITE_API_BASE_URL` |
| Login retorna `403 Permissão insuficiente` ao criar OS | Versão antiga do backend (sem `admin` em `POST /orders`) | Suba o backend novo (`docker-compose up --build -d`) |
| Sino de notificações não atualiza em tempo real | WebSocket barrado no proxy | Verifique se o `vite.config.ts` tem `ws: true` no proxy de `/api` |
| `R$` aparece com ponto/ vírgula errada | Cache antigo do build | `rm -rf frontend/dist && npm run build` |
| Tela de **Auditoria** vazia | OS selecionada não tem histórico | Selecione uma OS que teve mudança de status; o backend só popula o log após alguma ação |
| `Erro 500` ao exportar PDF | Serviço de finanças não está saudável | `docker-compose logs finance` |

---

## 12. Aviso

> Este projeto é **acadêmico**. Nenhuma das credenciais versionadas (em
> `.env`, no `seed_admin.py` ou neste README) representa dados reais. Não
> reutilize estas chaves em qualquer ambiente que não seja o de
> desenvolvimento local.
