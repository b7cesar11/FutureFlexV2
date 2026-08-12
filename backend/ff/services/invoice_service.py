"""Servico de faturas. A fatura e a obrigacao AGREGADA do periodo do cartao.

Regra anti-dupla-contagem: a fatura possui uma ocorrencia propria (kind="invoice") que e
a unica que soma no total de Compromissos do Mes. As parcelas/compras vinculadas
(refs.invoice_id preenchido) sao a COMPOSICAO da fatura e nao somam de novo.
"""
from datetime import date

from ..core.db import db
from ..core.deps import DomainError
from ..domain import card_cycle
from ..domain.calendar_rules import as_datetime, clamp_day, parse_competence
from ..domain.money import summed
from ..models.base import now_utc
from ..models.entities import Invoice, Occurrence, OccMeta, OccRefs
from ..repositories import registry as repo
from bson import ObjectId


async def get_or_create(user_id: str, card, competence: str, session=None) -> Invoice:
    """Idempotente por (user, cartao, periodo) — protegido por indice unico."""
    year, month = parse_competence(competence)
    existing = await db.invoices.find_one(
        {"user_id": ObjectId(user_id), "credit_card_id": ObjectId(card.id),
         "period.year": year, "period.month": month}, session=session)
    if existing:
        return Invoice.from_mongo(existing)

    closing = clamp_day(competence, card.closing_day)
    due = card_cycle.due_date_for(competence, card.closing_day, card.due_day)
    invoice = Invoice(user_id=user_id, credit_card_id=card.id,
                      period={"year": year, "month": month}, competence=competence,
                      closing_date=as_datetime(closing), due_date=as_datetime(due),
                      total=0.0, paid_amount=0.0, status="open")
    await repo.invoices.insert(invoice, session=session)

    # ocorrencia agregadora da fatura (a que aparece no grupo "Cartões")
    occ = Occurrence(user_id=user_id, commitment_id=None, kind="invoice", direction="outflow",
                     competence=competence, due_date=as_datetime(due), amount=0.0,
                     label=f"Fatura {card.name}", origin_group="cards",
                     refs=OccRefs(credit_card_id=card.id, invoice_id=invoice.id),
                     detail={"closing_date": as_datetime(closing).isoformat(), "items_count": 0},
                     meta=OccMeta(materialized_by="invoice_service", generated_at=now_utc()))
    await repo.occurrences.insert(occ, session=session)
    return invoice


async def recalculate(user_id: str, invoice_id: str, session=None) -> Invoice:
    """Recalcula o total da fatura a partir de seus itens e sincroniza a ocorrencia agregadora."""
    items = await repo.occurrences.find(
        user_id, {"refs.invoice_id": invoice_id}, session=session)
    children = [o for o in items if o.kind != "invoice" and o.state != "cancelled"]
    aggregator = next((o for o in items if o.kind == "invoice"), None)

    total = summed(o.amount for o in children)
    paid_children = summed(o.paid_amount for o in children)
    invoice = await repo.invoices.get(user_id, invoice_id, session=session)
    status = invoice.status
    if status not in ("paid", "partially_paid"):
        status = "open"
    await repo.invoices.update(user_id, invoice_id,
                               {"total": total, "updated_at": now_utc(), "status": status},
                               session=session)
    if aggregator:
        await repo.occurrences.update(
            user_id, aggregator.id,
            {"amount": total, "paid_amount": min(paid_children, total),
             "detail.items_count": len(children), "updated_at": now_utc()},
            session=session)
    invoice.total = total
    return invoice


async def attach_occurrence(user_id: str, card, competence: str, session=None) -> Invoice:
    return await get_or_create(user_id, card, competence, session=session)
