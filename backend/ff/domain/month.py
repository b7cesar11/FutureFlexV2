"""Regra ANTI-DUPLA-CONTAGEM e agregacao do mes. FONTE UNICA de calculo mensal.

Principio aprovado: uma entidade agregadora (fatura do cartao) representa a obrigacao
financeira do periodo; seus filhos (parcelas/compras do cartao) sao apenas a COMPOSICAO
dessa obrigacao. Pai e filhos nunca sao somados juntos.
"""
from datetime import date

from . import status as st
from ..models.base import stringify_ids as _clean
from .money import summed

GROUPS = ["cards", "installments", "fixed", "subscriptions", "financing",
          "loans", "third_parties", "income"]

GROUP_LABELS = {
    "cards": "Cartões",
    "installments": "Parcelamentos",
    "fixed": "Despesas fixas",
    "subscriptions": "Assinaturas",
    "financing": "Financiamentos",
    "loans": "Empréstimos",
    "third_parties": "Terceiros",
    "income": "Receitas",
}


def is_aggregated_child(occ) -> bool:
    """True quando a ocorrencia e composicao de uma fatura (nao soma no total)."""
    return bool(occ.refs.invoice_id) and occ.kind != "invoice"


def countable(occurrences):
    """Ocorrencias que representam obrigacao/entrada propria (sem dupla contagem)."""
    return [o for o in occurrences
            if o.state != st.CANCELLED and not is_aggregated_child(o)]


def build_month_view(occurrences, competence: str, today: date,
                     current_competence: str | None = None) -> dict:
    current_competence = current_competence or f"{today.year:04d}-{today.month:02d}"
    for o in occurrences:
        o.status = st.derive(o, today, current_competence)

    counted = countable(occurrences)
    active = [o for o in counted if not o.frozen]

    inflow = [o for o in active if o.direction == "inflow"]
    outflow = [o for o in active if o.direction == "outflow"]

    income_expected = summed(o.amount for o in inflow)
    income_received = summed(o.paid_amount for o in inflow)
    committed = summed(o.amount for o in outflow)
    paid = summed(o.paid_amount for o in outflow)
    pending = summed([committed, -paid])
    frozen_total = summed(o.amount for o in counted if o.frozen)
    overdue = summed(o.amount - o.paid_amount for o in outflow if o.status == st.OVERDUE)

    groups = []
    for key in GROUPS:
        items = [o for o in occurrences if o.origin_group == key and o.state != st.CANCELLED]
        if not items:
            continue
        counted_items = [o for o in items if not is_aggregated_child(o) and not o.frozen]
        groups.append({
            "key": key,
            "label": GROUP_LABELS[key],
            "total": summed(o.amount for o in counted_items),
            "paid": summed(o.paid_amount for o in counted_items),
            "counts_in_total": True,
            "items": [serialize_item(o) for o in items],
        })

    return {
        "competence": competence,
        "income_expected": income_expected,
        "income_received": income_received,
        "committed": committed,
        "paid": paid,
        "pending": pending,
        "frozen_total": frozen_total,
        "overdue": overdue,
        "free_projected": summed([income_expected, -committed]),
        "progress_pct": 0 if committed == 0 else round(paid / committed * 100),
        "commitment_ratio_pct": 0 if income_expected == 0 else round(committed / income_expected * 100),
        "groups": groups,
    }


def serialize_item(o) -> dict:
    return {
        "id": o.id,
        "commitment_id": o.commitment_id,
        "kind": o.kind,
        "direction": o.direction,
        "label": o.label,
        "amount": o.amount,
        "amount_source": getattr(o, "amount_source", "default"),
        "paid_amount": o.paid_amount,
        "competence": o.competence,
        "due_date": o.due_date,
        "sequence": o.sequence,
        "sequence_total": o.sequence_total,
        "status": getattr(o, "status", None),
        "frozen": o.frozen,
        "origin_group": o.origin_group,
        "counts_in_total": not is_aggregated_child(o),
        "refs": _clean(o.refs.model_dump()),
        "detail": _clean(o.detail),
    }
