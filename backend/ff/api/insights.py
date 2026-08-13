"""Assinaturas, Congelados, Saude Financeira e Analista IA."""
from fastapi import APIRouter, Body, Depends

from ..core.db import UnitOfWork
from ..core.deps import current_user_id
from ..services import (ai_service, context_service, frozen_service, health_service,
                        overview_service, subscription_service)

router = APIRouter(tags=["inteligencia"])


# ------------------------------------------------------------------ assinaturas

@router.get("/subscriptions")
async def list_subscriptions(user_id: str = Depends(current_user_id)):
    return await subscription_service.list_with_metrics(user_id)


@router.post("/subscriptions")
async def create_subscription(payload: dict, user_id: str = Depends(current_user_id)):
    async with UnitOfWork() as uow:
        return await subscription_service.create(user_id, payload, session=uow.session)


@router.patch("/subscriptions/{subscription_id}")
async def update_subscription(subscription_id: str, payload: dict,
                              user_id: str = Depends(current_user_id)):
    async with UnitOfWork() as uow:
        return await subscription_service.update(user_id, subscription_id, payload,
                                                 session=uow.session)


@router.post("/subscriptions/{subscription_id}/status")
async def set_subscription_status(subscription_id: str, payload: dict,
                                 user_id: str = Depends(current_user_id)):
    async with UnitOfWork() as uow:
        return await subscription_service.set_status(user_id, subscription_id,
                                                     payload.get("status"),
                                                     session=uow.session)


# ------------------------------------------------------------------ congelados

@router.get("/frozen")
async def list_frozen(user_id: str = Depends(current_user_id)):
    return await frozen_service.list_frozen(user_id)


# ------------------------------------------------------------------ saude financeira

@router.get("/health-score")
async def health_score(user_id: str = Depends(current_user_id)):
    return await health_service.score(user_id)


# ------------------------------------------------------------------ analista IA

@router.get("/ai/context")
async def ai_context(user_id: str = Depends(current_user_id)):
    """Contexto exato que a IA recebe — auditável pelo usuário."""
    return await context_service.build(user_id)


@router.post("/ai/ask")
async def ai_ask(payload: dict, user_id: str = Depends(current_user_id)):
    return await ai_service.ask(user_id, payload.get("question", ""),
                                payload.get("session_id", "default"))


@router.post("/ai/purchase-analysis")
async def ai_purchase(payload: dict, user_id: str = Depends(current_user_id)):
    return await ai_service.analyze_purchase(user_id, payload,
                                             payload.get("session_id", "default"))


@router.post("/ai/cuts")
async def ai_cuts(payload: dict = Body(default={}), user_id: str = Depends(current_user_id)):
    return await ai_service.suggest_cuts(user_id, payload.get("session_id", "default"))


@router.get("/ai/cut-candidates")
async def cut_candidates(user_id: str = Depends(current_user_id)):
    """Candidatos a corte calculados no backend (sem IA) — base determinística."""
    return await context_service.cut_candidates(user_id)


@router.get("/ai/conversations/{session_id}")
async def ai_conversation(session_id: str, user_id: str = Depends(current_user_id)):
    return await ai_service.conversation(user_id, session_id)


@router.delete("/ai/conversations/{session_id}")
async def clear_conversation(session_id: str, user_id: str = Depends(current_user_id)):
    return await ai_service.clear_conversation(user_id, session_id)


# ------------------------------------------------------------------ dashboard integrado

@router.get("/overview")
async def overview(user_id: str = Depends(current_user_id)):
    return await overview_service.dashboard(user_id)
