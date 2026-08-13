"""Area de Congelados: usa EXCLUSIVAMENTE o mecanismo de congelamento existente."""
from ..domain.calendar_rules import competence_of, today_utc
from ..domain.money import summed
from ..repositories import registry as repo


async def list_frozen(user_id: str) -> dict:
    commitments = await repo.commitments.find(user_id, {"frozen": True},
                                              sort=[("frozen_at", -1)])
    today = today_utc()
    current = competence_of(today)
    items = []
    for commitment in commitments:
        occurrences = await repo.occurrences.find(user_id, {"commitment_id": commitment.id},
                                                  sort=[("due_date", 1)])
        future = [o for o in occurrences
                  if o.state == "open" and o.competence >= current]
        monthly = future[0].amount if future else commitment.installment_amount
        card = (await repo.credit_cards.get(user_id, commitment.credit_card_id)
                if commitment.credit_card_id else None)
        person = (await repo.people.get(user_id, commitment.person_id)
                  if commitment.person_id else None)
        subscription = None
        if (commitment.source or {}).get("module") == "subscription":
            subscription = await repo.subscriptions.get(
                user_id, (commitment.source or {}).get("ref_id"))
        items.append({
            "commitment_id": commitment.id,
            "name": commitment.description,
            "type": commitment.type,
            "direction": commitment.direction,
            "origin_group": commitment.origin_group,
            "amount": commitment.total_amount,
            "monthly_impact": monthly,
            "future_occurrences": len(future),
            "released_total": summed(o.amount for o in future),
            "frozen_at": commitment.frozen_at,
            "reason": commitment.freeze_reason,
            "payment_source": (f"Cartão {card.name}" if card else "Conta / dinheiro"),
            "person": person.name if person else None,
            "is_subscription": subscription is not None,
            "subscription_id": subscription.id if subscription else None,
            "history_preserved": len([o for o in occurrences if o.state == "paid"]),
        })
    return {
        "items": items,
        "summary": {
            "count": len(items),
            "monthly_released": summed(i["monthly_impact"] for i in items
                                       if i["direction"] == "outflow"),
            "total_released": summed(i["released_total"] for i in items
                                     if i["direction"] == "outflow"),
        },
    }
