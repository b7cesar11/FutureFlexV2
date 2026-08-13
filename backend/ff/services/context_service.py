"""FinancialContextService: monta o contexto financeiro estruturado do usuario autenticado.

A IA NUNCA acessa o MongoDB. Ela recebe apenas este dicionario, construido a partir dos
Application Services existentes (mesma fonte de verdade do Dashboard e de Compromissos).
Nada de outros usuarios, nada de credenciais, nada de ids internos desnecessarios.
"""
from ..domain.calendar_rules import competence_of, today_utc
from ..domain.money import money, summed
from ..repositories import registry as repo
from . import health_service, month_service, subscription_service, third_party_service

ESSENTIAL_CATEGORIES = {"Moradia", "Saúde", "Educação", "Transporte", "Alimentação"}
ESSENTIAL_KEYWORDS = ("aluguel", "condomínio", "condominio", "energia", "luz", "água", "agua",
                      "internet", "financiamento", "escola", "plano de saúde", "saude",
                      "empréstimo", "emprestimo")


async def build(user_id: str, months: int = 6) -> dict:
    current = competence_of(today_utc())
    month = await month_service.month_view(user_id, current)
    free = await month_service.free_money(user_id)
    projection = await month_service.projection(user_id, months)
    health = await health_service.score(user_id)
    subs = await subscription_service.list_with_metrics(user_id)
    third = await third_party_service.summary(user_id)

    accounts = await repo.accounts.find(user_id, {"archived": False})
    invoices = await repo.invoices.find(user_id, {"status": {"$ne": "paid"}},
                                        sort=[("due_date", 1)])
    cards = await repo.credit_cards.find(user_id, {"archived": False})
    card_names = {c.id: c.name for c in cards}
    commitments = await repo.commitments.find(user_id, {"status": "active"})

    ending = []
    for row in projection["rows"]:
        for item in row["ending_commitments"]:
            ending.append({"competence": row["competence"], **item})

    return {
        "reference_date": today_utc().isoformat(),
        "competence": current,
        "currency": "BRL",
        "balance": free["balance"],
        "accounts": [{"name": a.name, "balance": a.current_balance} for a in accounts],
        "free_money": {
            "free_now": free["free_now"],
            "free_optimistic": free["free_optimistic"],
            "pending_commitments": free["pending_commitments"],
            "pending_income": free["pending_income"],
        },
        "month": {
            "income_expected": month["income_expected"],
            "committed": month["committed"],
            "paid": month["paid"],
            "pending": month["pending"],
            "overdue": month["overdue"],
            "frozen_total": month["frozen_total"],
            "progress_pct": month["progress_pct"],
            "commitment_ratio_pct": month["commitment_ratio_pct"],
            "groups": [{"label": g["label"], "total": g["total"],
                        "items": [{"label": i["label"], "amount": i["amount"],
                                   "status": i["status"],
                                   "counts_in_total": i["counts_in_total"]}
                                  for i in g["items"]]}
                       for g in month["groups"]],
        },
        "open_invoices": [{"card": card_names.get(i.credit_card_id, "Cartão"),
                           "competence": i.competence,
                           "total": i.total, "paid": i.paid_amount,
                           "due_date": i.due_date.date().isoformat()} for i in invoices],
        "installments": [
            {"description": c.description, "installment_amount": c.installment_amount,
             "installments_total": c.installments_total,
             "card": card_names.get(c.credit_card_id) if c.credit_card_id else None,
             "frozen": c.frozen}
            for c in commitments if c.type == "purchase_installment"],
        "recurring_expenses": [
            {"description": c.description, "amount": c.installment_amount, "frozen": c.frozen}
            for c in commitments if c.type == "fixed_expense"],
        "subscriptions": {
            "monthly_total": subs["summary"]["monthly_total"],
            "annual_total": subs["summary"]["annual_total"],
            "active_count": subs["summary"]["active_count"],
            "items": [{"name": s["name"], "monthly": s["monthly_equivalent"],
                       "annual": s["annual_cost"], "status": s["status"],
                       "category": (s["category"] or {}).get("name")}
                      for s in subs["items"]],
        },
        "third_parties": {
            "total_receivable": third["total_receivable"],
            "total_payable": third["total_payable"],
            "items": [{"person": i["person"], "direction": i["direction"],
                       "pending": i["pending"]} for i in third["items"]],
        },
        "projection": [{"competence": r["competence"], "income": r["income"],
                        "commitments": r["commitments"], "free": r["free"],
                        "projected_balance": r["projected_balance"],
                        "commitment_ratio_pct": r["commitment_ratio_pct"]}
                       for r in projection["rows"]],
        "ending_commitments": ending[:8],
        "health": {
            "score": health["score"], "band_label": health["band_label"],
            "data_completeness_pct": health["data_completeness_pct"],
            "has_enough_data": health["has_enough_data"],
            "factors": [{"label": f["label"], "points": f["points"],
                         "max_points": f["max_points"], "verdict": f["verdict"],
                         "explanation": f["explanation"]} for f in health["factors"]],
        },
        "data_availability": {
            "has_income": month["income_expected"] > 0,
            "has_accounts": len(accounts) > 0,
            "has_commitments": len(commitments) > 0,
            "has_cards": len(cards) > 0,
            "has_subscriptions": subs["summary"]["active_count"] > 0,
        },
    }


def _is_essential(name: str, category: str | None) -> bool:
    if category and category in ESSENTIAL_CATEGORIES:
        return True
    lowered = (name or "").lower()
    return any(keyword in lowered for keyword in ESSENTIAL_KEYWORDS)


async def cut_candidates(user_id: str) -> dict:
    """Candidatos a corte calculados DETERMINISTICAMENTE no backend (a IA apenas explica)."""
    subs = await subscription_service.list_with_metrics(user_id)
    commitments = await repo.commitments.find(user_id, {"status": "active", "frozen": False})
    categories = await repo.categories.find(user_id, {})
    category_names = {c.id: c.name for c in categories}
    income = (await month_service.month_view(
        user_id, competence_of(today_utc())))["income_expected"]

    candidates = []
    for sub in subs["items"]:
        if sub["status"] != "active":
            continue
        candidates.append({
            "type": "subscription", "name": sub["name"],
            "monthly": sub["monthly_equivalent"], "annual_saving": sub["annual_cost"],
            "essential": _is_essential(sub["name"], (sub["category"] or {}).get("name")),
            "commitment_id": sub["commitment_id"],
            "note": "Assinatura recorrente — pode ser pausada ou cancelada a qualquer momento.",
        })
    for commitment in commitments:
        if commitment.type != "fixed_expense":
            continue
        essential = _is_essential(commitment.description,
                                  category_names.get(commitment.category_id))
        candidates.append({
            "type": "fixed_expense", "name": commitment.description,
            "monthly": commitment.installment_amount,
            "annual_saving": money(commitment.installment_amount * 12),
            "essential": essential, "commitment_id": commitment.id,
            "note": ("Despesa essencial: só reduza com alternativa concreta (renegociação, "
                     "troca de plano ou mudança de fornecedor)." if essential
                     else "Despesa recorrente não essencial."),
        })

    for candidate in candidates:
        share = (candidate["monthly"] / income) if income else 0
        if candidate["essential"]:
            candidate["impact"] = "medio" if share >= 0.05 else "baixo"
        elif share >= 0.05 or candidate["monthly"] >= 100:
            candidate["impact"] = "alto"
        elif share >= 0.02 or candidate["monthly"] >= 30:
            candidate["impact"] = "medio"
        else:
            candidate["impact"] = "baixo"
        candidate["income_share_pct"] = round(share * 100, 1) if income else None

    order = {"alto": 0, "medio": 1, "baixo": 2}
    candidates.sort(key=lambda c: (order[c["impact"]], -c["monthly"]))
    non_essential = [c for c in candidates if not c["essential"]]
    return {
        "income_expected": income,
        "candidates": candidates,
        "potential_monthly_saving": summed(c["monthly"] for c in non_essential),
        "potential_annual_saving": summed(c["annual_saving"] for c in non_essential),
        "high_impact": [c for c in candidates if c["impact"] == "alto"],
        "medium_impact": [c for c in candidates if c["impact"] == "medio"],
        "low_impact": [c for c in candidates if c["impact"] == "baixo"],
    }
