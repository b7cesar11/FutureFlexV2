# FUTURE FLEX V2 — Arquitetura Técnica (Proposta para Aprovação)

Stack: React (PWA, mobile-first, tema escuro) + FastAPI + MongoDB (motor de replica set → transações ACID multi-documento).
Auth: JWT próprio (e-mail/senha, bcrypt) **+** Google gerenciado pela Emergent (mesmo usuário, `auth_providers[]`).
IA: GPT-5.5 via Universal Key da Emergent. Idioma pt-BR, moeda BRL.

---

## 1. Camadas (regra inviolável)

```
Frontend (React)         → só renderiza e chama API. ZERO regra financeira.
  ↓ HTTP /api
API Layer (routers)      → validação de payload (Pydantic), auth, ownership.
  ↓
Application Services     → casos de uso, orquestração, transaction boundary.
  ↓
Domain (puro, sem I/O)   → regras: parcelamento, status, ciclo de fatura,
                           recorrência, projeção, dinheiro livre, score.
  ↓
Repositories             → único lugar que fala com MongoDB (Motor async).
  ↓
MongoDB
```

- `domain/` é **puro Python testável sem banco** (funções determinísticas).
- Nenhum valor derivado (total do mês, dinheiro livre, status) é gravado como campo mutável de UI; é calculado pelo domínio ou materializado por um serviço idempotente.
- Frontend consome *view models* prontos (ex.: `GET /api/months/2026-08` retorna o mês inteiro já agrupado e calculado) — elimina cálculo duplicado entre Dashboard e Compromissos.

## 2. Modelo de Dados MongoDB (não é tradução 1:1 do Postgres)

Princípios de modelagem:
- **Embed** o que é lido junto e não cresce sem limite (regra de recorrência, snapshot de categoria, linhas de fatura pequenas → não; ver abaixo).
- **Referência** para tudo que é consultado por si só ou cresce (ocorrências, transações).
- **Coleção de ocorrências única e polimórfica** (`occurrences`): é a espinha dorsal do calendário financeiro. Parcela, cobrança de assinatura, despesa fixa do mês, fatura, terceiro e receita futura são todos ocorrências. Isso resolve o problema estrutural do sistema antigo (uma tabela de ocorrência por módulo → telas divergentes).
- Todo documento: `_id: ObjectId` (serializado como `str` via `PyObjectId`), `user_id`, `created_at`, `updated_at` (UTC).

### 2.1 Coleções

| Coleção | Conteúdo chave | Notas |
|---|---|---|
| `users` | email, password_hash?, auth_providers[], profile{}, preferences{} | perfil e preferências embutidos (1:1) |
| `people` | name, phone, notes, avatar_color | terceiros/pessoas |
| `accounts` | name, type(checking/savings/cash/wallet), institution, opening_balance, current_balance, archived | `current_balance` só muda dentro de transação atômica |
| `credit_cards` | name, brand, limit, closing_day, due_day, default_account_id, color | |
| `invoices` | card_id, period{year,month}, closing_date, due_date, total, paid_amount, status | uma por cartão/ciclo; itens **não** embutidos |
| `categories` | name, kind(expense/income), icon, color, parent_id, is_system | seed pt-BR |
| `commitments` | **entidade central** (ver §3) | |
| `occurrences` | **espinha dorsal** (ver §4) | |
| `subscriptions` | name, amount, periodicity, billing_day, payment{card_id\|account_id}, category_id, start/end, status, commitment_id | domínio próprio; gera occurrences via commitment |
| `income_sources` | name, amount, recurrence{}, account_id, status, commitment_id | |
| `third_party_relationships` | person_id, direction(receivable/payable), total, installments, card_id?, status, commitment_id | |
| `transactions` | **fato real** (ver §5) | |
| `goals` / `goal_contributions` | target, current, deadline, monthly_suggestion | |
| `investments` / `investment_transactions` | type, institution, invested, current_value / contribution\|withdrawal | visão patrimonial |
| `budgets` | category_id, period, limit | |
| `simulations` | payload, resultado, `is_simulation: true` | nunca toca em occurrences reais |
| `ai_conversations` | messages[], context_snapshot_ref | |
| `alerts` | type, severity, month, payload, read_at | gerados por serviço, não persistem cálculo |
| `idempotency_keys` | key, scope, result_ref, expires_at | garante §7 |
| `audit_logs` | user_id, action, entity, before/after resumo, error | observabilidade §54 |

### 2.2 Índices

```
users:        {email:1} unique sparse; {google_sub:1} unique sparse
occurrences:  {user_id:1, competence:1, status_hint:1}        ← query principal do mês
              {user_id:1, due_date:1}
              {user_id:1, commitment_id:1, sequence:1}
              {user_id:1, invoice_id:1}
              {user_id:1, person_id:1}
              {user_id:1, commitment_id:1, competence:1} UNIQUE  ← idempotência de recorrência
transactions: {user_id:1, date:-1}; {user_id:1, account_id:1, date:-1};
              {user_id:1, occurrence_id:1} unique sparse
invoices:     {user_id:1, card_id:1, "period.year":1, "period.month":1} UNIQUE
commitments:  {user_id:1, type:1, status:1}; {user_id:1, frozen:1}
accounts/cards/categories/people: {user_id:1, name:1}
idempotency_keys: {key:1} unique + TTL em expires_at
```

`competence` é string `"YYYY-MM"` — ordenável, indexável, sem armadilha de timezone.

## 3. `commitments` — entidade central

```jsonc
{
  "_id": ObjectId, "user_id": ObjectId,
  "type": "purchase_installment|fixed_expense|subscription|loan|financing|
           credit_card_invoice|third_party_payable|third_party_receivable|
           recurring_income|other",
  "direction": "outflow|inflow",
  "description": "iPhone 15",
  "total_amount": 3600.00,
  "installments_total": 12,            // null = recorrência sem fim
  "installment_amount": 300.00,
  "recurrence": { "frequency":"monthly|weekly|yearly|once",
                  "day_of_month":5, "interval":1,
                  "start_competence":"2026-08", "end_competence":"2027-07" },
  "payment_method": "credit_card|account|cash",
  "credit_card_id": ObjectId|null,
  "default_account_id": ObjectId|null,   // SUGESTÃO, não vínculo rígido (§14)
  "category_id": ObjectId, "person_id": ObjectId|null,
  "source": { "module":"subscription|third_party|income|purchase|manual",
              "ref_id": ObjectId|null },
  "frozen": false, "frozen_at": null,
  "status": "active|completed|cancelled",
  "materialized_until": "2027-07"        // controle de geração incremental
}
```

Regra: **nada financeiro nasce fora de um commitment.** Assinatura, despesa fixa, receita, terceiro e compra parcelada criam seu commitment na mesma transação (§51 garantido por construção).

## 4. `occurrences` — o calendário financeiro

```jsonc
{
  "_id": ObjectId, "user_id": ObjectId, "commitment_id": ObjectId,
  "type": <herdado do commitment>, "direction": "outflow|inflow",
  "description": "iPhone 15 4/12",
  "amount": 300.00,
  "due_date": ISODate, "competence": "2026-08",
  "sequence": 4, "sequence_total": 12,      // parcela 4/12
  "invoice_id": ObjectId|null,              // quando cai em fatura
  "credit_card_id": ObjectId|null, "person_id": ObjectId|null,
  "category_id": ObjectId,
  "paid_amount": 0, "paid_at": null,
  "transaction_ids": [],                    // pagamentos reais
  "frozen": false, "cancelled": false,
  "origin_group": "cards|installments|fixed|subscriptions|financing|
                   loans|third_parties|income"   // agrupamento §23
}
```

**Status é DERIVADO (§11), nunca campo manual:**

```
cancelled            → cancelled
frozen               → frozen
paid_amount >= amount→ paid
today > due_date     → overdue
due_date no mês atual→ due
senão                → future
```
Persistimos apenas `status_hint` (paid/open/cancelled/frozen) para permitir índice; o status apresentado é sempre recalculado pelo domínio a partir de data + pagamento.

## 5. Compromisso ≠ Transação (§9)

`transactions` = fato consumado, único lugar que move `accounts.current_balance`:

```jsonc
{ "type":"expense|income|transfer|invoice_payment|commitment_payment",
  "amount":300, "date":ISODate, "account_id":ObjectId,   // conta ESCOLHIDA no pagamento
  "category_id":ObjectId, "occurrence_id":ObjectId|null,
  "invoice_id":ObjectId|null, "credit_card_id":ObjectId|null,
  "person_id":ObjectId|null, "description":"", "source":"manual|nlp|whatsapp|api" }
```

Compra no cartão **não** gera transaction e **não** debita conta: gera commitment + occurrences vinculadas a `invoices`. Só o **pagamento da fatura** gera `transaction(type=invoice_payment)` que debita a conta (§12).

## 6. Fronteiras de transação (MongoDB multi-document, `session.start_transaction`)

| Caso de uso | Coleções tocadas atomicamente |
|---|---|
| `pay_occurrence` | occurrences, transactions, accounts, invoices, commitments(status) |
| `pay_invoice` | invoices, occurrences(itens→paid), transactions, accounts |
| `create_installment_purchase` | commitments, occurrences(N), invoices(upsert dos ciclos) |
| `create_subscription` | subscriptions, commitments, occurrences |
| `create_third_party` | third_party_relationships, commitments, occurrences, invoices? |
| `freeze/unfreeze_commitment` | commitments, occurrences (§25, atômico) |
| `materialize_recurrences` | occurrences, commitments.materialized_until |
| `delete/cancel` | commitments, occurrences, (transactions preservadas) |
| `transfer` | 2× accounts, transactions |

Nenhuma sequência de mutations no frontend. Todo caso de uso acima = **1 endpoint, 1 transação**.

## 7. Idempotência (§42)

- Índice único `{user_id, commitment_id, competence}` em occurrences → recorrência nunca duplica.
- Índice único de `invoices` por cartão+período → `get_or_create_invoice` seguro.
- Header opcional `Idempotency-Key` em POSTs de pagamento, gravado em `idempotency_keys`; replay retorna o mesmo resultado.
- Materialização é **incremental e determinística**: gera de `materialized_until+1` até `hoje+18 meses`.

## 8. Regras de domínio centralizadas (`backend/domain/`)

- `installments.py` — divide valor em N parcelas com ajuste de centavos na 1ª (soma exata = total).
- `recurrence.py` — datas determinísticas, clamp de dia (31 → último dia do mês).
- `card_cycle.py` — dada `purchase_date`, `closing_day`, `due_day` → competência da 1ª parcela e vencimentos seguintes.
- `status.py` — regra única de status (§11).
- `projection.py` — saldo atual + receitas − compromissos por mês; detecta "parcelas que terminam" e quanto libera.
- `free_money.py` — dinheiro livre = saldo − compromissos pendentes do mês (§21).
- `health_score.py` — 0–100 **explicável**: retorna score + componentes com peso, valor e frase.
- `simulation.py` — aplica deltas sobre uma cópia em memória da projeção; nunca escreve.

## 9. API (todas com prefixo `/api`, JWT obrigatório, ownership por `user_id`)

```
auth:        POST /auth/register /auth/login /auth/google/session, GET /auth/me
cadastros:   /accounts /credit-cards /categories /people        (CRUD)
motor:       POST /commitments  (cria + materializa)
             GET  /commitments/:id  (detalhe §24: parcela atual, restante, próximos meses)
             POST /commitments/:id/freeze | /unfreeze
             GET  /occurrences?competence=&group=&status=
             POST /occurrences/:id/pay   { account_id, date, amount }
faturas:     GET /invoices?card_id=&competence=   POST /invoices/:id/pay
módulos:     /subscriptions /income-sources /third-parties /goals /investments /budgets
transações:  GET /transactions (filtros §37)  POST /transactions
visões:      GET /months/:competence     ← VIEW MODEL único da tela Compromissos+Dashboard
             GET /projection?months=12
             GET /dashboard
             GET /reports/monthly/:competence
             GET /alerts
IA:          POST /ai/ask   POST /ai/parse (linguagem natural → intenção, sem gravar)
             POST /ai/confirm (grava após confirmação do usuário)
             POST /simulations
ingress:     POST /ingest/message  { channel: app|web|whatsapp|api, text }  ← §33
```

`GET /months/:competence` é a fonte única exibida por qualquer tela: `{income_expected, committed, paid, pending, free_projected, progress_pct, groups[{key,label,total,items[]}], insights[]}`.

## 10. Frontend

- React + Tailwind + shadcn/ui, design system próprio (tema escuro fintech), `MonthContext` global (mês selecionado) e React Query para cache/paginação.
- Mobile: bottom nav (Início, Compromissos*, **+ Registrar** central, Cartões, Mais) — Compromissos destacado.
- Desktop: sidebar completa + dashboard em grid aproveitando largura, tabelas e gráficos (Recharts).
- PWA: manifest, service worker (cache de shell + offline read-only), instalável.
- Zero cálculo financeiro no cliente: apenas formatação BRL/datas.

## 11. Segurança

JWT (access + refresh), bcrypt, todo repositório filtra por `user_id` obrigatoriamente (nenhuma query sem ele), validação de ownership de cada `*_id` referenciado no payload antes de gravar. Equivalente funcional de RLS na camada de repositório.

## 12. Testes de negócio (§52)

pytest sobre o domínio + integração: 12 parcelas; assinatura mensal; despesa fixa futura; compra no cartão não debita conta e pagamento de fatura debita; terceiro a receber/pagar; pagamento usa a conta escolhida; congelamento remove dos totais ativos; simulação não altera dados; materialização 2× não duplica.

## 13. Plano de implementação (fases entregáveis)

| Fase | Escopo |
|---|---|
| 1 | Fundação: auth (JWT + Google), design system, layout responsivo/PWA, contas, categorias, cartões, pessoas |
| 2 | Motor: commitments + occurrences + parcelamento + status + transações + pagamento atômico |
| 3 | Cartões: ciclos, faturas, compras parceladas, pagamento de fatura |
| 4 | **Compromissos do Mês** (tela principal) + agrupamento + detalhe + congelamento |
| 5 | Recorrências: despesas fixas, assinaturas, receitas |
| 6 | Terceiros (a pagar/receber, cartão de terceiro) |
| 7 | Dashboard, projeção 12 meses, dinheiro livre, saúde financeira explicável |
| 8 | Metas e investimentos |
| 9 | IA (GPT-5.5): análise contextual, perguntas, linguagem natural, simulador |
| 10 | Relatórios mensais, alertas, tendências |
| 11 | WhatsApp sobre a camada `/ingest/message` |

## 14. Riscos arquiteturais e mitigação

1. **Transações no Mongo exigem replica set** → VERIFICADO: o MongoDB deste ambiente está em modo *standalone*, portanto transações multi-documento não estão disponíveis hoje. Plano na Fase 1: converter o mongod para *single-node replica set* (`replSet rs0` + `rs.initiate()`) via supervisor, o que habilita transações ACID reais sem mudar a URL de conexão. Se a conversão não for viável, o fallback é um **Unit of Work com compensação**: cada caso de uso escreve um `audit_logs` de intenção, aplica as escritas na ordem segura (occurrence → transaction → saldo/fatura) e desfaz em erro, com job de reconciliação de saldos a partir de `transactions`.
2. **Explosão de occurrences** em recorrência infinita → janela rolante de 18 meses + materialização incremental idempotente.
3. **Divergência de saldo** → `accounts.current_balance` alterado exclusivamente dentro de transações; job de reconciliação a partir de `transactions`.
4. **Timezone** → tudo UTC no banco; `competence` string; exibição em America/Sao_Paulo.
5. **Custo/latência de IA** → IA recebe *snapshot agregado* (nunca dump bruto), com cache por mês.
6. **Ciclo de fatura em dia de virada** → regra única em `card_cycle.py`, coberta por testes.

---

### Aguardando aprovação
Confirme (ou aponte ajustes) e eu inicio pela Fase 1 + Fase 2.
