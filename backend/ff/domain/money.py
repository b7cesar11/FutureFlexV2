"""Utilitarios monetarios. Toda aritmetica financeira passa por aqui."""


def money(value) -> float:
    """Arredonda para 2 casas com meio-para-cima em centavos (evita erro de float)."""
    return round(float(value) + 1e-9, 2)


def to_cents(value) -> int:
    return int(round(float(value) * 100))


def from_cents(cents: int) -> float:
    return money(cents / 100)


def summed(values) -> float:
    return from_cents(sum(to_cents(v) for v in values))
