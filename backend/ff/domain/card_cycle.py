"""Ciclo do cartao de credito: em qual fatura uma compra cai e quando ela vence."""
from datetime import date

from .calendar_rules import add_months, clamp_day, competence_of


def invoice_competence_for_purchase(purchase_date: date, closing_day: int) -> str:
    """Compra ate o fechamento entra na fatura do ciclo corrente; depois, na seguinte."""
    base = competence_of(purchase_date)
    last_closing = clamp_day(base, closing_day)
    if purchase_date <= last_closing:
        return base
    return add_months(base, 1)


def due_date_for(invoice_competence: str, closing_day: int, due_day: int) -> date:
    """Se o vencimento cai antes/igual ao fechamento, ele pertence ao mes seguinte."""
    comp = invoice_competence if due_day > closing_day else add_months(invoice_competence, 1)
    return clamp_day(comp, due_day)


def schedule(purchase_date: date, closing_day: int, due_day: int,
             installments: int) -> list[tuple[str, date]]:
    """Retorna [(competencia_da_fatura, data_de_vencimento)] para cada parcela."""
    first = invoice_competence_for_purchase(purchase_date, closing_day)
    out = []
    for i in range(installments):
        comp = add_months(first, i)
        out.append((comp, due_date_for(comp, closing_day, due_day)))
    return out
