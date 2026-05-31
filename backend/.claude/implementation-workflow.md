# Workflow de Implementação

## Regra de Ouro

**Nunca pule a fase de planejamento.**

Escrever código antes de entender o contrato completo gera retrabalho, viola RBAC e ignora side effects de triggers. O planejamento custa 5 minutos. O retrabalho custa horas.

---

## Fluxo Completo

### 1. Leitura de Contexto

Antes de qualquer coisa, leia:

- [ ] `CLAUDE.md` — entender o escopo completo
- [ ] `MANUTECH_API_Documentation_v2.md` — contrato da rota alvo
- [ ] `manutech_schema_v3.sql` — tabelas, colunas, constraints, triggers afetados
- [ ] O arquivo de regras específico do que vai implementar (ex: `redis-rules.md` se envolver eventos)

### 2. Identificar o Serviço e Camadas

Responder:
- Qual serviço é responsável por essa rota?
- Quais tabelas do banco são lidas/escritas?
- Algum trigger é disparado? O código precisa ler o valor atualizado depois?
- É necessário publicar evento Redis?
- Qual é o RBAC exato da rota?
- Existe RLS que precisa ser configurado?

### 3. Criar Plano de Implementação

Antes de escrever código, descrever brevemente:

```
Rota: POST /orders/:id/assign
Serviço: Order Service

Camadas afetadas:
  - Router: validate body (technician_id), checar roles [supervisor]
  - Service: validar technician (role=technician, status=active), fechar assignment ativo, criar novo, publicar Redis
  - Repository: get_active_assignment(), close_assignment(), create_assignment()
  - Schema: AssignRequest (technician_id: int), AssignResponse

Banco:
  - SELECT em users (verificar role e status do técnico)
  - UPDATE em order_assignments (fechar ativo anterior)
  - INSERT em order_assignments (novo ativo)
  - RLS necessário: sim (set_rls_context antes do INSERT)
  - Trigger disparado: não (assignments não têm trigger)

Redis:
  - Publicar em channel "order.assigned" após INSERT bem-sucedido

Erros esperados:
  - 404 TECHNICIAN_NOT_FOUND
  - 422 NOT_A_TECHNICIAN
  - 400 ORDER_CLOSED
```

### 4. Identificar Riscos

Pensar nos casos de borda:
- O técnico pode estar inativo?
- A OS pode estar cancelada/concluída?
- O mesmo técnico já está atribuído? (constraint `uq_assignment_active`)
- E se o Redis estiver fora do ar? (não bloquear o response — logar o erro e seguir)

### 5. Implementar na Ordem

```
models (SQLAlchemy) → schemas (Pydantic) → repository → service → router → testes
```

Não inverter a ordem. O schema define o contrato; o repository implementa o acesso; o service orquestra.

### 6. Testes

Para cada rota implementada, criar:

- [ ] Teste de sucesso (happy path)
- [ ] Teste de cada erro documentado (404, 400, 409, etc.)
- [ ] Teste de RBAC para cada role (permitido e negado)
- [ ] Teste de validação de campos obrigatórios

### 7. Review com Checklist

```
[ ] Rota bate com a documentação (método, path, status code)?
[ ] Request schema tem exatamente os campos documentados?
[ ] Response schema tem exatamente os campos documentados?
[ ] RBAC correto para todos os roles?
[ ] RLS configurado antes das queries?
[ ] Não está recalculando o que trigger já faz?
[ ] password_hash não exposto?
[ ] Credenciais via env vars?
[ ] Erros retornam o envelope {detail, code, field}?
[ ] Testes cobrem RBAC + regras de negócio?
[ ] Cobertura >= 80%?
[ ] .env.example atualizado se adicionou nova variável?
```

---

## Exemplos de Situações Que Exigem Pergunta ao Dev/Operador

- "A documentação diz que o campo X é opcional, mas o banco tem NOT NULL. O que prevalece?"
- "A rota não está documentada. Devo criar?"
- "O ENUM do banco tem um valor não listado na docs. Qual usar?"
- "O arquivo de storage para uploads é Supabase Storage ou outro serviço?"

**Nesses casos: parar, não assumir, perguntar.**

---

## Anti-Patterns — Nunca Fazer

| Anti-pattern | Consequência |
|-------------|-------------|
| Criar rota não documentada | Viola o contrato da API |
| Calcular `total_cost` no Python | Divergência com o trigger do banco |
| Fazer `SELECT *` | Expõe dados sensíveis, performance ruim |
| Hardcodar credenciais | Vazamento de segurança |
| Chamar outro serviço via HTTP interno | Acoplamento, viola arquitetura |
| Pular RLS em queries | Vazamento de dados entre usuários |
| Ignorar soft delete | Exclusão irreversível de dados |
| Logar tokens ou senhas | Vulnerabilidade de segurança |
