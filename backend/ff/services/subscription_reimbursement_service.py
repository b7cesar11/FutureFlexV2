"""Reembolso de assinatura paga no cartão do usuário por um terceiro.

A assinatura continua sendo a ÚNICA despesa do cartão. Este serviço cria apenas o lado
recebível do terceiro e o liga ao Commitment da assinatura, evitando dupla contagem.
"""
from ..core.deps import DomainError
from ..domain.calendar_rules import as_datetime, clamp_day, competence_of, today_utc
from ..domain.money import summed
from ..models.base import now_utc
from ..models.entities import ThirdPartyRelationship
from ..repositories import registry as repo
from . import commitment_service
from .authorization import assert_owned


def _first_charge_date(subscription):
    competence = subscription.start_competence or competence_of(today_utc())
    return as_datetime(clamp_day(competence, int(subscription.billing_day or 1)))


async def _relation(user_id: str, subscription, session=None):
    if not subscription.third_party_relationship_id:
        return None
    return await repo.third_parties.get(
        user_id, subscription.third_party_relationship_id, session=session
    )


async def _assert_can_replace(user_id: str, relationship, session=None) -> None:
    if not relationship or not relationship.commitment_id:
        return
    occurrences = await repo.occurrences.find(
        user_id, {"commitment_id": relationship.commitment_id}, session=session
    )
    current = competence_of(today_utc())
    if any(
        o.state == "paid"
        or (o.paid_amount or 0) > 0
        or bool(o.refs.transaction_ids)
        or o.competence < current
        for o in occurrences
    ):
        raise DomainError(
            "O responsável desta assinatura já possui histórico financeiro. "
            "Para preservar os meses anteriores, mantenha a pessoa atual e altere "
            "o responsável apenas em uma nova assinatura a partir do mês desejado.",
            409,
        )


async def _clear_card_link(user_id: str, subscription, session=None) -> None:
    if not subscription.commitment_id:
        return
    await repo.commitments.update(
        user_id,
        subscription.commitment_id,
        {"linked_commitment_id": None, "person_id": None, "updated_at": now_utc()},
        session=session,
    )
    await repo.occurrences.update_many(
        user_id,
        {"commitment_id": subscription.commitment_id},
        {
            "refs.person_id": None,
            "detail.third_party_responsible": False,
            "detail.third_party_id": None,
            "detail.subscription_reimbursement": False,
            "updated_at": now_utc(),
        },
        session=session,
    )


async def _delete_relation(user_id: str, subscription, relationship, session=None) -> None:
    await _assert_can_replace(user_id, relationship, session=session)
    if relationship.commitment_id:
        await repo.occurrences.delete_many(
            user_id, {"commitment_id": relationship.commitment_id}, session=session
        )
        await repo.commitments.delete(
            user_id, relationship.commitment_id, session=session
        )
    await repo.third_parties.delete(user_id, relationship.id, session=session)
    await _clear_card_link(user_id, subscription, session=session)
    await repo.subscriptions.update(
        user_id,
        subscription.id,
        {
            "responsible_person_id": None,
            "third_party_relationship_id": None,
            "updated_at": now_utc(),
        },
        session=session,
    )
    subscription.responsible_person_id = None
    subscription.third_party_relationship_id = None


async def _create_relation(user_id: str, subscription, person_id: str, session=None) -> dict:
    if not subscription.credit_card_id:
        raise DomainError(
            "Para outra pessoa reembolsar uma assinatura, ela precisa estar cobrada no seu cartão.",
            422,
        )
    if not subscription.commitment_id:
        raise DomainError("Compromisso da assinatura não encontrado.", 404)

    await assert_owned(
        user_id,
        {
            "person_id": person_id,
            "credit_card_id": subscription.credit_card_id,
            "category_id": subscription.category_id,
        },
        session=session,
    )
    person = await repo.people.get(user_id, person_id, session=session)
    if not person:
        raise DomainError("Pessoa não encontrada.", 404)

    relationship = ThirdPartyRelationship(
        user_id=user_id,
        person_id=person_id,
        direction="receivable",
        description=subscription.name,
        total_amount=subscription.amount,
        installments=1,
        recurring=True,
        credit_card_id=subscription.credit_card_id,
        category_id=subscription.category_id,
        start_date=_first_charge_date(subscription),
        card_commitment_id=subscription.commitment_id,
        source_module="subscription",
        source_ref_id=subscription.id,
    )
    await repo.third_parties.insert(relationship, session=session)

    receivable = await commitment_service.create_commitment(
        user_id,
        {
            "type": "third_party_receivable",
            "description": f"{person.name} · {subscription.name}",
            "total_amount": subscription.amount,
            "payment_method": "account",
            "person_id": person_id,
            "category_id": subscription.category_id,
            "start_date": relationship.start_date,
            "frequency": subscription.periodicity,
            "day_of_month": subscription.billing_day,
            "start_competence": subscription.start_competence,
            "end_competence": subscription.end_competence,
        },
        session=session,
        source={"module": "subscription_reimbursement", "ref_id": relationship.id},
        linked_commitment_id=subscription.commitment_id,
    )

    await repo.third_parties.update(
        user_id,
        relationship.id,
        {"commitment_id": receivable.id, "updated_at": now_utc()},
        session=session,
    )
    await repo.commitments.update(
        user_id,
        subscription.commitment_id,
        {
            "linked_commitment_id": receivable.id,
            "person_id": person_id,
            "updated_at": now_utc(),
        },
        session=session,
    )
    await repo.occurrences.update_many(
        user_id,
        {"commitment_id": subscription.commitment_id},
        {
            "refs.person_id": person_id,
            "detail.third_party_responsible": True,
            "detail.third_party_id": relationship.id,
            "detail.subscription_reimbursement": True,
            "updated_at": now_utc(),
        },
        session=session,
    )
    await repo.subscriptions.update(
        user_id,
        subscription.id,
        {
            "responsible_person_id": person_id,
            "third_party_relationship_id": relationship.id,
            "updated_at": now_utc(),
        },
        session=session,
    )
    subscription.responsible_person_id = person_id
    subscription.third_party_relationship_id = relationship.id

    if subscription.status == "paused":
        await commitment_service.freeze(
            user_id,
            receivable.id,
            True,
            session=session,
            reason="Assinatura pausada",
        )

    return {
        "third_party_relationship_id": relationship.id,
        "third_party_commitment_id": receivable.id,
    }


async def _sync_existing(user_id: str, subscription, relationship, session=None) -> dict:
    person = await repo.people.get(user_id, relationship.person_id, session=session)
    if not person:
        raise DomainError("Pessoa responsável não encontrada.", 404)
    receivable = await repo.commitments.get(
        user_id, relationship.commitment_id, session=session
    )
    if not receivable:
        raise DomainError("Recebível da assinatura não encontrado.", 404)

    await repo.third_parties.update(
        user_id,
        relationship.id,
        {
            "description": subscription.name,
            "total_amount": subscription.amount,
            "credit_card_id": subscription.credit_card_id,
            "category_id": subscription.category_id,
            "updated_at": now_utc(),
        },
        session=session,
    )
    await repo.commitments.update(
        user_id,
        receivable.id,
        {
            "description": f"{person.name} · {subscription.name}",
            "total_amount": subscription.amount,
            "installment_amount": subscription.amount,
            "category_id": subscription.category_id,
            "recurrence.day_of_month": subscription.billing_day,
            "recurrence.end_competence": subscription.end_competence,
            "updated_at": now_utc(),
        },
        session=session,
    )

    current = competence_of(today_utc())
    await repo.occurrences.update_many(
        user_id,
        {
            "commitment_id": receivable.id,
            "competence": {"$gte": current},
            "state": "open",
            "paid_amount": 0,
            "amount_source": {"$ne": "override"},
        },
        {"amount": subscription.amount, "updated_at": now_utc()},
        session=session,
    )
    updated = await repo.commitments.get(user_id, receivable.id, session=session)
    await commitment_service.materialize(user_id, updated, session=session)

    await repo.commitments.update(
        user_id,
        subscription.commitment_id,
        {
            "linked_commitment_id": receivable.id,
            "person_id": relationship.person_id,
            "updated_at": now_utc(),
        },
        session=session,
    )
    await repo.occurrences.update_many(
        user_id,
        {"commitment_id": subscription.commitment_id},
        {
            "refs.person_id": relationship.person_id,
            "detail.third_party_responsible": True,
            "detail.third_party_id": relationship.id,
            "detail.subscription_reimbursement": True,
            "updated_at": now_utc(),
        },
        session=session,
    )
    return {
        "third_party_relationship_id": relationship.id,
        "third_party_commitment_id": receivable.id,
    }


async def sync_assignment(user_id: str, subscription, desired_person_id, session=None) -> dict:
    desired = str(desired_person_id) if desired_person_id else None
    relationship = await _relation(user_id, subscription, session=session)

    if desired and not subscription.credit_card_id:
        raise DomainError(
            "Para outra pessoa reembolsar uma assinatura, selecione um cartão de crédito.",
            422,
        )
    if desired:
        await assert_owned(user_id, {"person_id": desired}, session=session)

    if relationship:
        current_person = str(relationship.person_id)
        if desired == current_person:
            subscription.responsible_person_id = relationship.person_id
            return await _sync_existing(user_id, subscription, relationship, session=session)
        await _delete_relation(user_id, subscription, relationship, session=session)

    if desired:
        return await _create_relation(user_id, subscription, desired, session=session)
    return {"third_party_relationship_id": None, "third_party_commitment_id": None}


async def sync_status(user_id: str, subscription, status: str, session=None) -> None:
    relationship = await _relation(user_id, subscription, session=session)
    if not relationship or not relationship.commitment_id:
        return
    if status == "paused":
        await commitment_service.freeze(
            user_id,
            relationship.commitment_id,
            True,
            session=session,
            reason="Assinatura pausada",
        )
    elif status == "active":
        await commitment_service.freeze(
            user_id, relationship.commitment_id, False, session=session
        )
        if relationship.status != "open":
            await repo.third_parties.update(
                user_id,
                relationship.id,
                {"status": "open", "updated_at": now_utc()},
                session=session,
            )
    elif status == "cancelled":
        await commitment_service.cancel(
            user_id, relationship.commitment_id, session=session
        )
        await repo.third_parties.update(
            user_id,
            relationship.id,
            {"status": "cancelled", "updated_at": now_utc()},
            session=session,
        )


async def metrics(user_id: str, subscription, session=None) -> dict:
    relationship = await _relation(user_id, subscription, session=session)
    person = (
        await repo.people.get(user_id, subscription.responsible_person_id, session=session)
        if subscription.responsible_person_id else None
    )
    if not relationship or not relationship.commitment_id:
        return {
            "responsible_person": ({"id": person.id, "name": person.name} if person else None),
            "third_party_relationship_id": None,
            "third_party_commitment_id": None,
            "reimbursement_pending": 0.0,
            "reimbursement_received": 0.0,
        }

    occurrences = await repo.occurrences.find(
        user_id, {"commitment_id": relationship.commitment_id}, session=session
    )
    current = competence_of(today_utc())
    due = [
        o for o in occurrences
        if o.state != "cancelled" and not o.frozen and o.competence <= current
    ]
    pending = summed(max(o.amount - o.paid_amount, 0) for o in due)
    received = summed(o.paid_amount for o in occurrences if o.paid_amount)
    return {
        "responsible_person": ({"id": person.id, "name": person.name} if person else None),
        "third_party_relationship_id": relationship.id,
        "third_party_commitment_id": relationship.commitment_id,
        "reimbursement_pending": pending,
        "reimbursement_received": received,
    }
