"""Terceiros: dois compromissos com relacionamento explicito, sem dupla contagem.

Ana compra R$600 no meu cartao em 6x:
  A) purchase_installment (outflow)  -> minha obrigacao com o banco / fatura
  B) third_party_receivable (inflow) -> obrigacao da Ana comigo
Sao ligados por linked_commitment_id. B e ENTRADA esperada, nunca despesa.
"""
from ..core.deps import DomainError
from ..domain.calendar_rules import competence_of
from ..models.base import now_utc
from ..models.entities import ThirdPartyRelationship
from ..repositories import registry as repo
from . import commitment_service
from .authorization import assert_owned


async def create(user_id: str, payload: dict, session=None) -> dict:
    await assert_owned(user_id, {"person_id": payload["person_id"],
                                "credit_card_id": payload.get("credit_card_id"),
                                "category_id": payload.get("category_id")}, session=session)
    direction = payload["direction"]
    if direction not in ("receivable", "payable"):
        raise DomainError("Direção inválida (receivable|payable)", 400)

    person = await repo.people.get(user_id, payload["person_id"], session=session)
    if not person:
        raise DomainError("Pessoa não encontrada", 404)

    relationship = ThirdPartyRelationship(
        user_id=user_id, person_id=payload["person_id"], direction=direction,
        description=payload["description"], total_amount=float(payload["total_amount"]),
        installments=int(payload.get("installments") or 1),
        credit_card_id=payload.get("credit_card_id"))
    await repo.third_parties.insert(relationship, session=session)

    card_commitment = None
    if payload.get("credit_card_id") and direction == "receivable":
        # COMPROMISSO A — minha obrigacao com a instituicao financeira
        card_commitment = await commitment_service.create_commitment(user_id, {
            "type": "purchase_installment",
            "description": f"{payload['description']} ({person.name})",
            "total_amount": payload["total_amount"],
            "installments_total": relationship.installments,
            "payment_method": "credit_card",
            "credit_card_id": payload["credit_card_id"],
            "category_id": payload.get("category_id"),
            "start_date": payload.get("start_date"),
        }, session=session,
            source={"module": "third_party", "ref_id": relationship.id})

    # COMPROMISSO B — obrigacao do terceiro comigo (ou minha com ele)
    ctype = "third_party_receivable" if direction == "receivable" else "third_party_payable"
    tp_commitment = await commitment_service.create_commitment(user_id, {
        "type": ctype,
        "description": f"{person.name} · {payload['description']}",
        "total_amount": payload["total_amount"],
        "installments_total": relationship.installments,
        "payment_method": "account",
        "person_id": payload["person_id"],
        "category_id": payload.get("category_id"),
        "start_date": payload.get("start_date"),
    }, session=session, source={"module": "third_party", "ref_id": relationship.id},
        linked_commitment_id=card_commitment.id if card_commitment else None)

    if card_commitment:
        await repo.commitments.update(user_id, card_commitment.id,
                                     {"linked_commitment_id": tp_commitment.id,
                                      "person_id": payload["person_id"],
                                      "updated_at": now_utc()}, session=session)
        await repo.occurrences.update_many(
            user_id, {"commitment_id": card_commitment.id},
            {"refs.person_id": payload["person_id"],
             "detail.third_party_responsible": True,
             "detail.third_party_id": relationship.id}, session=session)

    await repo.third_parties.update(user_id, relationship.id, {
        "commitment_id": tp_commitment.id,
        "card_commitment_id": card_commitment.id if card_commitment else None,
        "updated_at": now_utc()}, session=session)

    return {"third_party_id": relationship.id,
            "commitment_id": tp_commitment.id,
            "card_commitment_id": card_commitment.id if card_commitment else None}


async def summary(user_id: str) -> dict:
    relationships = await repo.third_parties.find(user_id, {})
    out = []
    for rel in relationships:
        occs = await repo.occurrences.find(user_id, {"commitment_id": rel.commitment_id})
        active = [o for o in occs if o.state != "cancelled"]
        total = sum(o.amount for o in active)
        paid = sum(o.paid_amount for o in active)
        person = await repo.people.get(user_id, rel.person_id)
        out.append({
            "id": rel.id, "person": person.name if person else "", "person_id": rel.person_id,
            "direction": rel.direction, "description": rel.description,
            "total": round(total, 2), "paid": round(paid, 2),
            "pending": round(total - paid, 2), "installments": rel.installments,
            "credit_card_id": rel.credit_card_id, "commitment_id": rel.commitment_id,
            "card_commitment_id": rel.card_commitment_id, "status": rel.status,
        })
    receivable = round(sum(r["pending"] for r in out if r["direction"] == "receivable"), 2)
    payable = round(sum(r["pending"] for r in out if r["direction"] == "payable"), 2)
    return {"items": out, "total_receivable": receivable, "total_payable": payable}
