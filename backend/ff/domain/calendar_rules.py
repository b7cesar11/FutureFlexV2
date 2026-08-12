"""Calendario: competencia (YYYY-MM) e datas deterministicas de recorrencia."""
from calendar import monthrange
from datetime import date, datetime, timezone


def competence_of(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def parse_competence(competence: str) -> tuple[int, int]:
    year, month = competence.split("-")
    return int(year), int(month)


def add_months(competence: str, n: int) -> str:
    year, month = parse_competence(competence)
    total = (year * 12 + (month - 1)) + n
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def months_between(start: str, end: str) -> int:
    y1, m1 = parse_competence(start)
    y2, m2 = parse_competence(end)
    return (y2 * 12 + m2) - (y1 * 12 + m1)


def clamp_day(competence: str, day: int) -> date:
    """Dia 31 em fevereiro -> ultimo dia do mes (regra unica)."""
    year, month = parse_competence(competence)
    last = monthrange(year, month)[1]
    return date(year, month, min(max(day, 1), last))


def as_datetime(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


def today_utc() -> date:
    return datetime.now(timezone.utc).date()


def schedule_monthly(start_competence: str, day_of_month: int, count: int,
                     interval: int = 1) -> list[tuple[str, date]]:
    out = []
    for i in range(count):
        comp = add_months(start_competence, i * interval)
        out.append((comp, clamp_day(comp, day_of_month)))
    return out
