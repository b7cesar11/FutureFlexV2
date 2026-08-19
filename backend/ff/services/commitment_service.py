"""Criacao de compromissos e materializacao de ocorrencias (idempotente, janela de 24 meses).

Fluxo: Commitment -> Installments/Recurrence -> Occurrences -> Invoice (quando cartao) -> Projection
"""
from datetime import date, datetime, timezone

from bson import ObjectId
from pymongo import UpdateOne

from ..core.config import PROJECTION_WINDOW_MONTHS
from ..core.db import db
from ..core.deps import DomainError
from ..domain import card_cycle, installments as inst_rules
from ..domain.calendar_rules import (add_months, as_datetime, competence_of,
                                     months_between, schedule_monthly, today_utc)
from ..domain.money import to_cents
from ..models.base import now_utc
from ..models.entities import Commitment, Occurrence, OccMeta, OccRefs, Recurrence
from ..repositories import registry as repo
from . import invoice_service
from .authorization import assert_owned

KIND_BY_TYPE = {
    "purchase_installment": ("installment", "installments"),
    "fixed_expense": ("recurring_expense", "fixed"),
    "subscription": ("subscription_charge", "subscriptions"),
    "loan": ("loan", "loans"),
    "financing": ("financing", "financing"),
    "third_party_payable": ("third_party", "third_parties"),
    "third_party_receivable": ("third_party", "third_parties"),
    "recurring_income": ("income", "income"),
    "other": ("other", "fixed"),
}

INFLOW_TYPES = {"recurring_income", "third_party_receivable"}


def window_end(start: str | None = None) -> str:
    base = start or competence_of(today_utc())
    return add_months(base, PROJECTION_WINDOW_MONTHS - 1)


async def create_commitment(user_id: str, payload: dict, session=None,
                            source: dict | None = None,
                            linked_commitment_id: str | None = None) -> Commitment:
    ctype = payload["type"]
    kind, group = KIND_BY_TYPE[ctype]
    direction = "inflow" if ctype in INFLOW_TYPES else "outflow"

    await assert_owned(user_id, {
        "credit_card_id": payload.get("credit_card_id"),
        "account_id": payload.get("default_account_id"),
        "category_id": payload.get("category_id"),
        "person_id": payload.get("person_id"),
    }, session=session)

    total = float(payload["total_amount"])
    count = payload.get("installments_total")
    start_date = payload.get("start_date") or datetime.now(timezone.utc)
    if isinstance(start_date, str):
        start_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
    if start_date.tzinfo is None:
        start_date = start_date.replace(tzinfo=timezone.utc)

    payment_method = payload.get("payment_method") or (
        "credit_card" if payload.get("credit_card_id") else "account")

    if count:
        parts = inst_rules.split(total, int(count))
        installment_amount = parts[0]
    else:
        installment_amount = total

    recurrence = None
    if not count:
        recurrence = Recurrence(
            frequency=payload.get("frequency", "monthly"),
            interval=payload.get("interval", 1),
            day_of_month=payload.get("day_of_month", start_date.day),
            start_competence=payload.get("start_competence") or competence_of(start_date.date()),
            end_competence=payload.get("end_competence"),
        )

    commitment = Commitment(
        user_id=user_id, type=ctype, direction=direction,
        description=payload["description"], total_amount=total,
        installments_total=int(count) if count else None,
        installment_amount=installment_amount, recurrence=recurrence,
        payment_method=payment_method, credit_card_id=payload.get("credit_card_id"),
        default_account_id=payload.get("default_account_id"),
        category_id=payload.get("category_id"), person_id=payload.get("person_id"),
        linked_commitment_id=linked_commitment_id,
        source=source or {"module": "manual", "ref_id": None},
        origin_group=group, start_date=start_date, status="active",
    )
    await repo.commitments.insert(commitment, session=session)
    await materialize(user_id, commitment, session=session)
    return commitment


async def materialize(user_id: str, commitment: Commitment, session=None) -> int:
    """Gera/atualiza as ocorrencias do compromisso. Idempotente (upsert por slot unico)."""
    kind, group = KIND_BY_TYPE[commitment.type]
    card = None
    if commitment.payment_method == "credit_card" and commitment.credit_card_id:
        card = await repo.credit_cards.get(user_id, commitment.credit_card_id, session=session)
        if not card:
            raise DomainError("Cartão não encontrado", 404)

    slots: list[tuple[str, date, float, int | None]] = []
    if commitment.installments_total:
        parts = inst_rules.split(commitment.total_amount, commitment.installments_total)
        if card:
            sched = card_cycle.schedule(commitment.start_date.date(), card.closing_day,
                                        card.due_day, commitment.installments_total)
        else:
            start_comp = competence_of(commitment.start_date.date())
            sched = schedule_monthly(start_comp, commitment.start_date.day,
                                     commitment.installments_total)
        for i, (comp, due) in enumerate(sched):
            slots.append((comp, due, parts[i], i + 1))
    else:
        rec = commitment.recurrence
        start_comp = rec.start_competence
        limit_comp = window_end()
        if rec.end_competence and rec.end_competence < limit_comp:
            limit_comp = rec.end_competence
        count = max(months_between(start_comp, limit_comp) + 1, 0)
        if rec.frequency == "yearly":
            count = max(count // 12 + 1, 1)
            interval = 12
        else:
            interval = rec.interval or 1
            count = (count + interval - 1) // interval
        for comp, due in schedule_monthly(start_comp, rec.day_of_month, count, interval):
            if card:
                due = card_cycle.due_date_for(comp, card.closing_day, card.due_day)
            slots.append((comp, due, commitment.installment_amount, None))

    # ocorrencias ja liquidadas/canceladas sao IMUTAVEIS: preservam historico
    settled = await repo.occurrences.find(user_id,
                                         {"commitment_id": commitment.id,
                                          "state": {"$ne": "open"}}, session=session)
    frozen_slots = {(o.competence, o.sequence) for o in settled}
    slots = [s for s in slots if (s[0], s[3]) not in frozen_slots]

    ops = []
    invoice_by_comp = {}
    if card:
        for comp, _, _, _ in slots:
            if comp not in invoice_by_comp:
                invoice_by_comp[comp] = await invoice_service.get_or_create(
                    user_id, card, comp, session=session)

    for comp, due, amount, seq in slots:
        label = commitment.description
        if seq and commitment.installments_total:
            label = f"{commitment.description} · {seq}/{commitment.installments_total}"
        refs = OccRefs(
            credit_card_id=commitment.credit_card_id,
            invoice_id=invoice_by_comp[comp].id if card else None,
            account_id=None,
            category_id=commitment.category_id,
            person_id=commitment.person_id,
        )
        occ = Occurrence(
            user_id=user_id, commitment_id=commitment.id, kind=kind,
            direction=commitment.direction, competence=comp, due_date=as_datetime(due),
            amount=amount, sequence=seq,
            sequence_total=commitment.installments_total,
            frozen=commitment.frozen, refs=refs,
            detail=_detail_for(commitment), label=label, origin_group=group,
            meta=OccMeta(materialized_by="commitment_service", generated_at=now_utc()),
        )
        doc = occ.to_mongo()
        key = {"user_id": ObjectId(user_id), "commitment_id": ObjectId(commitment.id),
               "competence": comp, "sequence": seq}
        # amount e amount_source sao INSERT-ONLY: materializacoes futuras nunca
        # sobrescrevem valores ja existentes (protege customizacoes por competencia).
        insert_only = {"created_at": doc.pop("created_at"), "paid_amount": doc.pop("paid_amount"),
                       "paid_at": doc.pop("paid_at"), "state": doc.pop("state"),
                       "amount": doc.pop("amount"),
                       "amount_source": doc.pop("amount_source", "default")}
        for k in ("user_id", "commitment_id", "competence", "sequence"):
            doc.pop(k, None)
        ops.append(UpdateOne(key, {"$set": doc, "$setOnInsert": insert_only}, upsert=True))

    if ops:
        await db.occurrences.bulk_write(ops, session=session, ordered=False)
    last_comp = slots[-1][0] if slots else commitment.materialized_until
    await repo.commitments.update(user_id, commitment.id,
                                 {"materialized_until": last_comp, "updated_at": now_utc()},
                                 session=session)
    if card:
        for invoice in invoice_by_comp.values():
            await invoice_service.recalculate(user_id, invoice.id, session=session)
    return len(ops)


def _detail_for(commitment: Commitment) -> dict:
    if commitment.type == "subscription":
        return {"periodicity": (commitment.recurrence.frequency
                                if commitment.recurrence else "monthly")}
    if commitment.type in ("third_party_payable", "third_party_receivable"):
        return {"tp_direction": ("payable" if commitment.type == "third_party_payable"
                                else "receivable"),
                "third_party_id": (commitment.source or {}).get("ref_id")}
    return {}


async def freeze(user_id: str, commitment_id: str, frozen: bool, session=None,
                 reason: str | None = None) -> dict:
    commitment = await repo.commitments.get(user_id, commitment_id, session=session)
    if not commitment:
        raise DomainError("Compromisso não encontrado", 404)
    await repo.commitments.update(user_id, commitment_id,
                                 {"frozen": frozen,
                                  "frozen_at": now_utc() if frozen else None,
                                  "freeze_reason": reason if frozen else None,
                                  "updated_at": now_utc()}, session=session)
    today = today_utc()
    result = await repo.occurrences.update_many(
        user_id,
        {"commitment_id": commitment_id, "state": "open",
         "due_date": {"$gte": as_datetime(date(today.year, today.month, 1))}},
        {"frozen": frozen, "updated_at": now_utc()}, session=session)
    # faturas afetadas precisam refletir o congelamento
    affected = await repo.occurrences.find(user_id, {"commitment_id": commitment_id},
                                           session=session)
    for invoice_id in {o.refs.invoice_id for o in affected if o.refs.invoice_id}:
        await invoice_service.recalculate(user_id, invoice_id, session=session)
    return {"commitment_id": commitment_id, "frozen": frozen,
            "occurrences_updated": result.modified_count}


async def cancel(user_id: str, commitment_id: str, session=None) -> dict:
    commitment = await repo.commitments.get(user_id, commitment_id, session=session)
    if not commitment:
        raise DomainError("Compromisso não encontrado", 404)
    today = today_utc()
    result = await repo.occurrences.update_many(
        user_id,
        {"commitment_id": commitment_id, "state": "open",
         "due_date": {"$gte": as_datetime(date(today.year, today.month, 1))}},
        {"state": "cancelled", "updated_at": now_utc()}, session=session)
    await repo.commitments.update(user_id, commitment_id,
                                 {"status": "cancelled", "updated_at": now_utc()},
                                 session=session)
    affected = await repo.occurrences.find(user_id, {"commitment_id": commitment_id},
                                           session=session)
    for invoice_id in {o.refs.invoice_id for o in affected if o.refs.invoice_id}:
        await invoice_service.recalculate(user_id, invoice_id, session=session)
    return {"commitment_id": commitment_id, "cancelled_occurrences": result.modified_count}


async def delete_mistake(user_id: str, commitment_id: str, session=None) -> dict:
    """Remove um cadastro manual feito por engano, somente antes de qualquer realização.

    Histórico financeiro liquidado nunca é apagado. Compromissos gerados por módulos
    relacionais (assinaturas/terceiros) também não podem ser removidos isoladamente.
    """
    commitment = await repo.commitments.get(user_id, commitment_id, session=session)
    if not commitment:
        raise DomainError("Compromisso não encontrado", 404)

    source_module = (commitment.source or {}).get("module") or "manual"
    if source_module != "manual":
        raise DomainError(
            "Este compromisso foi criado por outro módulo e não pode ser excluído isoladamente.",
            409,
        )
    if commitment.linked_commitment_id:
        raise DomainError(
            "Este compromisso possui um vínculo financeiro e não pode ser excluído isoladamente.",
            409,
        )

    occurrences = await repo.occurrences.find(
        user_id, {"commitment_id": commitment_id}, session=session
    )
    if any(
        o.state == "paid"
        or to_cents(o.paid_amount) > 0
        or bool(o.refs.transaction_ids)
        for o in occurrences
    ):
        raise DomainError(
            "Este compromisso já possui pagamento ou movimentação. O histórico financeiro deve ser preservado.",
            409,
        )

    invoice_ids = {o.refs.invoice_id for o in occurrences if o.refs.invoice_id}
    deleted = await repo.occurrences.delete_many(
        user_id, {"commitment_id": commitment_id}, session=session
    )
    await repo.commitments.delete(user_id, commitment_id, session=session)

    for invoice_id in invoice_ids:
        await invoice_service.recalculate(user_id, invoice_id, session=session)

    return {
        "commitment_id": commitment_id,
        "deleted": True,
        "deleted_occurrences": deleted.deleted_count,
    }


async def materialize_all(user_id: str, session=None) -> dict:
    """Recorrencias: mantem a janela de 24 meses preenchida. Rodar 2x nao duplica."""
    active = await repo.commitments.find(user_id, {"status": "active",
                                                   "installments_total": None},
                                          session=session)
    total = 0
    for commitment in active:
        total += await materialize(user_id, commitment, session=session)
    return {"commitments": len(active), "slots": total}
