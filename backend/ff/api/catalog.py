"""CRUD de cadastros (contas, cartoes, categorias, pessoas)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..core.deps import current_user_id
from ..models.base import now_utc
from ..repositories import registry as repo
from ..repositories.registry import CATALOG

router = APIRouter(tags=["cadastros"])


def _serialize(model) -> dict:
    data = model.model_dump()
    data["id"] = model.id
    data.pop("user_id", None)
    return data


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
    if resource == "accounts":
        payload.setdefault("current_balance", payload.get("opening_balance", 0))
    model = model_cls(user_id=user_id, **payload)
    await repository.insert(model)
    return _serialize(model)


@router.patch("/{resource}/{item_id}")
async def update_item(resource: str, item_id: str, payload: dict,
                      user_id: str = Depends(current_user_id)):
    if resource not in CATALOG:
        raise HTTPException(status_code=404, detail="Recurso não encontrado")
    repository, _ = CATALOG[resource]
    if not await repository.exists(user_id, item_id):
        raise HTTPException(status_code=404, detail="Item não encontrado")
    changes = {k: v for k, v in payload.items()
               if k not in ("id", "_id", "user_id", "current_balance")}
    changes["updated_at"] = now_utc()
    await repository.update(user_id, item_id, changes)
    return _serialize(await repository.get(user_id, item_id))


@router.delete("/{resource}/{item_id}")
async def delete_item(resource: str, item_id: str, user_id: str = Depends(current_user_id)):
    if resource not in CATALOG:
        raise HTTPException(status_code=404, detail="Recurso não encontrado")
    repository, _ = CATALOG[resource]
    if not await repository.exists(user_id, item_id):
        raise HTTPException(status_code=404, detail="Item não encontrado")
    await repository.delete(user_id, item_id)
    return {"ok": True}
