"""Regressão da conta fixa de terceiro cobrada no cartão do usuário."""
import time
from datetime import datetime, timezone

import pytest
import requests

BASE = "http://localhost:8001/api"


@pytest.fixture()
def api():
    session = requests.Session()
    email = f"third.recurring.{int(time.time() * 1000)}@futureflex.dev"
    response = session.post(f"{BASE}/auth/register", json={
        "email": email, "password": "Teste@123", "name": "Terceiros",
    })
    assert response.status_code == 200, response.text
    token = response.json().get("access_token")
    if token:
        session.headers["Authorization"] = f"Bearer {token}"
    return session


def test_recurring_third_party_charge_uses_card_and_creates_receivable(api):
    card = api.post(f"{BASE}/credit-cards", json={
        "name": "Nubank", "limit": 5000, "closing_day": 28, "due_day": 5,
    })
    assert card.status_code == 200, card.text
    person = api.post(f"{BASE}/people", json={"name": "Pai"})
    assert person.status_code == 200, person.text

    now = datetime.now(timezone.utc)
    start = f"{now.year:04d}-{now.month:02d}-10"
    created = api.post(f"{BASE}/third-parties", json={
        "person_id": person.json()["id"],
        "direction": "receivable",
        "description": "Netflix",
        "total_amount": 55.90,
        "installments": 1,
        "recurring": True,
        "credit_card_id": card.json()["id"],
        "start_date": start,
    })
    assert created.status_code == 200, created.text
    ids = created.json()
    assert ids["card_commitment_id"]
    assert ids["commitment_id"]

    card_detail = api.get(f"{BASE}/commitments/{ids['card_commitment_id']}")
    receivable_detail = api.get(f"{BASE}/commitments/{ids['commitment_id']}")
    assert card_detail.status_code == 200, card_detail.text
    assert receivable_detail.status_code == 200, receivable_detail.text
    card_data = card_detail.json()
    receivable_data = receivable_detail.json()

    assert card_data["type"] == "fixed_expense"
    assert card_data["payment_method"] == "credit_card"
    assert card_data["linked_commitment"]["id"] == ids["commitment_id"]
    assert receivable_data["type"] == "third_party_receivable"
    assert receivable_data["direction"] == "inflow"
    assert receivable_data["linked_commitment"]["id"] == ids["card_commitment_id"]

    card_occ = card_data["occurrences"]
    recv_occ = receivable_data["occurrences"]
    assert len(card_occ) >= 12
    assert len(recv_occ) >= 12
    assert all(o["refs"]["invoice_id"] for o in card_occ)
    assert all(o["refs"]["person_id"] == person.json()["id"] for o in card_occ)
    assert all(o["amount"] == pytest.approx(55.90) for o in card_occ)
    assert all(o["amount"] == pytest.approx(55.90) for o in recv_occ)

    summary = api.get(f"{BASE}/third-parties")
    assert summary.status_code == 200, summary.text
    item = next(i for i in summary.json()["items"] if i["id"] == ids["third_party_id"])
    assert item["recurring"] is True
    assert item["credit_card_id"] == card.json()["id"]
    assert item["total_amount"] == pytest.approx(55.90)


def test_other_user_cannot_use_someone_elses_card_for_third_party(api):
    card = api.post(f"{BASE}/credit-cards", json={"name": "Meu cartão", "limit": 1000})
    assert card.status_code == 200, card.text

    other = requests.Session()
    email = f"third.other.{int(time.time() * 1000)}@futureflex.dev"
    registered = other.post(f"{BASE}/auth/register", json={
        "email": email, "password": "Teste@123", "name": "Outro",
    })
    assert registered.status_code == 200, registered.text
    token = registered.json().get("access_token")
    if token:
        other.headers["Authorization"] = f"Bearer {token}"
    person = other.post(f"{BASE}/people", json={"name": "Pai"})
    assert person.status_code == 200, person.text

    created = other.post(f"{BASE}/third-parties", json={
        "person_id": person.json()["id"], "direction": "receivable",
        "description": "Netflix", "total_amount": 55.90, "recurring": True,
        "credit_card_id": card.json()["id"], "start_date": "2026-09-10",
    })
    assert created.status_code in (403, 404), created.text
