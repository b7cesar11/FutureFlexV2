"""Metricas do motor financeiro -> health_score (dominio puro). Fonte unica de verdade."""
from ..domain import health_score
from ..domain.calendar_rules import add_months, competence_of, today_utc
from ..domain.money import money, summed
from ..repositories import registry as repo
from . import month_service, subscription_service


async def collect_metrics(user_id: str) -> dict:
    current = competence_of(today_utc())
    month = await month_service.month_view(user_id, current)
    free = await month_service.free_money(user_id)
    projection = await month_service.projection(user_id, 6)

    accounts = await repo.accounts.find(user_id, {"archived": False})
    cards = await repo.credit_cards.find(user_id, {"archived": False})
    invoices = await repo.invoices.find(user_id, {"status": {"$ne": "paid"}})
    commitments = await repo.commitments.find(user_id, {"status": "active", "frozen": False})

    horizon = add_months(current, 23)
    future = await repo.occurrences.find(
        user_id, {"competence": {"$gte": current, "$lte": horizon}, "state": "open"})
    countable = [o for o in future if not (o.refs.invoice_id and o.kind != "invoice")
                 and not o.frozen]

    # DIVIDA = obrigacoes com terceiros/instituicoes (parcelas, faturas, emprestimos,
    # financiamentos, terceiros a pagar). Despesa fixa recorrente NAO e divida.
    debt_kinds = {"invoice", "loan", "financing"}
    debt_remaining = summed(
        o.amount - o.paid_amount for o in countable
        if o.direction == "outflow" and (
            o.kind in debt_kinds
            or (o.kind == "installment" and not o.refs.invoice_id)
            or o.kind == "third_party"))
    installment_monthly = summed(o.amount for o in future
                                 if o.kind == "installment" and o.competence == current
                                 and not o.frozen)
    # USO DE CREDITO = faturas do ciclo corrente e do proximo (nao as 24 futuras)
    credit_horizon = add_months(current, 1)
    near_invoices = [i for i in invoices if i.competence <= credit_horizon]
    subs = await subscription_service.list_with_metrics(user_id)
    fixed_monthly = summed([
        summed(o.amount for o in future
               if o.kind == "recurring_expense" and o.competence == current and not o.frozen),
        subs["summary"]["monthly_total"],
    ])

    rows = projection["rows"]
    trend = None
    if len(rows) >= 4 and rows[0]["commitments"] > 0:
        later = summed([rows[1]["commitments"], rows[2]["commitments"], rows[3]["commitments"]])
        average_later = money(later / 3)
        trend = round((average_later - rows[0]["commitments"]) / rows[0]["commitments"] * 100)

    expense_months = [r for r in rows if r["commitments"] > 0]
    average_expenses = money(
        sum(r["commitments"] for r in expense_months) / len(expense_months)
    ) if expense_months else 0.0

    return {
        "competence": current,
        "monthly_income": month["income_expected"],
        "committed": month["committed"],
        "paid": month["paid"],
        "pending": month["pending"],
        "balance": free["balance"],
        "free_now": free["free_now"],
        "overdue": month["overdue"],
        "open_invoices_total": summed(i.total - i.paid_amount for i in near_invoices),
        "debt_remaining": debt_remaining,
        "installment_monthly": installment_monthly,
        "fixed_monthly": fixed_monthly,
        "subscriptions_monthly": subs["summary"]["monthly_total"],
        "average_monthly_expenses": average_expenses,
        "commitment_count": len(commitments),
        "account_count": len(accounts),
        "card_count": len(cards),
        "trend_delta_pct": trend,
    }


async def score(user_id: str) -> dict:
    metrics = await collect_metrics(user_id)
    return health_score.compute(metrics)
