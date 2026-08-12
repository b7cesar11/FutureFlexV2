"""Simulacao 100% READ-ONLY: opera sobre copias em memoria e nunca escreve dados financeiros."""
from copy import deepcopy

from ..core.config import PROJECTION_WINDOW_MONTHS
from ..domain import installments as inst_rules
from ..domain import projection as projection_rules
from ..domain.calendar_rules import add_months, as_datetime, clamp_day, competence_of, today_utc
from ..domain.money import money, summed
from ..models.entities import OccMeta, OccRefs, Occurrence
from ..repositories import registry as repo
from . import month_service


async def simulate(user_id: str, payload: dict) -> dict:
    months = int(payload.get("months") or PROJECTION_WINDOW_MONTHS)
    start = competence_of(today_utc())
    end = add_months(start, months - 1)
    real = await repo.occurrences.find(user_id, {"competence": {"$gte": start, "$lte": end}})
    balance = await month_service.balance(user_id)

    before = projection_rules.build_projection(balance, deepcopy(real), start, months,
                                               today_utc())

    simulated = deepcopy(real)
    notes = []

    # 1. nova compra parcelada
    purchase = payload.get("add_installment_purchase")
    if purchase:
        parts = inst_rules.split(float(purchase["total_amount"]), int(purchase["installments"]))
        for i, amount in enumerate(parts):
            comp = add_months(start, i)
            simulated.append(_virtual(user_id, comp, amount, "outflow",
                                      f"[simulação] {purchase.get('description', 'Nova compra')} "
                                      f"{i + 1}/{len(parts)}"))
        notes.append(f"Nova compra de R$ {money(purchase['total_amount']):.2f} em "
                     f"{len(parts)}x de R$ {parts[0]:.2f}")

    # 2. cancelar compromissos (ex.: assinaturas)
    for commitment_id in payload.get("cancel_commitment_ids", []):
        removed = [o for o in simulated if str(o.commitment_id) == str(commitment_id)]
        simulated = [o for o in simulated if str(o.commitment_id) != str(commitment_id)]
        if removed:
            notes.append(f"Cancelamento de '{removed[0].label}' libera "
                         f"R$ {removed[0].amount:.2f}/mês")

    # 3. variacao de renda mensal
    income_delta = payload.get("monthly_income_delta")
    if income_delta:
        for i in range(months):
            simulated.append(_virtual(user_id, add_months(start, i), money(abs(income_delta)),
                                      "inflow" if income_delta > 0 else "outflow",
                                      "[simulação] variação de renda"))
        notes.append(f"Variação de renda de R$ {money(income_delta):.2f}/mês")

    # 4. nova despesa recorrente
    recurring = payload.get("add_recurring_expense")
    if recurring:
        for i in range(months):
            simulated.append(_virtual(user_id, add_months(start, i),
                                      money(recurring["amount"]), "outflow",
                                      f"[simulação] {recurring.get('description', 'Nova despesa')}"))
        notes.append(f"Nova despesa recorrente de R$ {money(recurring['amount']):.2f}/mês")

    # 5. antecipacao de divida (usa saldo hoje)
    prepay = payload.get("prepay_amount")
    sim_balance = balance
    if prepay:
        sim_balance = summed([balance, -money(prepay)])
        notes.append(f"Antecipação de R$ {money(prepay):.2f} reduz seu saldo imediato")

    after = projection_rules.build_projection(sim_balance, simulated, start, months, today_utc())

    first_before, first_after = before["rows"][0], after["rows"][0]
    return {
        "notes": notes,
        "before": before, "after": after,
        "impact": {
            "monthly_commitment_delta": summed([first_after["commitments"],
                                                -first_before["commitments"]]),
            "free_delta": summed([first_after["free"], -first_before["free"]]),
            "commitment_ratio_before": first_before["commitment_ratio_pct"],
            "commitment_ratio_after": first_after["commitment_ratio_pct"],
            "affected_months": sum(1 for b, a in zip(before["rows"], after["rows"])
                                   if b["commitments"] != a["commitments"]
                                   or b["income"] != a["income"]),
            "risk": _risk(after["rows"]),
        },
        "read_only": True,
    }


def _risk(rows) -> str:
    negatives = [r for r in rows if r["projected_balance"] < 0]
    if negatives:
        return f"Atenção: saldo projetado fica negativo em {negatives[0]['competence']}"
    tight = [r for r in rows if r["income"] and r["commitment_ratio_pct"] > 80]
    if tight:
        return f"Comprometimento acima de 80% em {tight[0]['competence']}"
    return "Sem riscos identificados na janela simulada"


def _virtual(user_id: str, competence: str, amount: float, direction: str,
             label: str) -> Occurrence:
    return Occurrence(user_id=user_id, commitment_id=None, kind="other", direction=direction,
                      competence=competence, due_date=as_datetime(clamp_day(competence, 10)),
                      amount=amount, label=label, origin_group="fixed",
                      refs=OccRefs(), meta=OccMeta(materialized_by="simulation"))
