"""Divisao de valores em parcelas. Regra: a soma das parcelas e SEMPRE igual ao total."""
from .money import from_cents, to_cents


def split(total: float, count: int) -> list[float]:
    if count < 1:
        raise ValueError("count deve ser >= 1")
    cents = to_cents(total)
    base = cents // count
    remainder = cents - (base * count)
    values = [base] * count
    # o residuo de centavos vai para a PRIMEIRA parcela (regra unica do sistema)
    values[0] += remainder
    return [from_cents(v) for v in values]
