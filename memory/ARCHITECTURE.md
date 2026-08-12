# FUTURE FLEX V2 — Arquitetura Técnica v2 (revisão para aprovação final)

Stack: React 19 + Tailwind (PWA, mobile-first, tema escuro) · FastAPI + Motor (async) · MongoDB 7.0 **single-node replica set `rs0`** · Auth JWT + Google (Emergent) · IA GPT-5.5 (Universal Key) · pt-BR / BRL.

---

## 0. VALIDAÇÃO TÉCNICA: MongoDB Transactions — RESOLVIDO ✅

Testado empiricamente neste ambiente, não é suposição:

| Verificação | Resultado |
|---|---|
| Versão do mongod | **7.0.39** (suporta transações multi-documento) |
| Estado inicial | `standalone` → `OperationFailure: Transaction numbers are only allowed on a replica set member` |
| Conversão para replica set | **Executada com sucesso**: `mongod --replSet rs0 --dbpath /var/lib/mongodb` + `rs.initiate()` → `set: rs0, isWritablePrimary: true` |
| `MONGO_URL` | **Inalterada** (`mongodb://localhost:27017`) — a conversão é transparente para a aplicação |
| Commit multi-coleção | ✅ 2 coleções escritas atomicamente |
| Abort/rollback | ✅ exceção no meio da transação → **nenhuma** das 2 escritas persistiu |
| Persistência entre restarts | ✅ novo programa supervisor `mongodb-rs` (`/app/scripts/mongo_rs.sh`, autostart+autorestart, idempotente) garante `rs0` primary a cada boot do pod; o programa `mongodb` original (standalone) fica parado |
| Dados existentes | preservados — mesmo `dbPath`, sem perda |

**Conclusão: o motor financeiro será implementado com transações ACID reais (`session.start_transaction()`). NÃO haverá fallback de atomicidade simulada.**

O padrão único de acesso será um `UnitOfWork` que abre a sessão e repassa `session=` a todos os repositórios; qualquer escrita de repositório sem `session` em caso de uso multi-coleção é erro de implementação (coberto por teste).

Limitação residual (transparente): single-node RS não dá alta disponibilidade — se o processo cair, há indisponibilidade momentânea até o autorestart. Não afeta atomicidade nem durabilidade (`writeConcern: majority` com 1 nó = disco confirmado).

---

## 1. Commitment → Occurrence → Transaction (os três conceitos)

| | **Commitment** | **Occurrence** | **Transaction** |
|---|---|---|---|
| Significado | Obrigação/entrada **planejada** (o contrato) | A previsão **daquela competência** (a linha do calendário) | O evento que **realmente movimentou dinheiro** |
| Tempo | atemporal (tem início/fim) | 1 competência `YYYY-MM` | 1 data exata no passado |
| Quantidade | 1 | N (1 por competência/parcela) | 0..N (só quando pago) |
| Move saldo de conta | ❌ nunca | ❌ nunca | ✅ **exclusivamente** |
| Editável pelo usuário | ✅ (regra) | parcialmente (valor/vencimento da parcela) | ✅ (fato) |
| Entra na projeção | via occurrences | ✅ | ❌ (é histórico) |
| Entra no extrato | ❌ | ❌ | ✅ |

Regra de ouro: **Occurrence é previsão. Transaction é fato. Saldo só muda com fato.**

### 1.a Compra parcelada no cartão — iPhone R$3.600, 12x, Nubank, 10/08/2026
```
commitments  1 doc: type=purchase_installment, total=3600, installments_total=12,
                    installment_amount=300, credit_card_id=nubank, payment_method=credit_card
occurrences 12 docs: kind=installment, amount=300, sequence=1..12/12,
                    competence=2026-09..2027-08 (ciclo do cartão), invoice_id=<fatura do ciclo>
invoices    upsert de 12 faturas (uma por ciclo), total += 300 em cada
transactions 0 docs  ← a compra NÃO gera transação
accounts     inalterado
```
### 1.b Compra à vista no cartão — R$180, Nubank
```
commitments  1 doc: type=purchase_installment, installments_total=1, total=180
occurrences  1 doc: kind=installment, sequence=1/1, amount=180, invoice_id=<fatura 2026-09>
invoices     fatura 2026-09.total += 180
transactions 0 · accounts inalterado
```
À vista é o caso N=1 do parcelamento — mesmo código, zero ramificação especial.

### 1.c Pagamento da fatura Nubank 2026-09 (R$1.480, pago do Itaú em 08/09)
```
invoices     paid_amount=1480, status=paid
occurrences  todas as occurrences com invoice_id=<essa fatura> → paid_amount=amount, paid_at
             + a occurrence kind=invoice (a "fatura como compromisso") → paid
transactions 1 doc: type=invoice_payment, amount=1480, account_id=itau, invoice_id=<fatura>
accounts     itau.current_balance -= 1480   ← ÚNICO débito de conta em todo o fluxo do cartão
```
### 1.d Despesa fixa — Aluguel R$1.800, todo dia 10, indeterminado
```
commitments  1 doc: type=fixed_expense, recurrence={monthly, day_of_month:10}, installments_total=null
occurrences  18 docs (janela rolante), kind=recurring_expense, amount=1800, sequence=null
transactions só quando o usuário paga: 1 doc type=commitment_payment com a conta escolhida NAQUELE mês
```
### 1.e Assinatura — Spotify R$21,90, dia 15, no Nubank
```
subscriptions 1 doc (dados do domínio: periodicidade, próxima cobrança, valor anual 262,80, status)
commitments   1 doc: type=subscription, source={module:"subscription", ref_id:<sub>}
occurrences   18 docs kind=subscription_charge, amount=21.90, invoice_id=<fatura do mês> (cartão)
invoices      cada fatura recebe +21,90
transactions  nenhuma própria — é liquidada junto com a fatura do cartão
```
### 1.f Receita recorrente — Salário R$4.500, dia 5, conta Itaú
```
income_sources 1 doc · commitments 1 doc: type=recurring_income, direction=inflow
occurrences    18 docs kind=income, direction=inflow, amount=4500
transactions   ao confirmar o recebimento: type=income, account_id=itau → itau += 4500
```
### 1.g Terceiro a receber — Ana comprou R$600 no meu cartão em 6x
```
people                       1 doc (Ana)
third_party_relationships    1 doc: direction=receivable, total=600, installments=6, card_id=nubank
commitments 2 docs:
   (A) purchase_installment  600 em 6x no Nubank  → é MINHA dívida com o banco
   (B) third_party_receivable 600 em 6x, person_id=Ana → é o crédito que Ana me deve
occurrences 6 (do A, outflow, dentro das faturas) + 6 (do B, inflow, person_id=Ana)
efeito líquido nos Compromissos do Mês: −100 (fatura) +100 (Ana) = 0 de impacto real,
   mas ambos visíveis; se Ana atrasar, o outflow permanece e o inflow vira overdue.
transactions ao Ana pagar: type=income, account_id=<escolhida>, person_id=Ana
```
### 1.h Terceiro a pagar — peguei R$1.000 emprestado do João, 4x R$250
```
third_party_relationships 1 doc: direction=payable, total=1000, installments=4
commitments 1 doc: type=third_party_payable, direction=outflow, person_id=João
occurrences 4 docs kind=third_party, amount=250, inflow? NÃO → outflow
transactions a cada pagamento: type=expense, occurrence_id, account_id escolhida, person_id=João
```

---

## 2. `occurrences` — schema enxuto e universal

Problema evitado: uma coleção com 40 campos de todos os domínios. Solução: **núcleo universal fixo + `kind` + `detail` (subdocumento pequeno e específico) + `refs`**. Dados ricos do domínio **permanecem em `subscriptions`, `third_party_relationships`, `income_sources`, `commitments`** — occurrence só carrega o mínimo para renderizar e calcular o mês sem `$lookup`.

```jsonc
{
  // ---- IDENTIDADE (universal) ----
  "_id": ObjectId, "user_id": ObjectId,
  "commitment_id": ObjectId,          // dono da regra; sempre presente
  "kind": "installment | recurring_expense | subscription_charge | invoice |
           third_party | income | loan | financing | other",
  "direction": "outflow" | "inflow",

  // ---- CALENDÁRIO (universal) ----
  "competence": "2026-09",            // string ordenável; sem timezone
  "due_date": ISODate,                // UTC

  // ---- VALOR E LIQUIDAÇÃO (universal) ----
  "amount": 300.00,
  "paid_amount": 0.00,
  "paid_at": null,

  // ---- SEQUÊNCIA (universal, null quando não parcelado) ----
  "sequence": 4, "sequence_total": 12,

  // ---- ESTADO PERSISTIDO MÍNIMO (universal) ----
  "state": "open | paid | cancelled",   // fato binário, indexável
  "frozen": false,                      // espelho de commitments.frozen (para query do mês)

  // ---- REFERÊNCIAS (universal, sempre os mesmos 6 campos, null quando N/A) ----
  "refs": { "invoice_id": null, "credit_card_id": null, "account_id": null,
            "category_id": ObjectId, "person_id": null, "transaction_ids": [] },

  // ---- ESPECÍFICO DO KIND (pequeno, só o que a linha precisa exibir) ----
  "detail": {},   // installment: {}   subscription_charge:{ "periodicity":"monthly" }
                  // invoice:{ "closing_date":ISODate, "items_count":14 }
                  // third_party:{ "third_party_id":ObjectId, "tp_direction":"receivable" }
                  // income:{ "source_kind":"salary" }

  // ---- APRESENTAÇÃO / AGRUPAMENTO ----
  "label": "iPhone 15 · 4/12",
  "origin_group": "cards|installments|fixed|subscriptions|financing|loans|third_parties|income",

  // ---- METADATA ----
  "meta": { "materialized_by": "recurrence_engine|purchase_service|manual",
            "generated_at": ISODate, "source_channel": "web|app|nlp|whatsapp|api",
            "edited": false, "version": 1 },
  "created_at": ISODate, "updated_at": ISODate
}
```
`status` **nunca é armazenado** — é derivado (§ status abaixo). `state` guarda apenas o que não dá para inferir de uma data.

**Status derivado (função única `domain/status.py`):**
```
if state == "cancelled" -> cancelled
if frozen               -> frozen
if state == "paid" or paid_amount >= amount -> paid
if today > due_date     -> overdue
if competence == mês corrente -> due
else -> future
```

**Índices de `occurrences`:**
```
{user_id:1, competence:1, state:1, frozen:1}          ← query da tela do mês
{user_id:1, due_date:1, state:1}                      ← atrasados / próximos vencimentos
{user_id:1, commitment_id:1, sequence:1}              ← detalhe do compromisso
{user_id:1, "refs.invoice_id":1}                      ← itens da fatura
{user_id:1, "refs.person_id":1, state:1}              ← terceiros
{user_id:1, kind:1, competence:1}                     ← análises por tipo
{user_id:1, commitment_id:1, competence:1, sequence:1} UNIQUE ← idempotência
```

---

## 3. Fluxo completo do cartão de crédito

```
COMPRA (não é transação!)
  purchase_service.create(card, 3600, 12x, date=10/08)
      │  domain/card_cycle: closing_day=28, due_day=5
      │  10/08 < 28/08 → entra na fatura que fecha 28/08 e vence 05/09 → competence 2026-09
      ▼
COMMITMENT (1) ──► OCCURRENCES (12, kind=installment, refs.invoice_id preenchido)
      │
      ▼
INVOICE (upsert idempotente por card+período)  total += 300 por ciclo
      │        + 1 occurrence kind=invoice por fatura (é ELA que aparece no grupo "Cartões";
      │          as parcelas ficam como itens do detalhe, sem dupla contagem — ver §4)
      ▼
PAGAMENTO DA FATURA  POST /api/invoices/{id}/pay { account_id, date, amount }
      │  (transação ACID)
      ▼
TRANSACTION (type=invoice_payment, account_id=escolhida no ato)
      ▼
ACCOUNT.current_balance -= valor pago    ← ÚNICO ponto de débito
```
Garantia anti-dupla-contagem: no total do mês, o grupo **Cartões** soma as occurrences `kind=invoice`; as `kind=installment` que possuem `refs.invoice_id != null` são **excluídas do total** (são detalhe da fatura) e exibidas dentro do grupo Parcelamentos apenas como informação/cronograma. Parcelas sem cartão (financiamento, empréstimo) entram no total normalmente. Essa regra vive em `domain/month.py`, única.

---

## 4. Parcelamento
```
Commitment(total=3600, n=12)
   └─ domain/installments.split(3600, 12)
        → [300.00 × 12]  |  ex.: split(1000,3) → [333.34, 333.33, 333.33]  (soma == total, centavo na 1ª)
   └─ domain/card_cycle.schedule(purchase_date, closing_day, due_day, n)
        → [(competence, due_date)] × 12
   └─ Occurrences × 12 (sequence i/12, unique por (commitment, competence, sequence))
   └─ Invoice upsert por competência (só quando payment_method=credit_card)
   └─ Projection: soma occurrences futuras por competência → mostra quando o compromisso termina
                  e quanto libera ("em out/2026 você libera R$450/mês")
```
Alterações no commitment (valor/nº de parcelas) **re-materializam somente as occurrences abertas futuras**; parcelas pagas são imutáveis (preservam histórico).

---

## 5. `GET /api/months/{YYYY-MM}` — fonte única de verdade

Uma query indexada + cálculo puro no domínio. Dashboard, tela Compromissos, relatório mensal e IA consomem **este mesmo serviço** (`domain/month.build_month_view`).

```python
occ = find({user_id, competence: "2026-08"})          # 1 query, índice composto
countable = [o for o in occ if o.state != "cancelled"
             and not (o.kind == "installment" and o.refs.invoice_id)]   # anti-dupla-contagem

income_expected = Σ amount    where direction=inflow  and not frozen
committed       = Σ amount    where direction=outflow and not frozen   # total de compromissos
paid            = Σ paid_amount where direction=outflow and not frozen
pending         = committed - paid
frozen_total    = Σ amount    where frozen == True                     # fora de committed
overdue         = Σ (amount-paid_amount) where status == overdue
progress_pct    = 0 if committed == 0 else round(paid / committed * 100)
free_projected  = income_expected - committed          # visão do mês fechado
groups          = agrupar por origin_group, cada um com total e itens (status derivado)
```
Retorno: `{competence, income_expected, committed, paid, pending, frozen_total, overdue, free_projected, progress_pct, groups[], insights[]}`.

---

## 6. Dinheiro livre — definição matemática

Dois números distintos e ambos exibidos, para não confundir caixa com margem:

**(1) Livre agora (mês corrente)** — quanto posso gastar hoje sem furar o mês:
```
saldo_atual            = Σ accounts.current_balance (não arquivadas)          [só transactions afetam]
pendente_do_mes        = Σ (amount − paid_amount) de occurrences outflow, mês corrente,
                         state=open, frozen=false, excluindo parcelas com invoice_id
                         (a fatura entra pelo seu próprio kind=invoice)
receitas_a_receber_mes = Σ (amount − paid_amount) de occurrences inflow, mês corrente, state=open

LIVRE_AGORA = saldo_atual − pendente_do_mes
LIVRE_OTIMISTA = saldo_atual + receitas_a_receber_mes − pendente_do_mes
```
Occurrences **pagas** não entram (já estão refletidas no saldo pela transaction). Occurrences **congeladas** não entram. Faturas em aberto entram integralmente pelo saldo pendente da fatura. O limite do cartão **não** soma ao dinheiro livre (é crédito, não caixa).

**(2) Livre projetado do mês M (M futuro)**
```
LIVRE(M) = receitas_previstas(M) − compromissos_ativos(M)
SALDO_PROJETADO(M) = saldo_atual + Σ_{m=mês_atual..M} (receitas(m) − compromissos_pendentes(m))
```

---

## 7. Idempotência

**Índices únicos (barreira física no banco):**
```
occurrences  {user_id, commitment_id, competence, sequence}  UNIQUE
invoices     {user_id, credit_card_id, period.year, period.month} UNIQUE
transactions {user_id, occurrence_id} UNIQUE sparse     ← impede pagar 2× a mesma parcela
users        {email} UNIQUE sparse · {google_sub} UNIQUE sparse
idempotency_keys {key} UNIQUE + TTL 24h em expires_at
```
Escritas de materialização usam `bulk_write([UpdateOne(..., upsert=True)])` → rodar 2× não duplica, apenas reescreve o mesmo documento.

**`Idempotency-Key` (header) obrigatório em:** `POST /occurrences/{id}/pay`, `POST /invoices/{id}/pay`, `POST /commitments`, `POST /transactions`, `POST /ai/confirm`.
Fluxo: dentro da mesma transação, `insert_one({key, user_id, endpoint, request_hash})` na coleção `idempotency_keys`; se `DuplicateKeyError` → devolve o `result_ref` já gravado (HTTP 200, mesma resposta) sem reexecutar. Se `request_hash` divergir para a mesma key → HTTP 409.

---

## 8. Fronteiras transacionais (9)

Todas: 1 endpoint = 1 `UnitOfWork` = 1 `start_transaction`. Rollback = abort automático da sessão (nada persiste). Erro → HTTP 4xx/5xx + `audit_logs` com a exceção.

| # | Caso de uso | Coleções | Ordem | Sucesso | Falha / rollback |
|---|---|---|---|---|---|
| 1 | `pay_occurrence` | idempotency_keys, occurrences, transactions, accounts, invoices?, commitments | key → lock occurrence (`state=open`) → insert transaction → `$inc` account → update occurrence(paid) → recalc invoice se houver → completa commitment se última parcela | occurrence paid, saldo debitado 1×, transaction única | occurrence já paga → 409; conta inexistente/sem ownership → 403; qualquer erro → abort: **sem transaction, sem débito** |
| 2 | `pay_invoice` | idempotency_keys, invoices, occurrences(N), transactions, accounts | key → carrega fatura → insert transaction(invoice_payment) → `$inc` account → marca fatura paga → `update_many` itens paid → occurrence kind=invoice paid | fatura paid, N itens paid, 1 débito | pagamento parcial permitido (`status=partially_paid`); erro → abort total, itens continuam open |
| 3 | `create_installment_purchase` | commitments, occurrences(N), invoices(upsert M) | insert commitment → schedule (domínio) → bulk upsert occurrences → `$inc` totais das faturas | N occurrences + faturas coerentes | duplicidade por unique index → não duplica; erro → abort: nenhum commitment órfão |
| 4 | `create_subscription` | subscriptions, commitments, occurrences | insert subscription → insert commitment(ref) → materializa 18 meses (+ vincula faturas se cartão) | assinatura visível em Assinaturas, Compromissos, fatura e projeção | abort → nada criado (sem assinatura sem compromisso) |
| 5 | `create_third_party` | third_party_relationships, commitments(1–2), occurrences, invoices? | insert relationship → commitment(s) → occurrences → faturas se cartão de terceiro | terceiro aparece em Terceiros + Compromissos + fluxo | abort total |
| 6 | `freeze/unfreeze_commitment` | commitments, occurrences | `commitments.frozen=true` → `update_many occurrences {state:open, competence>=hoje} frozen=true` | compromisso sai dos totais ativos, histórico e parcelas pagas intactos | abort → nenhum estado misto (parte congelada) |
| 7 | `materialize_recurrences` | occurrences, commitments.materialized_until | por commitment ativo: gera de `materialized_until+1` até `hoje+18m` → bulk upsert → atualiza marca | janela sempre preenchida, nunca duplicada | abort → `materialized_until` não avança; próxima execução refaz |
| 8 | `transfer_between_accounts` | transactions(1), accounts(2) | insert transaction(transfer) → `$inc` origem → `$inc` destino | soma dos saldos preservada | abort → nenhum saldo alterado (sem dinheiro sumindo) |
| 9 | `cancel_or_delete_commitment` | commitments, occurrences, (transactions preservadas), invoices | commitment `status=cancelled` → occurrences abertas futuras `state=cancelled` → `$inc` estorno nas faturas afetadas | totais futuros recalculados, histórico pago preservado | abort → nada cancelado parcialmente |

Ordem geral padronizada: **validar/ownership → idempotência → escrever fato (transaction) → mover saldo → atualizar previsão (occurrence/invoice/commitment)**.

---

## 9. Projeção sem confundir previsão com fato
- Projeção lê **exclusivamente `occurrences`** (previsão). Nunca soma `transactions`.
- Histórico/extrato lê **exclusivamente `transactions`** (fato). Nunca soma `occurrences`.
- Único ponto de contato: `occurrences.refs.transaction_ids` (rastreabilidade) e a regra "occurrence paga não conta como pendente, pois seu efeito já está no saldo".
- Para não contar duas vezes o mês corrente: `SALDO_PROJETADO` parte do `saldo_atual` (que já contém os pagos) e soma apenas o **pendente**.
- Occurrences futuras trazem `state=open`; a API sempre devolve `status` derivado, e o frontend rotula visualmente **Previsto** vs **Realizado** com cores/badges distintos.

## 10. Health Score (0–100, explicável)

| Componente | Peso | Métrica | Faixa boa |
|---|---|---|---|
| Comprometimento da renda | 30 | `committed / income_expected` | < 50% |
| Margem livre | 20 | `livre_agora / income_expected` | > 20% |
| Pontualidade | 15 | pagos em dia / total últimos 3 meses | > 95% |
| Atrasos | 10 | valor em `overdue` | 0 |
| Reserva de emergência | 10 | `saldo_atual / gasto_médio_mensal` | ≥ 3 meses |
| Tendência | 10 | variação do comprometimento vs 3 meses | caindo |
| Metas | 5 | progresso médio das metas ativas | > 50% |

Resposta da API traz `{score, band:"boa", components:[{key, label, weight, value, points, verdict, explanation:"Você compromete 64% da renda; abaixo de 50% seria ideal (−11 pts)"}], top_actions:[...]}`. **Nunca uma nota sem os componentes.**

## 11. Simulação — 100% read-only
`POST /api/simulations` carrega a projeção real em memória, aplica os deltas (nova compra parcelada, cancelar assinaturas, antecipar dívida, mudança de salário) sobre **objetos de domínio em memória** e retorna o antes/depois. Garantias: o serviço de simulação recebe repositórios em **modo leitura** (nenhum método de escrita injetado), não abre `UnitOfWork`, e a única escrita opcional é o log da simulação em `simulations` (histórico do usuário, jamais em `occurrences`/`transactions`/`accounts`). Teste automatizado: snapshot de todas as coleções financeiras antes/depois de 20 simulações → hash idêntico.

---

# A. Modelo final de dados

`users` (profile+preferences embutidos) · `people` · `accounts` · `credit_cards` · `invoices` · `categories` · **`commitments`** · **`occurrences`** · `transactions` · `subscriptions` · `income_sources` · `third_party_relationships` · `goals` + `goal_contributions` · `investments` + `investment_transactions` · `budgets` · `simulations` · `ai_conversations` · `alerts` · `idempotency_keys` · `audit_logs`.
(Schemas de `commitments`/`occurrences`/`transactions` em §1–§2; demais coleções guardam os campos ricos de cada domínio, conforme aprovado na v1.)

# B. Relacionamentos
```
users 1─N accounts, credit_cards, categories, people, commitments, transactions, goals, investments
credit_cards 1─N invoices 1─N occurrences(kind=installment|subscription_charge)
commitments 1─N occurrences 0─N transactions
subscriptions 1─1 commitments      income_sources 1─1 commitments
third_party_relationships 1─1..2 commitments      people 1─N third_party_relationships
accounts 1─N transactions          categories 1─N commitments/occurrences/transactions
invoices 1─1 occurrence(kind=invoice)  ← a fatura como compromisso do mês
```

# C. Fluxo financeiro
```
ENTRADA (form | ação rápida | linguagem natural | WhatsApp)
   → /api/ingest ou endpoint do módulo
   → Application Service (UnitOfWork + transação ACID)
   → Domain (parcelamento, ciclo do cartão, recorrência)
   → commitments + occurrences (+ invoices)
   → GET /months/{YYYY-MM}  ──►  Compromissos do Mês · Dashboard · Relatório · IA
   → pagamento → transaction → account.balance
   → projection 18m → dinheiro livre → health score → alertas → IA/simulador
```

# D/E. Fronteiras transacionais §8 · Índices §2 + §7 (+ `transactions {user_id,date:-1}`, `{user_id,account_id,date:-1}`; `commitments {user_id,status,frozen}`; `invoices {user_id,status,due_date}`)

# F. API principal
```
/api/auth/{register,login,google/session,me,refresh}
/api/{accounts,credit-cards,categories,people}            CRUD
/api/commitments  POST GET  /:id  /:id/freeze  /:id/unfreeze  DELETE(cancel)
/api/occurrences  GET ?competence&group&status   POST /:id/pay
/api/invoices     GET ?card_id&competence   GET /:id   POST /:id/pay
/api/subscriptions /api/income-sources /api/third-parties /api/goals /api/investments /api/budgets
/api/transactions GET(filtros) POST PATCH DELETE
/api/months/{YYYY-MM}   ← FONTE ÚNICA   /api/projection?months=12   /api/dashboard
/api/reports/monthly/{YYYY-MM}   /api/alerts   /api/health-score
/api/ai/{ask,parse,confirm}   /api/simulations   /api/ingest/message
/api/admin/materialize   (idempotente, chamável por cron)
```

# G. Camadas
```
backend/
  server.py                      app + routers + lifespan(indexes, seed categorias)
  core/            config, security(jwt,bcrypt), deps(current_user), errors, logging
  domain/          installments, recurrence, card_cycle, status, month, free_money,
                   projection, health_score, simulation   ← PURO, sem I/O, 100% testável
  models/          base(PyObjectId, BaseDocument), commitment, occurrence, transaction, ...
  repositories/    base(user_id + session obrigatórios), occurrence_repo, invoice_repo, ...
  services/        unit_of_work, commitment_service, purchase_service, payment_service,
                   invoice_service, recurrence_service, subscription_service,
                   third_party_service, month_service, projection_service, ai_service
  api/             routers (só validação + delegação)
frontend/src/      pages/ components/ (ui, layout, commitments, cards, ...) hooks/ lib/
                   contexts/(Auth, Month) — ZERO regra financeira
```

# H. Estratégia de testes do domínio
`pytest` — unitários puros (sem banco) para `domain/*`: split de parcelas soma exata; dia 31 em fevereiro; compra antes/depois do fechamento; matriz completa de status; anti-dupla-contagem fatura×parcela; dinheiro livre com pagos/congelados; score somando 100.
Integração (com RS + transações): os 8 cenários exigidos (§52) + materializar 2× não duplica + pagar 2× a mesma parcela retorna 409 + abort de transação não deixa saldo alterado + simulação não altera nenhuma coleção (hash antes/depois) + isolamento entre usuários (ownership).

---
### Aguardando autorização para iniciar Fases 1 e 2.
