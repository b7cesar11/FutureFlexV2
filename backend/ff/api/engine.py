"""Motor financeiro: compromissos, ocorrencias, faturas, transacoes e visoes."""
from fastapi import APIRouter, Depends, Header, HTTPException, Query

from ..core.db import UnitOfWork
from ..core.deps import current_user_id
from ..domain import month as month_rules
from ..domain import status as st
from ..domain.calendar_rules import competence_of, today_utc
from ..models.base import stringify_ids
from ..repositories import registry as repo
from ..services import (commitment_service, month_service, payment_service,
                        simulation_service, third_party_service)

router = APIRouter(tags=["motor"])


def _serialize(model) -> dict:
    data = stringify_ids(model.model_dump())
    data["id"] = model.id
    data.pop("user_id", None)
    return data


# ------------------------------------------------------------------ compromissos

@router.post("/commitments")
async def create_commitment(payload: dict, user_id: str = Depends(current_user_id)):
    async with UnitOfWork() as uow:
        commitment = await commitment_service.create_commitment(user_id, payload,
                                                                session=uow.session)
    return _serialize(commitment)


@router.get("/commitments")
async def list_commitments(status: str | None = None, frozen: bool | None = None,
                           user_id: str = Depends(current_user_id)):
    filters = {}
    if status:
        filters["status"] = status
    if frozen is not None:
        filters["frozen"] = frozen
    items = await repo.commitments.find(user_id, filters, sort=[("created_at", -1)])
    return [_serialize(i) for i in items]


@router.get("/commitments/{commitment_id}")
async def commitment_detail(commitment_id: str, user_id: str = Depends(current_user_id)):
    commitment = await repo.commitments.get(user_id, commitment_id)
    if not commitment:
        raise HTTPException(status_code=404, detail="Compromisso não encontrado")
    occurrences = await repo.occurrences.find(user_id, {"commitment_id": commitment_id},
                                              sort=[("competence", 1)])
    today = today_utc()
    current = competence_of(today)
    for o in occurrences:
        o.status = st.derive(o, today, current)
    active = [o for o in occurrences if o.state != "cancelled"]
    paid = [o for o in active if o.status == st.PAID]
    remaining = round(sum(o.amount - o.paid_amount for o in active), 2)
    linked = None
    if commitment.linked_commitment_id:
        other = await repo.commitments.get(user_id, commitment.linked_commitment_id)
        if other:
            linked = {"id": other.id, "type": other.type, "description": other.description,
                      "direction": other.direction, "total_amount": other.total_amount}
    person = (await repo.people.get(user_id, commitment.person_id)
              if commitment.person_id else None)
    card = (await repo.credit_cards.get(user_id, commitment.credit_card_id)
            if commitment.credit_card_id else None)
    category = (await repo.categories.get(user_id, commitment.category_id)
                if commitment.category_id else None)
    return {
        **_serialize(commitment),
        "current_installment": len(paid) + 1 if commitment.installments_total else None,
        "paid_count": len(paid),
        "remaining_amount": remaining,
        "linked_commitment": linked,
        "third_party_responsible": bool(linked and commitment.type == "purchase_installment"),
        "person": {"id": person.id, "name": person.name} if person else None,
        "credit_card": {"id": card.id, "name": card.name} if card else None,
        "category": {"id": category.id, "name": category.name} if category else None,
        "occurrences": [month_rules.serialize_item(o) for o in occurrences],
    }


@router.post("/commitments/{commitment_id}/freeze")
async def freeze(commitment_id: str, user_id: str = Depends(current_user_id)):
    async with UnitOfWork() as uow:
        return await commitment_service.freeze(user_id, commitment_id, True, session=uow.session)


@router.post("/commitments/{commitment_id}/unfreeze")
async def unfreeze(commitment_id: str, user_id: str = Depends(current_user_id)):
    async with UnitOfWork() as uow:
        return await commitment_service.freeze(user_id, commitment_id, False, session=uow.session)


@router.delete("/commitments/{commitment_id}")
async def cancel_commitment(commitment_id: str, user_id: str = Depends(current_user_id)):
    async with UnitOfWork() as uow:
        return await commitment_service.cancel(user_id, commitment_id, session=uow.session)


@router.post("/commitments/materialize")
async def materialize_all(user_id: str = Depends(current_user_id)):
    async with UnitOfWork() as uow:
        return await commitment_service.materialize_all(user_id, session=uow.session)


# ------------------------------------------------------------------ ocorrencias

@router.get("/occurrences")
async def list_occurrences(competence: str | None = None, group: str | None = None,
                           status: str | None = None, person_id: str | None = None,
                           user_id: str = Depends(current_user_id)):
    filters = {}
    if competence:
        filters["competence"] = competence
    if group:
        filters["origin_group"] = group
    if person_id:
        filters["refs.person_id"] = person_id
    items = await repo.occurrences.find(user_id, filters, sort=[("due_date", 1)])
    today = today_utc()
    current = competence_of(today)
    for o in items:
        o.status = st.derive(o, today, current)
    if status:
        items = [o for o in items if o.status == status]
    return [month_rules.serialize_item(o) for o in items]


@router.post("/occurrences/{occurrence_id}/pay")
async def pay_occurrence(occurrence_id: str, payload: dict,
                         idempotency_key: str | None = Header(default=None,
                                                              alias="Idempotency-Key"),
                         user_id: str = Depends(current_user_id)):
    async with UnitOfWork() as uow:
        return await payment_service.pay_occurrence(user_id, occurrence_id, payload,
                                                    idempotency_key, session=uow.session)


# ------------------------------------------------------------------ faturas

@router.get("/invoices")
async def list_invoices(credit_card_id: str | None = None, competence: str | None = None,
                        user_id: str = Depends(current_user_id)):
    filters = {}
    if credit_card_id:
        filters["credit_card_id"] = credit_card_id
    if competence:
        filters["competence"] = competence
    items = await repo.invoices.find(user_id, filters, sort=[("competence", 1)])
    return [_serialize(i) for i in items]


@router.get("/invoices/{invoice_id}")
async def invoice_detail(invoice_id: str, user_id: str = Depends(current_user_id)):
    invoice = await repo.invoices.get(user_id, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Fatura não encontrada")
    items = await repo.occurrences.find(user_id, {"refs.invoice_id": invoice_id},
                                        sort=[("due_date", 1)])
    today = today_utc()
    current = competence_of(today)
    for o in items:
        o.status = st.derive(o, today, current)
    card = await repo.credit_cards.get(user_id, invoice.credit_card_id)
    return {**_serialize(invoice),
            "credit_card": {"id": card.id, "name": card.name} if card else None,
            "items": [month_rules.serialize_item(o) for o in items if o.kind != "invoice"]}


@router.post("/invoices/{invoice_id}/pay")
async def pay_invoice(invoice_id: str, payload: dict,
                      idempotency_key: str | None = Header(default=None,
                                                           alias="Idempotency-Key"),
                      user_id: str = Depends(current_user_id)):
    async with UnitOfWork() as uow:
        return await payment_service.pay_invoice(user_id, invoice_id, payload,
                                                 idempotency_key, session=uow.session)


# ------------------------------------------------------------------ transacoes

@router.get("/transactions")
async def list_transactions(competence: str | None = None, account_id: str | None = None,
                            type: str | None = None, category_id: str | None = None,
                            person_id: str | None = None, limit: int = Query(200, le=1000),
                            skip: int = 0, user_id: str = Depends(current_user_id)):
    filters = {}
    for key, value in (("competence", competence), ("account_id", account_id),
                       ("type", type), ("category_id", category_id),
                       ("person_id", person_id)):
        if value:
            filters[key] = value
    items = await repo.transactions.find(user_id, filters, sort=[("date", -1)],
                                         limit=limit, skip=skip)
    return [_serialize(i) for i in items]


@router.post("/transactions")
async def create_transaction(payload: dict,
                             idempotency_key: str | None = Header(default=None,
                                                                  alias="Idempotency-Key"),
                             user_id: str = Depends(current_user_id)):
    async with UnitOfWork() as uow:
        return await payment_service.create_transaction(user_id, payload, idempotency_key,
                                                        session=uow.session)


# ------------------------------------------------------------------ terceiros

@router.post("/third-parties")
async def create_third_party(payload: dict, user_id: str = Depends(current_user_id)):
    async with UnitOfWork() as uow:
        return await third_party_service.create(user_id, payload, session=uow.session)


@router.get("/third-parties")
async def list_third_parties(user_id: str = Depends(current_user_id)):
    return await third_party_service.summary(user_id)


# ------------------------------------------------------------------ visoes (fonte unica)

@router.get("/months/{competence}")
async def month_view(competence: str, user_id: str = Depends(current_user_id)):
    return await month_service.month_view(user_id, competence)


@router.get("/free-money")
async def free_money(user_id: str = Depends(current_user_id)):
    return await month_service.free_money(user_id)


@router.get("/projection")
async def projection(months: int = Query(24, ge=1, le=36),
                     user_id: str = Depends(current_user_id)):
    return await month_service.projection(user_id, months)


@router.get("/dashboard")
async def dashboard(user_id: str = Depends(current_user_id)):
    return await month_service.dashboard(user_id)


@router.post("/simulations")
async def simulate(payload: dict, user_id: str = Depends(current_user_id)):
    return await simulation_service.simulate(user_id, payload)
