"""Fonte UNICA de leitura financeira: mes, dinheiro livre, projecao e dashboard."""
from datetime import date

from ..core.config import PROJECTION_WINDOW_MONTHS
from ..domain import month as month_rules
from ..domain import projection as projection_rules
from ..domain.calendar_rules import add_months, competence_of, today_utc
from ..domain.money import summed
from ..repositories import registry as repo


async def balance(user_id: str) -> float:
    accounts = await repo.accounts.find(user_id, {"archived": False})
    return summed(a.current_balance for a in accounts)


async def month_view(user_id: str, competence: str) -> dict:
    occurrences = await repo.occurrences.find(user_id, {"competence": competence})
    view = month_rules.build_month_view(occurrences, competence, today_utc(),
                                        competence_of(today_utc()))
    view["insights"] = _insights(view)
    return view


def _insights(view: dict) -> list[dict]:
    out = []
    if view["overdue"] > 0:
        out.append({"severity": "warning",
                    "text": f"Você tem R$ {view['overdue']:.2f} em compromissos atrasados."})
    if view["income_expected"] and view["commitment_ratio_pct"] > 70:
        out.append({"severity": "warning",
                    "text": f"{view['commitment_ratio_pct']}% da sua renda prevista está comprometida."})
    if view["committed"] and view["progress_pct"] >= 100:
        out.append({"severity": "success", "text": "Todos os compromissos do mês estão quitados."})
    if view["frozen_total"] > 0:
        out.append({"severity": "info",
                    "text": f"R$ {view['frozen_total']:.2f} estão congelados e fora do total ativo."})
    return out


async def free_money(user_id: str) -> dict:
    current = competence_of(today_utc())
    occurrences = await repo.occurrences.find(user_id, {"competence": current})
    result = projection_rules.free_now(await balance(user_id), occurrences, today_utc(), current)
    result["competence"] = current
    return result


async def projection(user_id: str, months: int | None = None) -> dict:
    months = months or PROJECTION_WINDOW_MONTHS
    start = competence_of(today_utc())
    end = add_months(start, months - 1)
    occurrences = await repo.occurrences.find(
        user_id, {"competence": {"$gte": start, "$lte": end}})
    return projection_rules.build_projection(await balance(user_id), occurrences, start,
                                             months, today_utc())


async def dashboard(user_id: str) -> dict:
    current = competence_of(today_utc())
    month = await month_view(user_id, current)
    free = await free_money(user_id)
    proj = await projection(user_id, 6)
    accounts = await repo.accounts.find(user_id, {"archived": False})
    invoices = await repo.invoices.find(user_id, {"status": {"$ne": "paid"}})
    return {
        "competence": current,
        "balance": free["balance"],
        "free_now": free["free_now"],
        "free_optimistic": free["free_optimistic"],
        "income_expected": month["income_expected"],
        "committed": month["committed"],
        "paid": month["paid"],
        "pending": month["pending"],
        "overdue": month["overdue"],
        "progress_pct": month["progress_pct"],
        "commitment_ratio_pct": month["commitment_ratio_pct"],
        "accounts": [{"id": a.id, "name": a.name, "balance": a.current_balance,
                      "type": a.type, "color": a.color} for a in accounts],
        "open_invoices": [{"id": i.id, "competence": i.competence, "total": i.total,
                           "paid_amount": i.paid_amount, "due_date": i.due_date,
                           "credit_card_id": i.credit_card_id, "status": i.status}
                          for i in invoices],
        "next_months": proj["rows"],
        "insights": month["insights"],
    }
