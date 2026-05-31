# Code Review — Checklist

Use este checklist antes de finalizar **qualquer implementação**.  
Se qualquer item falhar, não considere a tarefa concluída.

---

## 1. Contrato de API

- [ ] O método HTTP está correto (GET/POST/PUT/PATCH/DELETE)?
- [ ] O path está exatamente igual à documentação?
- [ ] O status code de sucesso está correto (200/201/204)?
- [ ] Todos os campos do request body estão documentados (nenhum inventado)?
- [ ] Todos os campos do response estão documentados (nenhum inventado)?
- [ ] Campos opcionais estão corretamente marcados como `Optional`?
- [ ] A paginação está implementada nas rotas de listagem?
- [ ] O envelope de erro `{detail, code, field}` é usado em todos os erros?
- [ ] Os códigos de erro (SNAKE_CASE) são os documentados?

## 2. Banco de Dados

- [ ] As colunas usadas existem no `manutech_schema_v3.sql`?
- [ ] Os ENUMs usados existem no schema (nenhum inventado)?
- [ ] As constraints do banco são respeitadas no código?
- [ ] Não está usando `SELECT *` em nenhuma query?
- [ ] Migrations Alembic foram criadas para qualquer DDL novo?
- [ ] `set_rls_context()` é chamado antes das queries em rotas autenticadas?
- [ ] Não está recalculando valores que triggers do banco já calculam automaticamente?
- [ ] Soft delete é usado (nunca DELETE físico, exceto notifications)?

## 3. RBAC e Segurança

- [ ] A dependency `require_roles([...])` está na rota com os roles corretos?
- [ ] Os roles permitidos batem exatamente com a tabela de RBAC do CLAUDE.md?
- [ ] `password_hash` não aparece em nenhum schema de response?
- [ ] Nenhuma credencial hardcoded (keys, passwords, tokens)?
- [ ] Todas as variáveis sensíveis vêm de variáveis de ambiente?
- [ ] Uploads validam MIME type antes de salvar?
- [ ] Uploads validam tamanho (≤ 20 MB) antes de salvar?
- [ ] `file_path` de uploads usa UUID gerado server-side?

## 4. Arquitetura

- [ ] Router é fino (sem lógica de negócio, sem SQL direto)?
- [ ] Service não importa nada de FastAPI (`Request`, `Response`, etc.)?
- [ ] Repository não contém regras de negócio?
- [ ] Services não chamam outros serviços via HTTP?
- [ ] Eventos Redis são publicados **após** commit bem-sucedido, não antes?

## 5. Redis

- [ ] Cache tem TTL definido (nunca cache sem expiração)?
- [ ] Eventos publicados usam apenas os channels documentados?
- [ ] Payload dos eventos tem os campos mínimos documentados?
- [ ] Falha no Redis não bloqueia o response (tratar exceção e logar)?

## 6. Testes

- [ ] Happy path testado?
- [ ] Todos os erros documentados têm teste correspondente?
- [ ] RBAC testado para pelo menos 2 roles (um com acesso, um sem)?
- [ ] Campos obrigatórios ausentes geram 422?
- [ ] Cobertura do serviço está ≥ 80%?

## 7. Docker e DevOps

- [ ] `Dockerfile` do serviço existe e tem healthcheck?
- [ ] `.env.example` está atualizado com novas variáveis adicionadas?
- [ ] Nova variável de ambiente está documentada em `env-guide.md`?
- [ ] `docker-compose.yml` referencia o serviço corretamente?

---

## Resultado

| Todos os itens OK | Pode finalizar ✅ |
| Algum item falhou | Corrigir antes de finalizar ❌ |

Não negocie com o checklist. Cada item existe por uma razão documentada.
