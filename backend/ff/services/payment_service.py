"""Pagamentos. UNICO lugar que move saldo de conta.

Occurrence -> Payment Service -> Transaction -> Account
A conta e escolhida NO MOMENTO do pagamento (nunca herdada obrigatoriamente do compromisso).
"""
from datetime import datetime, timezone

from ..core.deps import DomainError
from ..domain.calendar_rules import competence_of
from ..domain.money import money, summed, to_cents
from ..models.base import now_utc
from ..models.entities import Transaction
from ..repositories import registry as repo
from . import idempotency, invoice_service
from .authorization import assert_owned


def _parse_date(value) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value


async def _apply_to_account(user_id: str, account_id: str, delta: float, session=None):
    account = await repo.accounts.get(user_id, account_id, session=session)
    if not account:
        raise DomainError("Conta não encontrada", 404)
    new_balance = summed([account.current_balance, delta])
    await repo.accounts.update(user_id, account_id,
                               {"current_balance": new_balance, "updated_at": now_utc()},
                               session=session)
    return new_balance


async def pay_occurrence(user_id: str, occurrence_id: str, payload: dict,
                         idempotency_key: str | None = None, session=None) -> dict:
    await idempotency.claim(user_id, idempotency_key, "pay_occurrence", session=session)

    occ = await repo.occurrences.get(user_id, occurrence_id, session=session)
    if not occ:
        raise DomainError("Ocorrência não encontrada", 404)
    if occ.kind == "invoice":
        raise DomainError("Use o pagamento de fatura para esta ocorrência", 400)
    if occ.state == "paid":
        raise DomainError("Ocorrência já paga", 409)
    if occ.state == "cancelled":
        raise DomainError("Ocorrência cancelada", 409)
    if occ.refs.invoice_id:
        raise DomainError(
            "Esta parcela compõe uma fatura de cartão. Pague a fatura correspondente.", 400)

    account_id = payload.get("account_id")
    if not account_id:
        raise DomainError("Informe a conta utilizada no pagamento", 400)
    await assert_owned(user_id, {"account_id": account_id}, session=session)

    amount = money(payload.get("amount") or (occ.amount - occ.paid_amount))
    if amount <= 0:
        raise DomainError("Valor de pagamento inválido", 400)
    paid_at = _parse_date(payload.get("date"))

    delta = amount if occ.direction == "inflow" else -amount
    tx = Transaction(
        user_id=user_id,
        type="income" if occ.direction == "inflow" else "commitment_payment",
        amount=amount, date=paid_at, competence=competence_of(paid_at.date()),
        account_id=account_id, category_id=occ.refs.category_id,
        occurrence_id=occ.id, person_id=occ.refs.person_id,
        description=payload.get("description") or occ.label,
        source=payload.get("source", "manual"), idempotency_key=(
            f"{user_id}:pay_occurrence:{idempotency_key}" if idempotency_key else None),
    )
    await repo.transactions.insert(tx, session=session)
    balance = await _apply_to_account(user_id, account_id, delta, session=session)

    total_paid = summed([occ.paid_amount, amount])
    fully = to_cents(total_paid) >= to_cents(occ.amount)
    await repo.occurrences.update(user_id, occ.id, {
        "paid_amount": total_paid,
        "paid_at": paid_at if fully else None,
        "state": "paid" if fully else "open",
        "refs.account_id": account_id,
        "refs.transaction_ids": (occ.refs.transaction_ids or []) + [tx.id],
        "updated_at": now_utc(),
    }, session=session)

    if occ.commitment_id and fully:
        await _complete_commitment_if_done(user_id, occ.commitment_id, session=session)

    await idempotency.store_result(user_id, idempotency_key, "pay_occurrence", tx.id,
                                  session=session)
    return {"occurrence_id": occ.id, "transaction_id": tx.id, "amount": amount,
            "account_balance": balance, "state": "paid" if fully else "open"}


async def _complete_commitment_if_done(user_id: str, commitment_id: str, session=None):
    open_count = await repo.occurrences.count(user_id,
                                              {"commitment_id": commitment_id, "state": "open"},
                                              session=session)
    commitment = await repo.commitments.get(user_id, commitment_id, session=session)
    if commitment and commitment.installments_total and open_count == 0:
        await repo.commitments.update(user_id, commitment_id,
                                     {"status": "completed", "updated_at": now_utc()},
                                     session=session)


async def pay_invoice(user_id: str, invoice_id: str, payload: dict,
                      idempotency_key: str | None = None, session=None) -> dict:
    await idempotency.claim(user_id, idempotency_key, "pay_invoice", session=session)

    invoice = await repo.invoices.get(user_id, invoice_id, session=session)
    if not invoice:
        raise DomainError("Fatura não encontrada", 404)
    if invoice.status == "paid":
        raise DomainError("Fatura já paga", 409)

    account_id = payload.get("account_id")
    if not account_id:
        raise DomainError("Informe a conta utilizada no pagamento da fatura", 400)
    await assert_owned(user_id, {"account_id": account_id}, session=session)

    outstanding = summed([invoice.total, -invoice.paid_amount])
    amount = money(payload.get("amount") or outstanding)
    if amount <= 0 or to_cents(amount) > to_cents(outstanding):
        raise DomainError("Valor de pagamento inválido para esta fatura", 400)
    paid_at = _parse_date(payload.get("date"))

    tx = Transaction(user_id=user_id, type="invoice_payment", amount=amount, date=paid_at,
                     competence=competence_of(paid_at.date()), account_id=account_id,
                     invoice_id=invoice.id, credit_card_id=invoice.credit_card_id,
                     description=payload.get("description") or f"Pagamento fatura {invoice.competence}",
                     source=payload.get("source", "manual"),
                     idempotency_key=(f"{user_id}:pay_invoice:{idempotency_key}"
                                      if idempotency_key else None))
    await repo.transactions.insert(tx, session=session)
    balance = await _apply_to_account(user_id, account_id, -amount, session=session)

    total_paid = summed([invoice.paid_amount, amount])
    fully = to_cents(total_paid) >= to_cents(invoice.total)
    await repo.invoices.update(user_id, invoice.id, {
        "paid_amount": total_paid, "status": "paid" if fully else "partially_paid",
        "updated_at": now_utc()}, session=session)

    items = await repo.occurrences.find(user_id, {"refs.invoice_id": invoice.id},
                                        session=session)
    updated = 0
    for occ in items:
        if occ.state == "cancelled":
            continue
        if fully:
            await repo.occurrences.update(user_id, occ.id, {
                "paid_amount": occ.amount, "paid_at": paid_at, "state": "paid",
                "refs.account_id": account_id if occ.kind == "invoice" else None,
                "refs.transaction_ids": (occ.refs.transaction_ids or []) + (
                    [tx.id] if occ.kind == "invoice" else []),
                "updated_at": now_utc()}, session=session)
            updated += 1
            if occ.commitment_id:
                await _complete_commitment_if_done(user_id, occ.commitment_id, session=session)
        elif occ.kind == "invoice":
            await repo.occurrences.update(user_id, occ.id, {
                "paid_amount": total_paid,
                "refs.transaction_ids": (occ.refs.transaction_ids or []) + [tx.id],
                "updated_at": now_utc()}, session=session)

    await idempotency.store_result(user_id, idempotency_key, "pay_invoice", tx.id,
                                  session=session)
    return {"invoice_id": invoice.id, "transaction_id": tx.id, "amount": amount,
            "account_balance": balance, "status": "paid" if fully else "partially_paid",
            "items_settled": updated}


async def create_transaction(user_id: str, payload: dict, idempotency_key: str | None = None,
                             session=None) -> dict:
    """Transacao avulsa (fato real) — inclui transferencia entre contas."""
    await idempotency.claim(user_id, idempotency_key, "create_transaction", session=session)
    ttype = payload["type"]
    if ttype not in ("expense", "income", "transfer"):
        raise DomainError("Tipo de transação inválido para lançamento manual", 400)
    await assert_owned(user_id, {"account_id": payload.get("account_id"),
                                "to_account_id": payload.get("to_account_id"),
                                "category_id": payload.get("category_id"),
                                "person_id": payload.get("person_id")}, session=session)
    amount = money(payload["amount"])
    when = _parse_date(payload.get("date"))
    tx = Transaction(user_id=user_id, type=ttype, amount=amount, date=when,
                     competence=competence_of(when.date()),
                     account_id=payload.get("account_id"),
                     to_account_id=payload.get("to_account_id"),
                     category_id=payload.get("category_id"),
                     person_id=payload.get("person_id"),
                     description=payload.get("description", ""),
                     source=payload.get("source", "manual"),
                     idempotency_key=(f"{user_id}:create_transaction:{idempotency_key}"
                                      if idempotency_key else None))
    await repo.transactions.insert(tx, session=session)

    if ttype == "transfer":
        if not payload.get("account_id") or not payload.get("to_account_id"):
            raise DomainError("Transferência exige conta de origem e destino", 400)
        await _apply_to_account(user_id, payload["account_id"], -amount, session=session)
        await _apply_to_account(user_id, payload["to_account_id"], amount, session=session)
    else:
        if not payload.get("account_id"):
            raise DomainError("Informe a conta da transação", 400)
        delta = amount if ttype == "income" else -amount
        await _apply_to_account(user_id, payload["account_id"], delta, session=session)

    await idempotency.store_result(user_id, idempotency_key, "create_transaction", tx.id,
                                  session=session)
    return {"transaction_id": tx.id, "amount": amount}
