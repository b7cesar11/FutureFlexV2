"""Analista financeiro com IA (GPT-5.5).

Regras de seguranca:
- a IA NUNCA acessa o banco: recebe apenas o contexto do usuario autenticado;
- a IA e ANALISTA: nao paga, nao transfere, nao altera, nao congela, nao cancela;
- simulacoes usam o simulation_service existente (read-only);
- sem dados suficientes -> resposta explicita de que nao ha dados, sem inventar.
"""
import json
import logging
from datetime import timedelta

from bson import ObjectId
from emergentintegrations.llm.chat import LlmChat, UserMessage

from ..core.config import AI_DAILY_LIMIT, AI_MODEL, AI_PROVIDER, EMERGENT_LLM_KEY
from ..core.db import db
from ..core.deps import DomainError
from ..domain.money import money
from ..models.base import now_utc
from . import context_service, simulation_service

logger = logging.getLogger("future_flex.ai")

SYSTEM_PROMPT = """Você é o Analista Financeiro do Future Flex, um sistema de gestão financeira pessoal brasileiro.

REGRAS ABSOLUTAS:
1. Use EXCLUSIVAMENTE os números do CONTEXTO FINANCEIRO em JSON fornecido. Nunca invente, estime ou complete dados ausentes.
2. Se o contexto não tiver a informação necessária, diga exatamente: "Não tenho informações suficientes para responder com segurança." e explique qual dado falta cadastrar.
3. Sempre mostre a base do seu cálculo, citando os valores usados (renda, compromissos, faturas, dinheiro livre, projeção).
4. Você é ANALISTA: não executa pagamentos, transferências, cancelamentos, congelamentos nem qualquer alteração. Se pedirem uma ação, explique como o usuário faz na interface.
5. Responda em português do Brasil, valores em reais no formato R$ 1.234,56.
6. Seja direto e concreto: 3 a 6 frases ou uma lista curta. Sem juridiquês, sem termos técnicos do sistema (não fale "occurrence", "commitment", "endpoint").
7. Entenda a diferença: a fatura do cartão é a obrigação agregada do mês; as parcelas dentro dela são a composição e não somam de novo.
8. Ao avaliar uma compra, considere dinheiro livre, compromissos atuais e futuros, renda, faturas em aberto e a projeção. Nunca responda apenas "sim" ou "não": explique o impacto mensal e no dinheiro livre projetado.
9. Ao sugerir cortes, priorize assinaturas e recorrentes não essenciais. Nunca sugira cortar aluguel, financiamento, saúde ou contas essenciais sem explicar o impacto e oferecer alternativa (renegociar, trocar de plano).
"""


def _chat(session_id: str, extra_system: str = "") -> LlmChat:
    if not EMERGENT_LLM_KEY:
        raise DomainError("Integração de IA não configurada", 503)
    return LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=SYSTEM_PROMPT + extra_system,
    ).with_model(AI_PROVIDER, AI_MODEL)


async def _check_rate_limit(user_id: str):
    since = now_utc() - timedelta(days=1)
    used = await db.ai_usage.count_documents({"user_id": ObjectId(user_id),
                                              "created_at": {"$gte": since}})
    if used >= AI_DAILY_LIMIT:
        raise DomainError(
            f"Limite de {AI_DAILY_LIMIT} perguntas à IA nas últimas 24h atingido.", 429)


async def _register_usage(user_id: str, kind: str):
    await db.ai_usage.insert_one({"user_id": ObjectId(user_id), "kind": kind,
                                  "created_at": now_utc()})


async def _history(user_id: str, session_id: str) -> list[dict]:
    doc = await db.ai_conversations.find_one({"user_id": ObjectId(user_id),
                                              "session_id": session_id})
    return (doc or {}).get("messages", [])


async def _store(user_id: str, session_id: str, question: str, answer: str, kind: str):
    await db.ai_conversations.update_one(
        {"user_id": ObjectId(user_id), "session_id": session_id},
        {"$push": {"messages": {"$each": [
            {"role": "user", "content": question, "at": now_utc()},
            {"role": "assistant", "content": answer, "kind": kind, "at": now_utc()},
        ]}}, "$set": {"updated_at": now_utc()},
         "$setOnInsert": {"created_at": now_utc()}},
        upsert=True)


async def _run(user_id: str, session_id: str, prompt: str, context: dict, kind: str,
               question_for_history: str, extra_system: str = "") -> str:
    await _check_rate_limit(user_id)
    chat = _chat(f"{user_id}:{session_id}", extra_system)
    history = await _history(user_id, session_id)
    recap = ""
    if history:
        last = history[-6:]
        recap = "\n\nCONVERSA ANTERIOR (resumo):\n" + "\n".join(
            f"{m['role']}: {m['content'][:400]}" for m in last)

    message = (f"CONTEXTO FINANCEIRO (JSON, dados reais do usuário):\n"
               f"{json.dumps(context, ensure_ascii=False, default=str)}{recap}\n\n"
               f"PERGUNTA/TAREFA:\n{prompt}")
    try:
        answer = await chat.send_message(UserMessage(text=message))
    except Exception as exc:
        logger.error("Falha na chamada de IA (user=%s kind=%s): %s", user_id, kind, exc)
        raise DomainError("Não foi possível consultar a IA agora. Tente novamente.", 502) from exc

    answer = answer if isinstance(answer, str) else str(answer)
    await _register_usage(user_id, kind)
    await _store(user_id, session_id, question_for_history, answer, kind)
    return answer


async def ask(user_id: str, question: str, session_id: str = "default") -> dict:
    if not question or not question.strip():
        raise DomainError("Escreva sua pergunta", 400)
    context = await context_service.build(user_id)
    answer = await _run(user_id, session_id, question.strip(), context, "ask", question.strip())
    return {
        "answer": answer,
        "session_id": session_id,
        "context_summary": {
            "balance": context["balance"],
            "income_expected": context["month"]["income_expected"],
            "committed": context["month"]["committed"],
            "free_now": context["free_money"]["free_now"],
            "health_score": context["health"]["score"],
        },
        "data_availability": context["data_availability"],
        "model": AI_MODEL,
    }


async def analyze_purchase(user_id: str, payload: dict, session_id: str = "default") -> dict:
    amount = money(payload.get("amount") or 0)
    if amount <= 0:
        raise DomainError("Informe o valor da compra", 400)
    installments = int(payload.get("installments") or 1)
    payment_method = payload.get("payment_method") or (
        "credit_card" if installments > 1 else "account")

    context = await context_service.build(user_id)
    # simulacao READ-ONLY reutilizando o servico existente
    simulation = await simulation_service.simulate(user_id, {
        "add_installment_purchase": {
            "description": payload.get("description") or "Compra avaliada",
            "total_amount": amount, "installments": installments},
        "months": 12,
    })
    installment_amount = money(amount / installments)

    prompt = (
        f"O usuário quer saber se pode comprar {money(amount)} "
        f"{'à vista' if installments == 1 else f'em {installments}x de {installment_amount}'} "
        f"({'no cartão de crédito' if payment_method == 'credit_card' else 'na conta/dinheiro'}).\n"
        f"Use a SIMULAÇÃO abaixo (read-only, não alterou nada no sistema) para explicar o impacto:\n"
        f"{json.dumps(simulation['impact'], ensure_ascii=False)}\n"
        f"Comparativo do dinheiro livre por mês (antes x depois):\n"
        f"{json.dumps([{'mes': b['competence'], 'livre_hoje': b['free'], 'livre_simulado': a['free']} for b, a in zip(simulation['before']['rows'][:6], simulation['after']['rows'][:6])], ensure_ascii=False)}\n"
        f"Responda: é viável? qual o impacto mensal? como fica o dinheiro livre projetado? "
        f"há risco em algum mês? Se faltar dado (por exemplo renda não cadastrada), diga isso."
    )
    answer = await _run(user_id, session_id, prompt, context, "purchase",
                        f"Posso comprar {money(amount)} em {installments}x?")
    return {
        "answer": answer,
        "simulation": simulation,
        "purchase": {"amount": amount, "installments": installments,
                     "installment_amount": installment_amount,
                     "payment_method": payment_method},
        "read_only": True,
        "model": AI_MODEL,
    }


async def suggest_cuts(user_id: str, session_id: str = "default") -> dict:
    candidates = await context_service.cut_candidates(user_id)
    context = await context_service.build(user_id)
    if not candidates["candidates"]:
        answer = ("Não tenho informações suficientes para responder com segurança: você ainda "
                  "não possui assinaturas nem despesas recorrentes cadastradas. Cadastre-as "
                  "para que eu possa indicar cortes.")
        await _store(user_id, session_id, "O que eu posso cortar?", answer, "cuts")
        return {"answer": answer, "candidates": candidates, "model": AI_MODEL}

    prompt = (
        "O usuário quer saber o que pode cortar. Abaixo estão os candidatos JÁ CALCULADOS pelo "
        "sistema, com impacto classificado (alto/medio/baixo) e economia anual:\n"
        f"{json.dumps(candidates, ensure_ascii=False, default=str)}\n"
        "Organize a resposta em ALTO IMPACTO, MÉDIO IMPACTO e BAIXO IMPACTO, citando valor "
        "mensal e economia anual de cada item. Para itens essenciais, não recomende cortar: "
        "explique o impacto e proponha alternativas. Feche com a economia mensal e anual total "
        "possível cortando apenas os não essenciais."
    )
    answer = await _run(user_id, session_id, prompt, context, "cuts", "O que eu posso cortar?")
    return {"answer": answer, "candidates": candidates, "model": AI_MODEL}


async def conversation(user_id: str, session_id: str = "default") -> dict:
    messages = await _history(user_id, session_id)
    return {"session_id": session_id,
            "messages": [{"role": m["role"], "content": m["content"], "at": m["at"]}
                         for m in messages]}


async def clear_conversation(user_id: str, session_id: str = "default") -> dict:
    await db.ai_conversations.delete_one({"user_id": ObjectId(user_id),
                                          "session_id": session_id})
    return {"ok": True}
