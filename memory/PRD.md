# Future Flex V2 — PRD

## Problema original
Sistema inteligente de gestão e planejamento financeiro pessoal, construído do zero, cujo coração é
"Compromissos do Mês" (a fatura da vida financeira). O produto não mostra só onde o dinheiro foi:
mostra para onde está indo — saldo, receitas futuras, compromissos, dinheiro livre, projeção,
simulação e IA. Requisitos completos no enunciado do usuário (63 seções).

## Decisões aprovadas pelo usuário
- Backend/DB: FastAPI + MongoDB (sem Supabase), re-arquitetado nativamente para Mongo
- Auth: JWT próprio + Google gerenciado pela Emergent (ambos)
- IA: GPT-5.5 via Universal Key (fase 9, ainda não implementada)
- pt-BR / BRL · tema escuro moderno
- Janela de materialização/projeção: **24 meses** (configurável por env)
- Anti-dupla-contagem: fatura = obrigação agregada do período; parcelas/compras do cartão =
  composição. Pai e filhos nunca somam juntos. Vale para qualquer agregador futuro.
- Terceiro no cartão: dois compromissos ligados (saída do cartão + entrada esperada do terceiro),
  sem gerar duas despesas, com relacionamento explícito
- Ocorrência futura ≠ transaction; conta escolhida no momento do pagamento; simulação read-only

## Arquitetura
```
Frontend (React) → API → Application Services (UnitOfWork/ACID) → Domain (puro) → Repositories → MongoDB
```
- Commitment (obrigação planejada) → Occurrence (previsão por competência, espinha dorsal do
  calendário) → Transaction (fato real, único que move saldo de conta)
- `GET /api/months/{YYYY-MM}` é a fonte única consumida por Dashboard e Compromissos
- Documento de arquitetura completo: `/app/memory/ARCHITECTURE.md`

## Implementado (12/06/2026 — Fases 1 e 2)
**Infra**
- MongoDB convertido de standalone para single-node replica set `rs0` → transações ACID
  multi-documento reais (commit e rollback validados). Programa supervisor `mongodb-rs`
  (`/app/scripts/mongo_rs.sh`) garante o replica set a cada boot; `MONGO_URL` inalterada
- Índices únicos de idempotência: ocorrência por (user, commitment, competência, sequência),
  fatura por (user, cartão, período), transação por idempotency_key

**Fase 1 — Fundação**
- Auth JWT (bcrypt, access+refresh, cookies httpOnly, lockout de 5 tentativas/15min) +
  Google gerenciado pela Emergent no mesmo registro de usuário
- Camadas separadas: `ff/core`, `ff/domain` (puro, sem I/O), `ff/models`, `ff/repositories`,
  `ff/services`, `ff/api`
- Authorization equivalente a RLS: todo repositório filtra por `user_id` e cada referência
  do payload tem ownership validado antes da escrita
- Design system escuro próprio, layout responsivo (sidebar desktop / bottom nav mobile com
  Compromissos destacado + FAB central), PWA instalável (manifest, service worker, ícones)
- Seed de categorias pt-BR e conta demo com dados de exemplo

**Fase 2 — Motor financeiro**
- Commitments (10 tipos), occurrences polimórficas, parcelamento com soma exata do total,
  ciclo de fatura do cartão, recorrências determinísticas e idempotentes em janela de 24 meses
- Status sempre derivado (future/due/paid/overdue/cancelled/frozen)
- Pagamento atômico (ocorrência e fatura) — único ponto que move saldo; conta escolhida no ato
- Terceiros a pagar/receber, inclusive terceiro usando meu cartão (dois compromissos ligados)
- Congelamento atômico, cancelamento, projeção de 24 meses, dinheiro livre, dashboard, simulador
  read-only, transações com filtros

**Qualidade**
- 20 testes de negócio próprios (`/app/tests/test_business_rules.py`) — 20/20 verdes
- Testing agent: 40/40 backend, frontend ~95% (apenas 2 avisos de console de baixa prioridade),
  sem issues bloqueantes (`/app/test_reports/iteration_1.json`)

## Backlog priorizado
- P0 Fase 3 (completar) — página de Assinaturas com total mensal/anual e próximas cobranças
- P0 Fase 4 (completar) — congelados em área própria, edição/cancelamento de compromisso na UI
- P1 Fase 7 — Health Score explicável, alertas inteligentes persistidos
- P1 Fase 5 — Receitas: página dedicada de fontes de receita
- P2 Fase 8 — Metas e investimentos
- P2 Fase 9 — IA GPT-5.5: analista financeiro, IA contextual por tela, linguagem natural
- P2 Fase 10 — Relatório mensal inteligente, comparativos, tendências
- P2 Fase 11 — WhatsApp sobre a camada `/api/ingest/message`

## Próximas tarefas
Aguardando o usuário priorizar entre Assinaturas, Health Score, Metas/Investimentos e IA.
