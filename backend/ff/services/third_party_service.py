"""Terceiros: relacionamento explícito + compromissos ligados, sem dupla contagem.

Registros ainda não realizados podem ser corrigidos ou removidos. Depois que existe
pagamento (inclusive pagamento parcial da fatura relacionada), o histórico fica protegido.
"""
from datetime import datetime, timezone

from ..core.deps import DomainError
from ..domain.money import money
from ..models.base import now_utc
from ..models.entities import ThirdPartyRelationship
from ..repositories import registry as repo
from . import commitment_service, invoice_service
from .authorization import assert_owned


def _parse_date(value):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            raise DomainError("Data inválida.", 422) from None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _validated(payload: dict, *, partial: bool = False) -> dict:
    out = dict(payload)
    if not partial or "description" in out:
        description = str(out.get("description") or "").strip()
        if not description:
            raise DomainError("Informe a descrição do registro de terceiro.", 422)
        out["description"] = description
    if not partial or "direction" in out:
        direction = out.get("direction")
        if direction not in ("receivable", "payable"):
            raise DomainError("Direção inválida (receivable|payable).", 422)
    if not partial or "total_amount" in out:
        try:
            total = money(out.get("total_amount"))
        except (TypeError, ValueError):
            raise DomainError("Informe um valor válido.", 422) from None
        if total <= 0:
            raise DomainError("O valor deve ser maior que zero.", 422)
        out["total_amount"] = total
    if not partial or "installments" in out:
        try:
            installments = int(out.get("installments") or 1)
        except (TypeError, ValueError):
            raise DomainError("Número de parcelas inválido.", 422) from None
        if installments < 1 or installments > 360:
            raise DomainError("Número de parcelas deve estar entre 1 e 360.", 422)
        out["installments"] = installments
    if "start_date" in out:
        out["start_date"] = _parse_date(out.get("start_date"))
    return out


async def _linked_occurrences(user_id: str, rel: ThirdPartyRelationship, session=None):
    commitment_ids = [cid for cid in (rel.commitment_id, rel.card_commitment_id) if cid]
    occurrences = []
    for commitment_id in commitment_ids:
        occurrences.extend(await repo.occurrences.find(
            user_id, {"commitment_id": commitment_id}, session=session))
    return commitment_ids, occurrences


async def _assert_unrealized(user_id: str, rel: ThirdPartyRelationship, session=None):
    commitment_ids, occurrences = await _linked_occurrences(user_id, rel, session=session)
    if any(o.state == "paid" or (o.paid_amount or 0) > 0 or bool(o.refs.transaction_ids)
           for o in occurrences):
        raise DomainError(
            "Este registro já possui pagamento/recebimento e não pode ser apagado ou reconstruído. O histórico financeiro foi preservado.",
            409,
        )
    invoice_ids = {o.refs.invoice_id for o in occurrences if o.refs and o.refs.invoice_id}
    for invoice_id in invoice_ids:
        invoice = await repo.invoices.get(user_id, invoice_id, session=session)
        if invoice and ((invoice.paid_amount or 0) > 0 or invoice.status in ("paid", "partially_paid")):
            raise DomainError(
                "A fatura relacionada já possui pagamento e impede uma alteração destrutiva deste registro.",
                409,
            )
    return commitment_ids, occurrences, invoice_ids


async def _remove_schedule(user_id: str, rel: ThirdPartyRelationship, session=None,
                           *, delete_relationship: bool = False):
    commitment_ids, occurrences, invoice_ids = await _assert_unrealized(
        user_id, rel, session=session)
    for commitment_id in commitment_ids:
        await repo.occurrences.delete_many(user_id, {"commitment_id": commitment_id}, session=session)
        await repo.commitments.delete(user_id, commitment_id, session=session)
    if delete_relationship:
        await repo.third_parties.delete(user_id, rel.id, session=session)
    for invoice_id in invoice_ids:
        await invoice_service.recalculate(user_id, invoice_id, session=session)
    return len(commitment_ids), len(occurrences)


async def _build_schedule(user_id: str, relationship: ThirdPartyRelationship, session=None) -> dict:
    person = await repo.people.get(user_id, relationship.person_id, session=session)
    if not person:
        raise DomainError("Pessoa não encontrada", 404)

    card_commitment = None
    if relationship.credit_card_id and relationship.direction == "receivable":
        card_commitment = await commitment_service.create_commitment(user_id, {
            "type": "purchase_installment",
            "description": f"{relationship.description} ({person.name})",
            "total_amount": relationship.total_amount,
            "installments_total": relationship.installments,
            "payment_method": "credit_card",
            "credit_card_id": relationship.credit_card_id,
            "category_id": relationship.category_id,
            "start_date": relationship.start_date,
        }, session=session, source={"module": "third_party", "ref_id": relationship.id})

    ctype = "third_party_receivable" if relationship.direction == "receivable" else "third_party_payable"
    tp_commitment = await commitment_service.create_commitment(user_id, {
        "type": ctype,
        "description": f"{person.name} · {relationship.description}",
        "total_amount": relationship.total_amount,
        "installments_total": relationship.installments,
        "payment_method": "account",
        "person_id": relationship.person_id,
        "category_id": relationship.category_id,
        "start_date": relationship.start_date,
    }, session=session, source={"module": "third_party", "ref_id": relationship.id},
        linked_commitment_id=card_commitment.id if card_commitment else None)

    if card_commitment:
        await repo.commitments.update(user_id, card_commitment.id, {
            "linked_commitment_id": tp_commitment.id,
            "person_id": relationship.person_id,
            "updated_at": now_utc(),
        }, session=session)
        await repo.occurrences.update_many(
            user_id, {"commitment_id": card_commitment.id}, {
                "refs.person_id": relationship.person_id,
                "detail.third_party_responsible": True,
                "detail.third_party_id": relationship.id,
                "updated_at": now_utc(),
            }, session=session)

    await repo.third_parties.update(user_id, relationship.id, {
        "commitment_id": tp_commitment.id,
        "card_commitment_id": card_commitment.id if card_commitment else None,
        "updated_at": now_utc(),
    }, session=session)
    relationship.commitment_id = tp_commitment.id
    relationship.card_commitment_id = card_commitment.id if card_commitment else None
    return {"third_party_id": relationship.id,
            "commitment_id": tp_commitment.id,
            "card_commitment_id": card_commitment.id if card_commitment else None}


async def create(user_id: str, payload: dict, session=None) -> dict:
    payload = _validated(payload)
    if not payload.get("person_id"):
        raise DomainError("Selecione a pessoa.", 422)
    await assert_owned(user_id, {"person_id": payload["person_id"],
                                "credit_card_id": payload.get("credit_card_id"),
                                "category_id": payload.get("category_id")}, session=session)

    relationship = ThirdPartyRelationship(
        user_id=user_id,
        person_id=payload["person_id"],
        direction=payload["direction"],
        description=payload["description"],
        total_amount=payload["total_amount"],
        installments=payload["installments"],
        credit_card_id=payload.get("credit_card_id"),
        category_id=payload.get("category_id"),
        start_date=payload.get("start_date"),
    )
    await repo.third_parties.insert(relationship, session=session)
    return await _build_schedule(user_id, relationship, session=session)


async def update(user_id: str, relationship_id: str, payload: dict, session=None) -> dict:
    rel = await repo.third_parties.get(user_id, relationship_id, session=session)
    if not rel:
        raise DomainError("Registro de terceiro não encontrado.", 404)
    if rel.status != "open":
        raise DomainError("Somente registros abertos podem ser corrigidos.", 409)

    payload = _validated(payload, partial=True)
    allowed = {
        "person_id", "direction", "description", "total_amount", "installments",
        "credit_card_id", "category_id", "start_date",
    }
    unknown = set(payload) - allowed
    if unknown:
        raise DomainError(f"Campos não editáveis: {', '.join(sorted(unknown))}", 422)

    person_id = payload.get("person_id", rel.person_id)
    credit_card_id = payload.get("credit_card_id", rel.credit_card_id)
    category_id = payload.get("category_id", rel.category_id)
    await assert_owned(user_id, {"person_id": person_id,
                                "credit_card_id": credit_card_id,
                                "category_id": category_id}, session=session)

    await _remove_schedule(user_id, rel, session=session, delete_relationship=False)
    changes = {
        **payload,
        "person_id": person_id,
        "credit_card_id": credit_card_id,
        "category_id": category_id,
        "commitment_id": None,
        "card_commitment_id": None,
        "updated_at": now_utc(),
    }
    await repo.third_parties.update(user_id, rel.id, changes, session=session)
    updated = await repo.third_parties.get(user_id, rel.id, session=session)
    return await _build_schedule(user_id, updated, session=session)


async def delete(user_id: str, relationship_id: str, session=None) -> dict:
    rel = await repo.third_parties.get(user_id, relationship_id, session=session)
    if not rel:
        raise DomainError("Registro de terceiro não encontrado.", 404)
    commitments, occurrences = await _remove_schedule(
        user_id, rel, session=session, delete_relationship=True)
    return {"ok": True, "third_party_id": relationship_id,
            "commitments_deleted": commitments, "occurrences_deleted": occurrences}


async def summary(user_id: str) -> dict:
    relationships = await repo.third_parties.find(user_id, {})
    out = []
    for rel in relationships:
        occs = await repo.occurrences.find(user_id, {"commitment_id": rel.commitment_id})
        active = [o for o in occs if o.state != "cancelled"]
        total = sum(o.amount for o in active)
        paid = sum(o.paid_amount for o in active)
        person = await repo.people.get(user_id, rel.person_id)
        first_due = min((o.due_date for o in active), default=None)
        out.append({
            "id": rel.id,
            "person": person.name if person else "",
            "person_id": rel.person_id,
            "direction": rel.direction,
            "description": rel.description,
            "total": round(total, 2),
            "total_amount": rel.total_amount,
            "paid": round(paid, 2),
            "pending": round(total - paid, 2),
            "installments": rel.installments,
            "credit_card_id": rel.credit_card_id,
            "category_id": rel.category_id,
            "start_date": rel.start_date.isoformat() if rel.start_date else None,
            "first_due_date": first_due.isoformat() if first_due else None,
            "commitment_id": rel.commitment_id,
            "card_commitment_id": rel.card_commitment_id,
            "status": rel.status,
            "editable": rel.status == "open" and paid == 0,
        })
    receivable = round(sum(r["pending"] for r in out if r["direction"] == "receivable"), 2)
    payable = round(sum(r["pending"] for r in out if r["direction"] == "payable"), 2)
    return {"items": out, "total_receivable": receivable, "total_payable": payable}
