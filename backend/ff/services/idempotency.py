"""Idempotencia de operacoes criticas."""
from datetime import timedelta

from ..core.db import db
from ..core.deps import DomainError
from ..models.base import now_utc
from bson import ObjectId
from pymongo.errors import DuplicateKeyError


async def claim(user_id: str, key: str | None, endpoint: str, session=None):
    """Registra a chave dentro da transacao. Se ja existir, devolve o resultado anterior."""
    if not key:
        return None
    try:
        await db.idempotency_keys.insert_one({
            "key": f"{user_id}:{endpoint}:{key}",
            "user_id": ObjectId(user_id),
            "endpoint": endpoint,
            "created_at": now_utc(),
            "expires_at": now_utc() + timedelta(hours=24),
        }, session=session)
        return None
    except DuplicateKeyError:
        existing = await db.idempotency_keys.find_one({"key": f"{user_id}:{endpoint}:{key}"})
        raise DomainError("Operação já executada com esta Idempotency-Key", 409) from None


async def store_result(user_id: str, key: str | None, endpoint: str, result_ref: str,
                       session=None):
    if not key:
        return
    await db.idempotency_keys.update_one({"key": f"{user_id}:{endpoint}:{key}"},
                                        {"$set": {"result_ref": result_ref}}, session=session)
