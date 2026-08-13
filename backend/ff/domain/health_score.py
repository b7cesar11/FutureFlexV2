"""Saude financeira: score 0-100 DETERMINISTICO e EXPLICAVEL.

Regras:
- funcao pura, sem I/O -> testavel;
- cada fator devolve pontos, peso, valor, explicacao e recomendacao;
- se faltar dado para um fator, ele e marcado has_data=false, NAO pontua e seu peso e
  excluido do total (o score e normalizado sobre os pesos disponiveis). Nunca inventar dado.
"""
from .money import money

WEIGHTS = {
    "commitment_ratio": 20,
    "reserve": 12,
    "overdue": 12,
    "credit_usage": 12,
    "debt": 10,
    "installment_dependency": 10,
    "free_margin": 10,
    "fixed_expense_weight": 8,
    "trend": 6,
}

LABELS = {
    "commitment_ratio": "Comprometimento de renda",
    "reserve": "Reserva disponível",
    "overdue": "Contas atrasadas",
    "credit_usage": "Uso de crédito",
    "debt": "Dívidas",
    "installment_dependency": "Dependência de parcelamentos",
    "free_margin": "Margem financeira",
    "fixed_expense_weight": "Peso das despesas fixas",
    "trend": "Tendência dos próximos meses",
}

NO_DATA_TEXT = "Não há dados suficientes para avaliar este fator."


def _grade(ratio: float, thresholds: list[tuple[float, float]]) -> float:
    """thresholds: [(limite, fracao_da_pontuacao)] avaliados em ordem crescente de limite."""
    for limit, fraction in thresholds:
        if ratio <= limit:
            return fraction
    return 0.0


def _factor(key: str, fraction: float, value, explanation: str, recommendation: str,
            has_data: bool = True) -> dict:
    weight = WEIGHTS[key]
    points = round(weight * fraction, 1) if has_data else 0.0
    if not has_data:
        verdict = "sem_dados"
    elif fraction >= 0.8:
        verdict = "bom"
    elif fraction >= 0.5:
        verdict = "atencao"
    else:
        verdict = "critico"
    return {
        "key": key, "label": LABELS[key], "weight": weight, "points": points,
        "max_points": weight, "value": value, "verdict": verdict, "has_data": has_data,
        "explanation": explanation if has_data else NO_DATA_TEXT,
        "recommendation": recommendation if has_data else
        "Cadastre os dados relacionados para que este fator seja avaliado.",
    }


def compute(metrics: dict) -> dict:
    """metrics: dict determinístico produzido pelo health_service a partir do motor financeiro."""
    income = metrics.get("monthly_income") or 0.0
    committed = metrics.get("committed") or 0.0
    balance = metrics.get("balance") or 0.0
    monthly_expenses = metrics.get("average_monthly_expenses") or 0.0
    overdue = metrics.get("overdue") or 0.0
    invoices_open = metrics.get("open_invoices_total") or 0.0
    debt_remaining = metrics.get("debt_remaining") or 0.0
    installment_monthly = metrics.get("installment_monthly") or 0.0
    fixed_monthly = metrics.get("fixed_monthly") or 0.0
    free_now = metrics.get("free_now") or 0.0
    trend = metrics.get("trend_delta_pct")
    has_income = income > 0
    has_commitments = metrics.get("commitment_count", 0) > 0

    factors = []

    ratio = committed / income if has_income else 0
    factors.append(_factor(
        "commitment_ratio",
        _grade(ratio, [(0.3, 1.0), (0.5, 0.8), (0.7, 0.55), (0.9, 0.3)]),
        round(ratio * 100),
        f"Seus compromissos previstos representam {round(ratio * 100)}% da sua renda mensal "
        f"de {money(income)}.",
        "Mantenha o comprometimento abaixo de 50% da renda para preservar margem."
        if ratio > 0.5 else "Comprometimento saudável. Continue assim.",
        has_data=has_income,
    ))

    months_covered = (balance / monthly_expenses) if monthly_expenses > 0 else None
    factors.append(_factor(
        "reserve",
        0.0 if months_covered is None else
        (1.0 if months_covered >= 6 else 0.8 if months_covered >= 3
         else 0.5 if months_covered >= 1 else 0.2),
        round(months_covered, 1) if months_covered is not None else None,
        f"Seu saldo de {money(balance)} cobre aproximadamente "
        f"{round(months_covered, 1) if months_covered else 0} meses das suas despesas.",
        "Busque uma reserva equivalente a 3 a 6 meses de despesas."
        if (months_covered or 0) < 3 else "Reserva em bom nível.",
        has_data=monthly_expenses > 0,
    ))

    factors.append(_factor(
        "overdue",
        1.0 if overdue == 0 else (0.5 if has_income and overdue < income * 0.1 else 0.1),
        money(overdue),
        "Você não possui compromissos atrasados." if overdue == 0
        else f"Você possui {money(overdue)} em compromissos atrasados.",
        "Quite os atrasos primeiro: eles pesam mais que qualquer outro fator."
        if overdue > 0 else "Continue pagando em dia.",
        has_data=has_commitments,
    ))

    credit_ratio = invoices_open / income if has_income else 0
    factors.append(_factor(
        "credit_usage",
        _grade(credit_ratio, [(0.1, 1.0), (0.25, 0.8), (0.4, 0.5), (0.6, 0.25)]),
        round(credit_ratio * 100),
        f"Suas faturas em aberto somam {money(invoices_open)}, "
        f"{round(credit_ratio * 100)}% da sua renda mensal.",
        "Reduza o uso do cartão para menos de 25% da renda mensal."
        if credit_ratio > 0.25 else "Uso de crédito sob controle.",
        has_data=has_income and metrics.get("card_count", 0) > 0,
    ))

    debt_ratio = debt_remaining / (income * 12) if has_income else 0
    factors.append(_factor(
        "debt",
        _grade(debt_ratio, [(0.1, 1.0), (0.25, 0.8), (0.5, 0.5), (0.8, 0.25)]),
        money(debt_remaining),
        f"Você tem {money(debt_remaining)} a pagar nos próximos meses, "
        f"{round(debt_ratio * 100)}% da sua renda anual.",
        "Evite novas dívidas e priorize a quitação das parcelas mais longas."
        if debt_ratio > 0.25 else "Nível de dívida confortável.",
        has_data=has_income,
    ))

    inst_ratio = installment_monthly / income if has_income else 0
    factors.append(_factor(
        "installment_dependency",
        _grade(inst_ratio, [(0.1, 1.0), (0.2, 0.8), (0.35, 0.5), (0.5, 0.25)]),
        round(inst_ratio * 100),
        f"Parcelamentos consomem {money(installment_monthly)} por mês, "
        f"{round(inst_ratio * 100)}% da renda.",
        "Evite novos parcelamentos até que os atuais terminem."
        if inst_ratio > 0.2 else "Baixa dependência de parcelamentos.",
        has_data=has_income,
    ))

    margin_ratio = free_now / income if has_income else 0
    factors.append(_factor(
        "free_margin",
        1.0 if margin_ratio >= 0.3 else 0.8 if margin_ratio >= 0.2
        else 0.5 if margin_ratio >= 0.1 else 0.2 if margin_ratio > 0 else 0.0,
        money(free_now),
        f"Seu dinheiro livre é {money(free_now)}, {round(margin_ratio * 100)}% da renda mensal.",
        "Aumente a margem cortando gastos recorrentes ou aumentando a renda."
        if margin_ratio < 0.2 else "Margem financeira confortável.",
        has_data=has_income,
    ))

    fixed_ratio = fixed_monthly / income if has_income else 0
    factors.append(_factor(
        "fixed_expense_weight",
        _grade(fixed_ratio, [(0.3, 1.0), (0.45, 0.8), (0.6, 0.5), (0.75, 0.25)]),
        round(fixed_ratio * 100),
        f"Despesas fixas e assinaturas somam {money(fixed_monthly)} por mês, "
        f"{round(fixed_ratio * 100)}% da renda.",
        "Revise despesas fixas e assinaturas: são o corte mais sustentável."
        if fixed_ratio > 0.45 else "Peso das despesas fixas equilibrado.",
        has_data=has_income,
    ))

    factors.append(_factor(
        "trend",
        0.0 if trend is None else
        (1.0 if trend <= -5 else 0.85 if trend <= 0 else 0.5 if trend <= 10 else 0.2),
        trend,
        ("Seus compromissos dos próximos meses estão estáveis." if (trend or 0) == 0 else
         "Seus compromissos dos próximos meses estão caindo "
         f"{abs(round(trend or 0))}%." if (trend or 0) < 0 else
         f"Seus compromissos dos próximos meses crescem {round(trend or 0)}%."),
        "Verifique quais compromissos futuros estão crescendo."
        if (trend or 0) > 0 else "Tendência favorável nos próximos meses.",
        has_data=trend is not None,
    ))

    available_weight = sum(f["weight"] for f in factors if f["has_data"])
    earned = sum(f["points"] for f in factors)
    score = round(earned / available_weight * 100) if available_weight else 0
    completeness = round(available_weight / sum(WEIGHTS.values()) * 100)

    if available_weight == 0:
        band, band_label = "sem_dados", "Sem dados suficientes"
    elif score >= 80:
        band, band_label = "excelente", "Excelente"
    elif score >= 65:
        band, band_label = "boa", "Boa"
    elif score >= 45:
        band, band_label = "atencao", "Atenção"
    else:
        band, band_label = "critica", "Crítica"

    top_actions = [
        {"factor": f["label"], "recommendation": f["recommendation"],
         "lost_points": round(f["max_points"] - f["points"], 1)}
        for f in sorted(factors, key=lambda f: f["points"] - f["max_points"])
        if f["has_data"] and f["points"] < f["max_points"]
    ][:3]

    return {
        "score": score,
        "band": band,
        "band_label": band_label,
        "earned_points": round(earned, 1),
        "available_weight": available_weight,
        "data_completeness_pct": completeness,
        "has_enough_data": available_weight >= 30,
        "factors": factors,
        "top_actions": top_actions,
        "metrics_used": metrics,
    }
