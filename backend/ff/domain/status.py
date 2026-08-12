"""Status de ocorrencia: SEMPRE derivado. Nunca existe campo manual de status."""
from datetime import date

from .money import to_cents

FUTURE = "future"
DUE = "due"
PAID = "paid"
OVERDUE = "overdue"
CANCELLED = "cancelled"
FROZEN = "frozen"

OPEN_STATES = {FUTURE, DUE, OVERDUE}


def derive(occurrence, today: date, current_competence: str | None = None) -> str:
    state = getattr(occurrence, "state", None) or occurrence.get("state")
    frozen = getattr(occurrence, "frozen", None) if not isinstance(occurrence, dict) else occurrence.get("frozen")
    amount = getattr(occurrence, "amount", None) if not isinstance(occurrence, dict) else occurrence.get("amount")
    paid = getattr(occurrence, "paid_amount", None) if not isinstance(occurrence, dict) else occurrence.get("paid_amount")
    due = getattr(occurrence, "due_date", None) if not isinstance(occurrence, dict) else occurrence.get("due_date")
    competence = getattr(occurrence, "competence", None) if not isinstance(occurrence, dict) else occurrence.get("competence")

    if state == CANCELLED:
        return CANCELLED
    if frozen:
        return FROZEN
    if state == PAID or (amount is not None and to_cents(paid or 0) >= to_cents(amount)):
        return PAID
    due_day = due.date() if hasattr(due, "date") else due
    if due_day and due_day < today:
        return OVERDUE
    if current_competence and competence == current_competence:
        return DUE
    return FUTURE
