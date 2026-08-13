"""Dashboard integrado: compoe as MESMAS fontes de verdade (mes, livre, projecao, saude,
assinaturas, congelados). Nenhum calculo novo aqui."""
from ..domain.calendar_rules import competence_of, today_utc
from ..domain import status as st
from ..repositories import registry as repo
from . import (frozen_service, health_service, month_service, subscription_service,
               third_party_service)


async def dashboard(user_id: str) -> dict:
    base = await month_service.dashboard(user_id)
    health = await health_service.score(user_id)
    subs = await subscription_service.list_with_metrics(user_id)
    frozen = await frozen_service.list_frozen(user_id)
    third = await third_party_service.summary(user_id)

    cards = await repo.credit_cards.find(user_id, {"archived": False})
    card_names = {c.id: c.name for c in cards}
    next_invoice = None
    open_invoices = [i for i in base["open_invoices"] if i["total"] > 0]
    if open_invoices:
        chosen = sorted(open_invoices, key=lambda i: i["due_date"])[0]
        next_invoice = {**chosen, "card": card_names.get(chosen["credit_card_id"], "Cartão")}

    today = today_utc()
    current = competence_of(today)
    upcoming = await repo.occurrences.find(
        user_id, {"competence": current, "state": "open", "frozen": False},
        sort=[("due_date", 1)])
    next_commitments = []
    for occ in upcoming:
        if occ.refs.invoice_id and occ.kind != "invoice":
            continue
        if occ.direction != "outflow":
            continue
        next_commitments.append({
            "id": occ.id, "label": occ.label, "amount": occ.amount,
            "due_date": occ.due_date, "status": st.derive(occ, today, current),
            "origin_group": occ.origin_group,
        })
        if len(next_commitments) == 5:
            break

    rows = base["next_months"]
    trend = None
    if len(rows) >= 2:
        trend = {
            "direction": ("down" if rows[1]["commitments"] < rows[0]["commitments"]
                          else "up" if rows[1]["commitments"] > rows[0]["commitments"]
                          else "flat"),
            "next_competence": rows[1]["competence"],
            "next_commitments": rows[1]["commitments"],
            "delta": round(rows[1]["commitments"] - rows[0]["commitments"], 2),
        }

    return {
        **base,
        "next_invoice": next_invoice,
        "next_commitments": next_commitments,
        "subscriptions": {
            "monthly_total": subs["summary"]["monthly_total"],
            "annual_total": subs["summary"]["annual_total"],
            "active_count": subs["summary"]["active_count"],
            "next_charge": subs["summary"]["next_charge"],
        },
        "health": {
            "score": health["score"], "band": health["band"],
            "band_label": health["band_label"],
            "has_enough_data": health["has_enough_data"],
            "data_completeness_pct": health["data_completeness_pct"],
            "top_actions": health["top_actions"],
        },
        "third_parties": {
            "total_receivable": third["total_receivable"],
            "total_payable": third["total_payable"],
        },
        "frozen": frozen["summary"],
        "trend": trend,
    }
