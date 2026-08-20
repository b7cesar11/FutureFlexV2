"""Correção segura de registros de terceiros já cadastrados."""
from fastapi import APIRouter, Depends

from ..core.db import UnitOfWork
from ..core.deps import current_user_id
from ..services import third_party_service

router = APIRouter(tags=["terceiros"])


@router.patch("/third-parties/{relationship_id}")
async def update_third_party(relationship_id: str, payload: dict,
                             user_id: str = Depends(current_user_id)):
    async with UnitOfWork() as uow:
        return await third_party_service.update(
            user_id, relationship_id, payload, session=uow.session
        )


@router.delete("/third-parties/{relationship_id}")
async def delete_third_party(relationship_id: str,
                             user_id: str = Depends(current_user_id)):
    async with UnitOfWork() as uow:
        return await third_party_service.delete(
            user_id, relationship_id, session=uow.session
        )
