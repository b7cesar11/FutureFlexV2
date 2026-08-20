"""CRUD seguro de cadastros (contas, cartões, categorias e pessoas).

Cadastros podem ser corrigidos livremente enquanto não houver histórico financeiro que
ficaria órfão. Exclusões com referências são bloqueadas explicitamente.
"""
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from ..core.db import UnitOfWork, db
from ..core.deps import current_user_id
from ..models.base import now_utc
from ..repositories.registry import CATALOG
from ..services.authorization import assert_owned

router = APIRouter(tags=["cadastros"])

EDITABLE_FIELDS = {
    "accounts": {"name", "type", "institution", "color", "archived"},
    "credit-cards": {
        "name", "brand", "limit", "closing_day", "due_day", "default_account_id",
        "color", "archived",
    },
    "categories": {"name", "kind", "icon", "color"},
    "people": {"name", "phone", "notes", "color"},
}


def _serialize(model) -> dict:
    data = model.model_dump()
    data["id"] = model.id
    data.pop("user_id", None)
    return data


def _clean_name(payload: dict) -> dict:
    if "name" in payload:
        payload["name"] = str(payload.get("name") or "").strip()
        if not payload["name"]:
            raise HTTPException(status_code=422, detail="Informe um nome.")
        if len(payload["name"]) > 120:
            raise HTTPException(status_code=422, detail="Nome muito longo.")
    return payload


def _validate_days(resource: str, payload: dict) -> None:
    if resource != "credit-cards":
        return
    for key, label in (("closing_day", "fechamento"), ("due_day", "vencimento")):
        if key not in payload:
            continue
        try:
            value = int(payload[key])
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail=f"Dia de {label} inválido.") from None
        if value < 1 or value > 31:
            raise HTTPException(status_code=422, detail=f"Dia de {label} deve estar entre 1 e 31.")
        payload[key] = value


async def _has_ref(collection: str, user_id: str, filters: dict, session=None) -> bool:
    query = {"user_id": ObjectId(user_id), **filters}
    return await db[collection].find_one(query, {"_id": 1}, session=session) is not None


async def _assert_delete_safe(resource: str, item_id: str, user_id: str, session=None) -> None:
    oid = ObjectId(item_id)
    checks: list[tuple[str, dict, str]] = []

    if resource == "accounts":
        checks = [
            ("transactions", {"$or": [{"account_id": oid}, {"to_account_id": oid}]}, "transações"),
            ("commitments", {"default_account_id": oid}, "compromissos"),
            ("occurrences", {"refs.account_id": oid}, "pagamentos"),
            ("credit_cards", {"default_account_id": oid}, "cartões"),
            ("subscriptions", {"account_id": oid}, "assinaturas"),
            ("income_sources", {"account_id": oid}, "fontes de renda"),
        ]
    elif resource == "credit-cards":
        checks = [
            ("invoices", {"credit_card_id": oid}, "faturas"),
            ("commitments", {"credit_card_id": oid}, "compromissos"),
            ("occurrences", {"refs.credit_card_id": oid}, "ocorrências"),
            ("third_party_relationships", {"credit_card_id": oid}, "terceiros"),
            ("subscriptions", {"credit_card_id": oid}, "assinaturas"),
            ("transactions", {"credit_card_id": oid}, "transações"),
        ]
    elif resource == "people":
        checks = [
            ("third_party_relationships", {"person_id": oid}, "registros de terceiros"),
            ("commitments", {"person_id": oid}, "compromissos"),
            ("occurrences", {"refs.person_id": oid}, "ocorrências"),
            ("transactions", {"person_id": oid}, "transações"),
        ]
    elif resource == "categories":
        checks = [
            ("commitments", {"category_id": oid}, "compromissos"),
            ("occurrences", {"refs.category_id": oid}, "ocorrências"),
            ("transactions", {"category_id": oid}, "transações"),
            ("subscriptions", {"category_id": oid}, "assinaturas"),
            ("income_sources", {"category_id": oid}, "fontes de renda"),
        ]

    for collection, filters, label in checks:
        if await _has_ref(collection, user_id, filters, session=session):
            raise HTTPException(
                status_code=409,
                detail=f"Não é possível excluir este cadastro porque ele já está ligado a {label}. Edite o cadastro ou remova primeiro o registro relacionado.",
            )


async def _card_cycle_is_locked(user_id: str, card_id: str, session=None) -> bool:
    oid = ObjectId(card_id)
    return any([
        await _has_ref("commitments", user_id, {"credit_card_id": oid}, session=session),
        await _has_ref("invoices", user_id, {"credit_card_id": oid}, session=session),
        await _has_ref("subscriptions", user_id, {"credit_card_id": oid}, session=session),
    ])


@router.get("/{resource}")
async def list_items(resource: str, user_id: str = Depends(current_user_id)):
    if resource not in CATALOG:
        raise HTTPException(status_code=404, detail="Recurso não encontrado")
    repository, _ = CATALOG[resource]
    items = await repository.find(user_id, {}, sort=[("name", 1)])
    return [_serialize(i) for i in items]


@router.post("/{resource}")
async def create_item(resource: str, payload: dict, user_id: str = Depends(current_user_id)):
    if resource not in CATALOG:
        raise HTTPException(status_code=404, detail="Recurso não encontrado")
    repository, model_cls = CATALOG[resource]
    payload = {k: v for k, v in payload.items() if k not in ("id", "_id", "user_id")}
    payload = _clean_name(payload)
    _validate_days(resource, payload)

    if resource in {"accounts", "credit-cards", "people", "categories"} and "name" not in payload:
        raise HTTPException(status_code=422, detail="Informe um nome.")
    if resource == "accounts":
        payload.setdefault("current_balance", payload.get("opening_balance", 0))
    if resource == "credit-cards" and payload.get("default_account_id"):
        await assert_owned(user_id, {"account_id": payload["default_account_id"]})

    model = model_cls(user_id=user_id, **payload)
    await repository.insert(model)
    return _serialize(model)


@router.patch("/{resource}/{item_id}")
async def update_item(resource: str, item_id: str, payload: dict,
                      user_id: str = Depends(current_user_id)):
    if resource not in CATALOG:
        raise HTTPException(status_code=404, detail="Recurso não encontrado")
    repository, _ = CATALOG[resource]

    async with UnitOfWork() as uow:
        current = await repository.get(user_id, item_id, session=uow.session)
        if not current:
            raise HTTPException(status_code=404, detail="Item não encontrado")

        unknown = set(payload) - EDITABLE_FIELDS[resource] - {"id", "_id", "user_id"}
        if unknown:
            raise HTTPException(status_code=422, detail=f"Campos não editáveis: {', '.join(sorted(unknown))}")
        changes = {k: v for k, v in payload.items() if k in EDITABLE_FIELDS[resource]}
        changes = _clean_name(changes)
        _validate_days(resource, changes)

        if resource == "credit-cards" and ({"closing_day", "due_day"} & set(changes)):
            cycle_changed = any(
                int(changes[key]) != int(getattr(current, key))
                for key in ("closing_day", "due_day") if key in changes
            )
            if cycle_changed and await _card_cycle_is_locked(user_id, item_id, session=uow.session):
                raise HTTPException(
                    status_code=409,
                    detail="Fechamento/vencimento não podem ser alterados depois que o cartão já possui faturas ou compromissos. Nome e limite continuam editáveis.",
                )
        if resource == "credit-cards" and changes.get("default_account_id"):
            await assert_owned(user_id, {"account_id": changes["default_account_id"]}, session=uow.session)

        changes["updated_at"] = now_utc()
        await repository.update(user_id, item_id, changes, session=uow.session)
        updated = await repository.get(user_id, item_id, session=uow.session)
    return _serialize(updated)


@router.delete("/{resource}/{item_id}")
async def delete_item(resource: str, item_id: str, user_id: str = Depends(current_user_id)):
    if resource not in CATALOG:
        raise HTTPException(status_code=404, detail="Recurso não encontrado")
    repository, _ = CATALOG[resource]
    async with UnitOfWork() as uow:
        if not await repository.exists(user_id, item_id, session=uow.session):
            raise HTTPException(status_code=404, detail="Item não encontrado")
        await _assert_delete_safe(resource, item_id, user_id, session=uow.session)
        await repository.delete(user_id, item_id, session=uow.session)
    return {"ok": True}
