"""Assinaturas: domínio próprio que reutiliza o motor de recorrência existente.

Uma assinatura pode opcionalmente ter um terceiro responsável pelo reembolso. A cobrança
do cartão continua sendo uma única despesa; o recebível do terceiro é criado e sincronizado
separadamente, ligado ao mesmo Commitment da assinatura.
"""
from ..core.deps import DomainError
from ..domain.calendar_rules import competence_of, today_utc
from ..domain.money import money, summed
from ..models.base import now_utc
from ..models.entities import Subscription
from ..repositories import registry as repo
from . import commitment_service
from . import subscription_reimbursement_service as reimbursement_service
from .authorization import assert_owned


def _clean_name(value) -> str:
    name = str(value or "").strip()
    if not name:
        raise DomainError("Informe o nome da assinatura.", 422)
    return name


def _amount(value) -> float:
    try:
        amount = money(value)
    except (TypeError, ValueError):
        raise DomainError("Informe um valor válido.", 422) from None
    if amount <= 0:
        raise DomainError("O valor da assinatura deve ser maior que zero.", 422)
    return amount


def _billing_day(value) -> int:
    try:
        day = int(value)
    except (TypeError, ValueError):
        raise DomainError("Dia da cobrança inválido.", 422) from None
    if day < 1 or day > 31:
        raise DomainError("Dia da cobrança deve estar entre 1 e 31.", 422)
    return day


async def create(user_id: str, payload: dict, session=None) -> dict:
    responsible_person_id = payload.get("responsible_person_id") or None
    await assert_owned(user_id, {
        "credit_card_id": payload.get("credit_card_id"),
        "account_id": payload.get("account_id"),
        "category_id": payload.get("category_id"),
        "person_id": responsible_person_id,
    }, session=session)

    name = _clean_name(payload.get("name"))
    amount = _amount(payload.get("amount"))
    periodicity = payload.get("periodicity", "monthly")
    if periodicity not in ("monthly", "yearly"):
        raise DomainError("Periodicidade inválida (monthly|yearly)", 422)
    billing_day = _billing_day(payload.get("billing_day") or today_utc().day)
    start_competence = payload.get("start_competence") or competence_of(today_utc())
    credit_card_id = payload.get("credit_card_id") or None
    account_id = payload.get("account_id") or None

    if responsible_person_id and not credit_card_id:
        raise DomainError(
            "Para um terceiro reembolsar uma assinatura, a cobrança deve estar no seu cartão de crédito.",
            422,
        )

    subscription = Subscription(
        user_id=user_id,
        name=name,
        description=payload.get("description"),
        amount=amount,
        periodicity=periodicity,
        billing_day=billing_day,
        payment_method="credit_card" if credit_card_id else "account",
        credit_card_id=credit_card_id,
        account_id=None if credit_card_id else account_id,
        category_id=payload.get("category_id"),
        responsible_person_id=responsible_person_id,
        start_competence=start_competence,
        end_competence=payload.get("end_competence"),
        status="active",
    )
    await repo.subscriptions.insert(subscription, session=session)

    commitment = await commitment_service.create_commitment(user_id, {
        "type": "subscription",
        "description": name,
        "total_amount": amount,
        "payment_method": subscription.payment_method,
        "credit_card_id": credit_card_id,
        "default_account_id": subscription.account_id,
        "category_id": payload.get("category_id"),
        "frequency": periodicity,
        "day_of_month": billing_day,
        "start_competence": start_competence,
        "end_competence": payload.get("end_competence"),
    }, session=session, source={"module": "subscription", "ref_id": subscription.id})

    await repo.subscriptions.update(
        user_id,
        subscription.id,
        {
            "commitment_id": commitment.id,
            "price_history": [{"amount": amount, "changed_at": now_utc()}],
            "updated_at": now_utc(),
        },
        session=session,
    )
    subscription.commitment_id = commitment.id

    reimbursement = {"third_party_relationship_id": None, "third_party_commitment_id": None}
    if responsible_person_id:
        reimbursement = await reimbursement_service.sync_assignment(
            user_id, subscription, responsible_person_id, session=session
        )

    return {
        "subscription_id": subscription.id,
        "commitment_id": commitment.id,
        **reimbursement,
    }


async def update(user_id: str, subscription_id: str, payload: dict, session=None) -> dict:
    subscription = await repo.subscriptions.get(user_id, subscription_id, session=session)
    if not subscription:
        raise DomainError("Assinatura não encontrada", 404)
    commitment = await repo.commitments.get(user_id, subscription.commitment_id, session=session)
    if not commitment:
        raise DomainError("Compromisso da assinatura não encontrado", 404)

    responsibility_changed = "responsible_person_id" in payload
    desired_person_id = (
        payload.get("responsible_person_id") or None
        if responsibility_changed else subscription.responsible_person_id
    )
    await assert_owned(user_id, {
        "category_id": payload.get("category_id") if "category_id" in payload else subscription.category_id,
        "person_id": desired_person_id,
    }, session=session)
    if desired_person_id and not subscription.credit_card_id:
        raise DomainError(
            "Para um terceiro reembolsar uma assinatura, ela precisa estar cobrada no seu cartão.",
            422,
        )

    doc = await repo.subscriptions.collection.find_one(
        {"_id": _oid(subscription_id)}, session=session
    )
    history = list(doc.get("price_history") or [])

    changes = {"updated_at": now_utc()}
    if "name" in payload:
        changes["name"] = _clean_name(payload.get("name"))
    if "description" in payload:
        changes["description"] = payload.get("description")
    if "category_id" in payload:
        changes["category_id"] = payload.get("category_id") or None
    if responsibility_changed:
        changes["responsible_person_id"] = desired_person_id

    new_amount = _amount(payload["amount"]) if payload.get("amount") is not None else None
    if new_amount is not None and new_amount != subscription.amount:
        changes["amount"] = new_amount
        history.append({"amount": new_amount, "changed_at": now_utc()})
        changes["price_history"] = history
    if "billing_day" in payload:
        changes["billing_day"] = _billing_day(payload.get("billing_day"))

    await repo.subscriptions.update(user_id, subscription_id, changes, session=session)

    commitment_changes = {"updated_at": now_utc()}
    if "name" in changes:
        commitment_changes["description"] = changes["name"]
    if new_amount is not None:
        commitment_changes["total_amount"] = new_amount
        commitment_changes["installment_amount"] = new_amount
    if "billing_day" in changes:
        commitment_changes["recurrence.day_of_month"] = changes["billing_day"]
    if "category_id" in changes:
        commitment_changes["category_id"] = changes["category_id"]
    await repo.commitments.update(
        user_id, commitment.id, commitment_changes, session=session
    )

    # Materialização é INSERT-ONLY para amount. Quando o preço da assinatura muda,
    # atualizamos explicitamente apenas ocorrências abertas futuras sem override.
    if new_amount is not None:
        current = competence_of(today_utc())
        await repo.occurrences.update_many(
            user_id,
            {
                "commitment_id": commitment.id,
                "competence": {"$gte": current},
                "state": "open",
                "paid_amount": 0,
                "amount_source": {"$ne": "override"},
            },
            {"amount": new_amount, "updated_at": now_utc()},
            session=session,
        )

    updated_commitment = await repo.commitments.get(
        user_id, commitment.id, session=session
    )
    await commitment_service.materialize(user_id, updated_commitment, session=session)

    updated_subscription = await repo.subscriptions.get(
        user_id, subscription_id, session=session
    )
    reimbursement = {
        "third_party_relationship_id": updated_subscription.third_party_relationship_id,
        "third_party_commitment_id": None,
    }
    if responsibility_changed or updated_subscription.third_party_relationship_id:
        reimbursement = await reimbursement_service.sync_assignment(
            user_id, updated_subscription, desired_person_id, session=session
        )

    return {
        "subscription_id": subscription_id,
        "commitment_id": commitment.id,
        **reimbursement,
    }


def _oid(value):
    from bson import ObjectId
    return ObjectId(value)


async def set_status(user_id: str, subscription_id: str, status: str, session=None) -> dict:
    """pause -> congelamento | active -> descongelamento | cancelled -> cancelamento."""
    subscription = await repo.subscriptions.get(user_id, subscription_id, session=session)
    if not subscription:
        raise DomainError("Assinatura não encontrada", 404)
    if status not in ("active", "paused", "cancelled"):
        raise DomainError("Status inválido (active|paused|cancelled)", 400)

    result = {}
    if status == "paused":
        result = await commitment_service.freeze(
            user_id, subscription.commitment_id, True,
            session=session, reason="Assinatura pausada"
        )
    elif status == "active":
        result = await commitment_service.freeze(
            user_id, subscription.commitment_id, False, session=session
        )
    else:
        result = await commitment_service.cancel(
            user_id, subscription.commitment_id, session=session
        )

    await reimbursement_service.sync_status(
        user_id, subscription, status, session=session
    )
    await repo.subscriptions.update(
        user_id,
        subscription_id,
        {
            "status": status,
            "end_competence": (
                competence_of(today_utc())
                if status == "cancelled" else subscription.end_competence
            ),
            "updated_at": now_utc(),
        },
        session=session,
    )
    return {"subscription_id": subscription_id, "status": status, **result}


def monthly_equivalent(subscription) -> float:
    return money(subscription.amount / 12) if subscription.periodicity == "yearly" \
        else money(subscription.amount)


async def list_with_metrics(user_id: str) -> dict:
    subscriptions = await repo.subscriptions.find(user_id, {}, sort=[("name", 1)])
    today = today_utc()
    items = []
    for sub in subscriptions:
        occurrences = await repo.occurrences.find(
            user_id, {"commitment_id": sub.commitment_id}, sort=[("due_date", 1)]
        )
        active = [o for o in occurrences if o.state != "cancelled"]
        future = [
            o for o in active if o.state == "open" and o.due_date.date() >= today
        ]
        paid = [o for o in active if o.state == "paid"]
        card = (
            await repo.credit_cards.get(user_id, sub.credit_card_id)
            if sub.credit_card_id else None
        )
        account = (
            await repo.accounts.get(user_id, sub.account_id)
            if sub.account_id else None
        )
        category = (
            await repo.categories.get(user_id, sub.category_id)
            if sub.category_id else None
        )
        doc = await repo.subscriptions.collection.find_one({"_id": _oid(sub.id)})
        history = [
            {"amount": h["amount"], "changed_at": h["changed_at"]}
            for h in (doc.get("price_history") or [])
        ]
        reimbursement = await reimbursement_service.metrics(user_id, sub)
        monthly = monthly_equivalent(sub)
        items.append({
            "id": sub.id,
            "name": sub.name,
            "description": sub.description,
            "amount": sub.amount,
            "periodicity": sub.periodicity,
            "billing_day": sub.billing_day,
            "status": sub.status,
            "start_competence": sub.start_competence,
            "end_competence": sub.end_competence,
            "commitment_id": sub.commitment_id,
            "category": {"id": category.id, "name": category.name} if category else None,
            "payment_source": (
                f"Cartão {card.name}" if card
                else (account.name if account else "Conta / dinheiro")
            ),
            "credit_card_id": sub.credit_card_id,
            "account_id": sub.account_id,
            "responsible_person_id": sub.responsible_person_id,
            **reimbursement,
            "monthly_equivalent": monthly,
            "annual_cost": money(monthly * 12),
            "next_charge": future[0].due_date if future else None,
            "next_charge_amount": future[0].amount if future else None,
            "next_competence": future[0].competence if future else None,
            "future_occurrences": len(future),
            "paid_occurrences": len(paid),
            "total_paid": summed(o.paid_amount for o in paid),
            "price_history": history,
            "price_increased": len(history) > 1 and history[-1]["amount"] > history[-2]["amount"],
            "previous_amount": history[-2]["amount"] if len(history) > 1 else None,
            "frozen": sub.status == "paused",
        })

    live = [i for i in items if i["status"] == "active"]
    monthly_total = summed(i["monthly_equivalent"] for i in live)
    upcoming = sorted(
        [i for i in live if i["next_charge"]], key=lambda i: i["next_charge"]
    )
    largest = max(live, key=lambda i: i["monthly_equivalent"], default=None)
    increased = [i for i in items if i["price_increased"]]
    third_party_live = [i for i in live if i["responsible_person"]]
    return {
        "items": items,
        "summary": {
            "monthly_total": monthly_total,
            "annual_total": money(monthly_total * 12),
            "active_count": len(live),
            "third_party_count": len(third_party_live),
            "third_party_pending": summed(i["reimbursement_pending"] for i in third_party_live),
            "paused_count": len([i for i in items if i["status"] == "paused"]),
            "cancelled_count": len([i for i in items if i["status"] == "cancelled"]),
            "next_charge": (
                {
                    "name": upcoming[0]["name"],
                    "date": upcoming[0]["next_charge"],
                    "amount": upcoming[0]["next_charge_amount"],
                }
                if upcoming else None
            ),
            "largest": (
                {
                    "name": largest["name"],
                    "monthly": largest["monthly_equivalent"],
                    "annual": largest["annual_cost"],
                }
                if largest else None
            ),
            "price_increases": [
                {"name": i["name"], "from": i["previous_amount"], "to": i["amount"]}
                for i in increased
            ],
        },
    }
