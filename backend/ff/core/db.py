from motor.motor_asyncio import AsyncIOMotorClient

from .config import DB_NAME, MONGO_URL

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]


class UnitOfWork:
    """Fronteira transacional unica. Todas as escritas de um caso de uso usam self.session."""

    def __init__(self):
        self.session = None

    async def __aenter__(self):
        self.session = await client.start_session()
        self.session.start_transaction()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        try:
            if exc_type is not None:
                await self.session.abort_transaction()
            else:
                await self.session.commit_transaction()
        finally:
            await self.session.end_session()
            self.session = None
        return False


async def ensure_indexes():
    await db.users.create_index("email", unique=True, sparse=True)
    await db.users.create_index("google_sub", unique=True,
                                partialFilterExpression={"google_sub": {"$type": "string"}})
    await db.user_sessions.create_index("session_token", unique=True)
    await db.login_attempts.create_index("identifier")
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)

    await db.occurrences.create_index([("user_id", 1), ("competence", 1), ("state", 1),
                                       ("frozen", 1)])
    await db.occurrences.create_index([("user_id", 1), ("due_date", 1), ("state", 1)])
    await db.occurrences.create_index([("user_id", 1), ("commitment_id", 1), ("sequence", 1)])
    await db.occurrences.create_index([("user_id", 1), ("refs.invoice_id", 1)])
    await db.occurrences.create_index([("user_id", 1), ("refs.person_id", 1), ("state", 1)])
    await db.occurrences.create_index([("user_id", 1), ("kind", 1), ("competence", 1)])
    await db.occurrences.create_index(
        [("user_id", 1), ("commitment_id", 1), ("competence", 1), ("sequence", 1)],
        unique=True, name="uniq_occurrence_slot")

    await db.invoices.create_index(
        [("user_id", 1), ("credit_card_id", 1), ("period.year", 1), ("period.month", 1)],
        unique=True, name="uniq_invoice_period")
    await db.invoices.create_index([("user_id", 1), ("status", 1), ("due_date", 1)])

    await db.transactions.create_index([("user_id", 1), ("date", -1)])
    await db.transactions.create_index([("user_id", 1), ("account_id", 1), ("date", -1)])
    await db.transactions.create_index(
        "idempotency_key", unique=True,
        partialFilterExpression={"idempotency_key": {"$type": "string"}})

    await db.commitments.create_index([("user_id", 1), ("status", 1), ("frozen", 1)])
    await db.commitments.create_index([("user_id", 1), ("type", 1)])

    for coll in ("accounts", "credit_cards", "categories", "people", "subscriptions",
                 "income_sources", "third_party_relationships"):
        await db[coll].create_index([("user_id", 1), ("name", 1)])

    await db.idempotency_keys.create_index("key", unique=True)
    await db.idempotency_keys.create_index("expires_at", expireAfterSeconds=0)
