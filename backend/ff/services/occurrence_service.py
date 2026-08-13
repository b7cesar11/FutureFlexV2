"""Valores dinamicos por competencia (Etapa 3).

Permite que um MESMO commitment tenha valores diferentes em cada occurrence,
sem transformar cada mes em um novo commitment. A occurrence continua sendo a
representacao da obrigacao naquela competencia; muda apenas o seu `amount`.

Auditabilidade: cada occurrence carrega `amount_source`:
  - "default"  -> usa o valor padrao do commitment (installment_amount)
  - "override" -> valor customizado manualmente para aquela competencia

Regras preservadas:
  - Ownership sempre pelo user_id autenticado (nunca confiar no frontend).
  - Ocorrencias pagas/canceladas sao imutaveis (historico intacto).
  - Customizacoes ("override") nunca sao sobrescritas por materializacoes futuras
    (amount e amount_source sao INSERT-ONLY em commitment_service.materialize).
  - Faturas afetadas sao recalculadas (anti-dupla-contagem preservada).
  - Toda a operacao roda dentro do UnitOfWork (ACID) fornecido pela API.
"""
import math

from ..core.deps import DomainError
from ..domain.calendar_rules import competence_of, today_utc
from ..domain.money import money
from ..models.base import now_utc
from ..repositories import registry as repo
from . import invoice_service

MODES = ("single", "this_and_future", "default")
MAX_AMOUNT = 1e11


def _validate_amount(raw) -> float:
    if raw is None:
        raise DomainError("Informe o novo valor.", 422)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise DomainError("Valor inválido.", 422)
    if not math.isfinite(value):
        raise DomainError("Valor inválido.", 422)
    value = money(value)
    if value <= 0:
        raise DomainError("O valor deve ser maior que zero.", 422)
    if value > MAX_AMOUNT:
        raise DomainError("Valor acima do limite permitido.", 422)
    return value


async def _recalc_invoices_for(user_id: str, occurrences, session=None) -> None:
    invoice_ids = {o.refs.invoice_id for o in occurrences if o.refs and o.refs.invoice_id}
    for invoice_id in invoice_ids:
        await invoice_service.recalculate(user_id, invoice_id, session=session)


async def update_occurrence_amount(user_id: str, occurrence_id: str, amount,
                                   mode: str = "single", session=None) -> dict:
    if mode not in MODES:
        raise DomainError("Modo de alteração inválido.", 422)
    new_amount = _validate_amount(amount)

    # Ownership: repo faz o scope por user_id; occurrence de outro usuario = 404.
    occ = await repo.occurrences.get(user_id, occurrence_id, session=session)
    if not occ:
        raise DomainError("Ocorrência não encontrada.", 404)

    # Imutabilidade de historico: paga ou cancelada nao pode ser alterada.
    if occ.state == "paid":
        raise DomainError("Esta ocorrência já foi paga e não pode ter seu valor alterado.", 409)
    if occ.state == "cancelled":
        raise DomainError("Esta ocorrência foi cancelada e não pode ser alterada.", 409)
    if (occ.paid_amount or 0) > 0:
        raise DomainError("Esta ocorrência já possui pagamento e não pode ter seu valor alterado.", 409)

    commitment = None
    if occ.commitment_id:
        commitment = await repo.commitments.get(user_id, occ.commitment_id, session=session)
        if not commitment:
            raise DomainError("Compromisso da ocorrência não encontrado.", 404)

    if mode == "single":
        return await _update_single(user_id, occ, new_amount, session)
    if mode == "this_and_future":
        if not commitment:
            raise DomainError("Ocorrência avulsa não permite alteração em série.", 422)
        return await _update_this_and_future(user_id, occ, commitment, new_amount, session)
    return await _update_default(user_id, occ, commitment, new_amount, session)


async def _update_single(user_id, occ, new_amount, session) -> dict:
    await repo.occurrences.update(
        user_id, occ.id,
        {"amount": new_amount, "amount_source": "override", "updated_at": now_utc()},
        session=session)
    if occ.refs and occ.refs.invoice_id:
        await invoice_service.recalculate(user_id, occ.refs.invoice_id, session=session)
    return {"occurrence_id": occ.id, "commitment_id": occ.commitment_id,
            "mode": "single", "new_amount": new_amount, "affected_occurrences": 1}


async def _update_this_and_future(user_id, occ, commitment, new_amount, session) -> dict:
    target_comp = occ.competence
    # 1) a occurrence selecionada e sempre atualizada (override), mesmo se ja era override.
    await repo.occurrences.update(
        user_id, occ.id,
        {"amount": new_amount, "amount_source": "override", "updated_at": now_utc()},
        session=session)
    # 2) competencias FUTURAS (> alvo), abertas, sem pagamento e que ainda nao foram
    #    customizadas manualmente. Overrides anteriores sao preservados.
    res = await repo.occurrences.update_many(
        user_id,
        {"commitment_id": commitment.id, "competence": {"$gt": target_comp},
         "state": "open", "paid_amount": 0, "amount_source": {"$ne": "override"}},
        {"amount": new_amount, "amount_source": "override", "updated_at": now_utc()},
        session=session)
    affected = 1 + res.modified_count
    touched = await repo.occurrences.find(
        user_id, {"commitment_id": commitment.id, "competence": {"$gte": target_comp}},
        session=session)
    await _recalc_invoices_for(user_id, touched, session=session)
    return {"occurrence_id": occ.id, "commitment_id": commitment.id,
            "mode": "this_and_future", "new_amount": new_amount,
            "affected_occurrences": affected}


async def _update_default(user_id, occ, commitment, new_amount, session) -> dict:
    if not commitment:
        raise DomainError("Ocorrência avulsa não possui valor padrão.", 422)
    if commitment.installments_total:
        raise DomainError(
            "Compromissos parcelados não possuem valor padrão editável. "
            "Edite a parcela específica.", 422)

    # Novo valor padrao do commitment (recorrencia): afeta apenas ocorrencias futuras
    # que ainda usam o padrao. Historico/pagas e overrides sao preservados.
    await repo.commitments.update(
        user_id, commitment.id,
        {"installment_amount": new_amount, "total_amount": new_amount,
         "updated_at": now_utc()},
        session=session)

    current = competence_of(today_utc())
    res = await repo.occurrences.update_many(
        user_id,
        {"commitment_id": commitment.id, "competence": {"$gte": current},
         "state": "open", "paid_amount": 0, "amount_source": {"$ne": "override"}},
        {"amount": new_amount, "updated_at": now_utc()},
        session=session)
    touched = await repo.occurrences.find(
        user_id, {"commitment_id": commitment.id, "competence": {"$gte": current}},
        session=session)
    await _recalc_invoices_for(user_id, touched, session=session)
    return {"occurrence_id": occ.id, "commitment_id": commitment.id,
            "mode": "default", "new_amount": new_amount,
            "affected_occurrences": res.modified_count}
