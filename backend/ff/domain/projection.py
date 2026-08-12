"""Dinheiro livre e projecao. Le APENAS ocorrencias (previsao) + saldo das contas."""
from datetime import date

from . import month as month_rules
from . import status as st
from .calendar_rules import add_months
from .money import summed


def free_now(balance: float, occurrences_current_month, today: date,
             current_competence: str) -> dict:
    """LIVRE_AGORA = saldo_atual - pendente_do_mes (sem contar pagos nem congelados)."""
    counted = [o for o in month_rules.countable(occurrences_current_month) if not o.frozen]
    for o in counted:
        o.status = st.derive(o, today, current_competence)

    pending_out = summed(o.amount - o.paid_amount for o in counted
                         if o.direction == "outflow" and o.status != st.PAID)
    pending_in = summed(o.amount - o.paid_amount for o in counted
                        if o.direction == "inflow" and o.status != st.PAID)

    return {
        "balance": balance,
        "pending_commitments": pending_out,
        "pending_income": pending_in,
        "free_now": summed([balance, -pending_out]),
        "free_optimistic": summed([balance, pending_in, -pending_out]),
    }


def build_projection(balance: float, occurrences, start_competence: str, months: int,
                     today: date) -> dict:
    """Projecao mes a mes. Nunca soma transactions: apenas ocorrencias previstas."""
    by_comp: dict[str, list] = {}
    for o in month_rules.countable(occurrences):
        if o.frozen:
            continue
        by_comp.setdefault(o.competence, []).append(o)

    running = balance
    rows = []
    for i in range(months):
        comp = add_months(start_competence, i)
        items = by_comp.get(comp, [])
        income = summed(o.amount for o in items if o.direction == "inflow")
        commitments = summed(o.amount for o in items if o.direction == "outflow")
        if i == 0:
            # no mes corrente, o que ja foi pago ja esta refletido no saldo
            income = summed(o.amount - o.paid_amount for o in items if o.direction == "inflow")
            commitments = summed(o.amount - o.paid_amount for o in items if o.direction == "outflow")
        running = summed([running, income, -commitments])
        ending = [o for o in items
                  if o.sequence and o.sequence_total and o.sequence == o.sequence_total]
        rows.append({
            "competence": comp,
            "income": income,
            "commitments": commitments,
            "free": summed([income, -commitments]),
            "projected_balance": running,
            "commitment_ratio_pct": 0 if income == 0 else round(commitments / income * 100),
            "ending_commitments": [{"label": o.label, "amount": o.amount} for o in ending],
            "released_next_month": summed(o.amount for o in ending),
        })
    return {"start_competence": start_competence, "months": months, "rows": rows}
