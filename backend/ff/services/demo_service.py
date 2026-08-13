"""Conta demo com dados financeiros de exemplo. Idempotente: roda no startup sem duplicar."""
import logging
import os

from ..core.db import UnitOfWork, db
from ..core.security import hash_password, verify_password
from ..domain.calendar_rules import competence_of, today_utc
from ..models.base import now_utc
from ..models.entities import Account, CreditCard, Person, User, UserProfile
from ..repositories import registry as repo
from . import (commitment_service, seed_service, subscription_service,
               third_party_service)

logger = logging.getLogger("future_flex.demo")

DEMO_EMAIL = "demo@futureflex.dev"
DEMO_PASSWORD = "Demo@2026"


async def ensure_demo_user() -> str | None:
    existing = await db.users.find_one({"email": DEMO_EMAIL})
    if existing:
        if not verify_password(DEMO_PASSWORD, existing.get("password_hash") or ""):
            await db.users.update_one(
                {"_id": existing["_id"]},
                {"$set": {"password_hash": hash_password(DEMO_PASSWORD),
                          "updated_at": now_utc()}})
        return str(existing["_id"])

    user = User(email=DEMO_EMAIL, password_hash=hash_password(DEMO_PASSWORD),
                auth_providers=["password"], profile=UserProfile(name="Conta Demo"))
    result = await db.users.insert_one(user.to_mongo())
    user_id = str(result.inserted_id)
    await seed_service.seed_user_defaults(user_id)
    await _seed_financial_data(user_id)
    logger.info("Conta demo criada: %s", DEMO_EMAIL)
    return user_id


async def _seed_financial_data(user_id: str):
    itau = Account(user_id=user_id, name="Itaú", type="checking", opening_balance=5200,
                   current_balance=5200, color="#F97316")
    nubank_account = Account(user_id=user_id, name="Nubank Conta", type="checking",
                             opening_balance=1800, current_balance=1800, color="#8B5CF6")
    card = CreditCard(user_id=user_id, name="Nubank", limit=9000, closing_day=28, due_day=5)
    ana = Person(user_id=user_id, name="Ana")

    async with UnitOfWork() as uow:
        for model, repository in ((itau, repo.accounts), (nubank_account, repo.accounts),
                                  (card, repo.credit_cards), (ana, repo.people)):
            await repository.insert(model, session=uow.session)

    categories = await repo.categories.find(user_id, {})
    by_name = {c.name: c.id for c in categories}
    day = min(today_utc().day, 10)

    async with UnitOfWork() as uow:
        await commitment_service.create_commitment(user_id, {
            "type": "purchase_installment", "description": "iPhone 15",
            "total_amount": 3600, "installments_total": 12,
            "payment_method": "credit_card", "credit_card_id": card.id,
            "category_id": by_name.get("Outros")}, session=uow.session)

    async with UnitOfWork() as uow:
        await commitment_service.create_commitment(user_id, {
            "type": "fixed_expense", "description": "Aluguel", "total_amount": 1800,
            "payment_method": "account", "day_of_month": 10,
            "default_account_id": itau.id,
            "category_id": by_name.get("Moradia")}, session=uow.session)

    async with UnitOfWork() as uow:
        await subscription_service.create(user_id, {
            "name": "Spotify", "amount": 21.90, "periodicity": "monthly",
            "billing_day": 15, "credit_card_id": card.id,
            "category_id": by_name.get("Assinaturas")}, session=uow.session)

    async with UnitOfWork() as uow:
        await subscription_service.create(user_id, {
            "name": "Netflix", "amount": 55.90, "periodicity": "monthly",
            "billing_day": 20, "credit_card_id": card.id,
            "category_id": by_name.get("Assinaturas")}, session=uow.session)

    async with UnitOfWork() as uow:
        await subscription_service.create(user_id, {
            "name": "YouTube Premium", "amount": 24.90, "periodicity": "monthly",
            "billing_day": 8, "credit_card_id": card.id,
            "category_id": by_name.get("Assinaturas")}, session=uow.session)

    async with UnitOfWork() as uow:
        await commitment_service.create_commitment(user_id, {
            "type": "recurring_income", "description": "Salário", "total_amount": 5400,
            "payment_method": "account", "day_of_month": 5,
            "default_account_id": itau.id,
            "category_id": by_name.get("Salário")}, session=uow.session)

    async with UnitOfWork() as uow:
        await third_party_service.create(user_id, {
            "person_id": ana.id, "direction": "receivable",
            "description": "Compra no meu cartão", "total_amount": 600, "installments": 6,
            "credit_card_id": card.id,
            "category_id": by_name.get("Terceiros")}, session=uow.session)
