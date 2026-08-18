# Future Flex V2 — Arquitetura protegida

## Princípio central

O Future Flex separa planejamento de realização financeira:

```text
Commitment → Occurrence → Transaction
```

- **Commitment**: regra/compromisso financeiro (aluguel, assinatura, parcela, renda etc.).
- **Occurrence**: instância daquele compromisso em uma competência específica.
- **Transaction**: movimento de dinheiro efetivamente realizado.

Uma ocorrência futura jamais deve virar Transaction automaticamente.

## Camadas

```text
Frontend React
    ↓
FastAPI / API
    ↓
Application Services
    ↓
Domain puro/testável
    ↓
Repositories
    ↓
MongoDB replica set
```

O frontend não é fonte de verdade para cálculos financeiros nem para autorização.

## Fonte única mensal

O backend deve produzir uma única visão de competência usada por Dashboard e Compromissos. Agregações paralelas no frontend são proibidas quando puderem divergir do motor.

## Regras financeiras invariáveis

1. `Commitment != Occurrence != Transaction`.
2. Ocorrências futuras representam planejamento.
3. Status é derivado de data de vencimento, pagamento, congelamento/cancelamento; não é um campo de baixa manual.
4. Compra no cartão não debita conta bancária.
5. Pagamento integral da fatura debita a conta escolhida no ato.
6. A fatura é obrigação agregada; os itens que a compõem não contam novamente no total.
7. Conta de pagamento não deve ficar permanentemente vinculada ao compromisso como regra de baixa.
8. Terceiro usando meu cartão = obrigação na minha fatura + recebível do terceiro, sem segunda despesa.
9. Congelamento preserva histórico e exclui o compromisso dos totais ativos; reativação restaura projeção futura.
10. Recorrências são materializadas de forma idempotente em janela configurável de 24 meses.
11. Operações financeiras multi-documento usam MongoDB transaction através da `UnitOfWork`.
12. Ownership é validado no backend por `user_id`.
13. Simulações são read-only.
14. IA recebe contexto estruturado e não possui acesso direto ao MongoDB nem capacidade de escrita financeira.
15. Valor recorrente dinâmico é representado pela mesma Commitment com valores diferentes por Occurrence.
16. Histórico pago é imutável e overrides manuais devem ser preservados.
17. Atrasado permanece na competência original; não deve ser duplicado/rolado como nova dívida no mês seguinte.

## Cartões e anti-dupla-contagem

Exemplo:

```text
Fatura Nubank R$ 421,90
├── iPhone R$ 300,00
├── Spotify R$ 21,90
└── Ana R$ 100,00
```

Comprometimento do cartão naquele mês: **R$ 421,90**, não R$ 843,80.

Os filhos podem aparecer no detalhamento com `counts_in_total=false` (ou contrato equivalente), mas a ocorrência agregadora de fatura é que entra no comprometimento.

## Transações ACID

`backend/ff/core/db.py` define a `UnitOfWork`. Se uma operação que modifica múltiplas coleções falhar, toda a transação deve ser abortada.

Exemplos:

- pagamento de occurrence: occurrence + transaction + account;
- pagamento de invoice: invoice + occurrence agregadora + transaction + account;
- criação de relações financeiras que exigem múltiplas gravações coordenadas.

Por isso o MongoDB precisa operar como replica set (`rs0` no ambiente local atual).

## Multi-cartão

O índice único de occurrences inclui `refs.invoice_id` para permitir ocorrências agregadoras de faturas de cartões diferentes na mesma competência sem perder idempotência.

## Projeção

A janela padrão é 24 meses (`PROJECTION_WINDOW_MONTHS`). Materialização e projeção não devem criar ocorrências infinitas nem duplicar competências.

## IA

O `context_service` monta o contexto financeiro determinístico. A IA interpreta esse contexto; ela não define saldo, comprometido, dinheiro livre, faturas, projeção ou Health Score.

Toda evolução futura deve preservar estas regras e adicionar regressão automatizada quando tocar nelas.
