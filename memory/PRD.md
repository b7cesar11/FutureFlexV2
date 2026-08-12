# Future Flex V2 — PRD

## Problema original
Sistema inteligente de gestão e planejamento financeiro pessoal, construído do zero, cujo coração é
"Compromissos do Mês" (fatura da vida financeira). Deve mostrar não só onde o dinheiro foi, mas para
onde está indo: saldo, receitas futuras, compromissos, dinheiro livre, projeção, simulação e IA.
Requisitos completos no enunciado do usuário (63 seções).

## Decisões aprovadas pelo usuário
- Backend/DB: FastAPI + MongoDB (sem Supabase), re-arquitetado nativamente para Mongo
- Auth: JWT próprio + Google gerenciado pela Emergent (ambos)
- IA: GPT-5.5 via Universal Key
- Idioma/moeda: pt-BR / BRL · Visual: tema escuro moderno (fintech)
- Regras financeiras exclusivamente no backend (domain layer); frontend não calcula

## Estado atual (jun/2026)
- FASE 0 concluída: arquitetura técnica completa em `/app/memory/ARCHITECTURE.md` (v2, revisada)
- Infra: MongoDB convertido de standalone para **single-node replica set `rs0`** →
  transações ACID multi-documento validadas (commit + rollback testados).
  Programa supervisor `mongodb-rs` (`/app/scripts/mongo_rs.sh`) garante persistência entre restarts.
  `MONGO_URL` inalterada.
- Nenhum código de aplicação implementado ainda (por instrução explícita do usuário)

## Núcleo do modelo
Commitment (obrigação planejada) → Occurrence (previsão por competência, espinha dorsal do
calendário) → Transaction (fato real, único que move saldo de conta).
`GET /api/months/{YYYY-MM}` é a fonte única de verdade para Dashboard, Compromissos, relatórios e IA.

## Backlog priorizado
- P0 Fase 1 — Fundação: auth (JWT+Google), design system escuro, layout responsivo + PWA,
  contas, categorias, cartões, pessoas
- P0 Fase 2 — Motor: commitments, occurrences, parcelamento, status derivado, transações,
  pagamento atômico (UnitOfWork)
- P0 Fase 3 — Cartões: ciclos, faturas, compras parceladas, pagamento de fatura
- P0 Fase 4 — Compromissos do Mês (tela principal, agrupamento, detalhe, congelamento)
- P1 Fase 5 — Recorrências (despesas fixas, assinaturas, receitas)
- P1 Fase 6 — Terceiros (a pagar/receber, cartão de terceiro)
- P1 Fase 7 — Dashboard, projeção 18m, dinheiro livre, health score explicável
- P2 Fase 8 — Metas e investimentos
- P2 Fase 9 — IA (análise, NLP, simulador)
- P2 Fase 10 — Relatórios e alertas · Fase 11 — WhatsApp via /api/ingest/message

## Próxima tarefa
Aguardando autorização do usuário para iniciar Fases 1 e 2.
