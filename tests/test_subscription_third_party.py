"""Assinatura de terceiro no cartão: uma despesa na fatura + um recebível vinculado."""
import time
from datetime import datetime, timezone

import pytest
import requests

BASE = "http://localhost:8001/api"
CURRENT = datetime.now(timezone.utc).strftime("%Y-%m")


def register(label):
    session = requests.Session()
    response = session.post(f"{BASE}/auth/register", json={
        "email": f"{label}.{int(time.time() * 1000000)}@futureflex.dev",
        "password": "Teste@123",
        "name": label,
    })
    assert response.status_code == 200, response.text
    token = response.json().get("access_token")
    if token:
        session.headers["Authorization"] = f"Bearer {token}"
    return session


@pytest.fixture()
def api():
    return register("subscription-third-party")


def create_catalog(api):
    card = api.post(f"{BASE}/credit-cards", json={
        "name": "Nubank", "limit": 5000, "closing_day": 28, "due_day": 5,
    })
    assert card.status_code == 200, card.text
    person = api.post(f"{BASE}/people", json={"name": "Pai"})
    assert person.status_code == 200, person.text
    return card.json(), person.json()


def test_subscription_on_my_card_creates_one_expense_and_one_receivable(api):
    card, person = create_catalog(api)
    created = api.post(f"{BASE}/subscriptions", json={
        "name": "Netflix",
        "amount": 55.90,
        "periodicity": "monthly",
        "billing_day": 10,
        "credit_card_id": card["id"],
        "responsible_person_id": person["id"],
        "start_competence": CURRENT,
    })
    assert created.status_code == 200, created.text
    ids = created.json()
    assert ids["commitment_id"]
    assert ids["third_party_relationship_id"]
    assert ids["third_party_commitment_id"]

    subscription_commitment = api.get(
        f"{BASE}/commitments/{ids['commitment_id']}"
    )
    receivable_commitment = api.get(
        f"{BASE}/commitments/{ids['third_party_commitment_id']}"
    )
    assert subscription_commitment.status_code == 200, subscription_commitment.text
    assert receivable_commitment.status_code == 200, receivable_commitment.text
    sub_c = subscription_commitment.json()
    recv_c = receivable_commitment.json()

    assert sub_c["type"] == "subscription"
    assert sub_c["payment_method"] == "credit_card"
    assert sub_c["linked_commitment"]["id"] == ids["third_party_commitment_id"]
    assert recv_c["type"] == "third_party_receivable"
    assert recv_c["direction"] == "inflow"
    assert recv_c["linked_commitment"]["id"] == ids["commitment_id"]
    assert all(o["refs"]["invoice_id"] for o in sub_c["occurrences"])
    assert all(o["refs"]["person_id"] == person["id"] for o in sub_c["occurrences"])

    # A assinatura é a única obrigação que entra no cartão; o segundo commitment é inflow.
    commitments = api.get(f"{BASE}/commitments").json()
    card_outflows = [
        c for c in commitments
        if c.get("credit_card_id") == card["id"] and c.get("direction") == "outflow"
        and "Netflix" in c.get("description", "")
    ]
    assert len(card_outflows) == 1
    assert card_outflows[0]["id"] == ids["commitment_id"]

    subscriptions = api.get(f"{BASE}/subscriptions")
    assert subscriptions.status_code == 200, subscriptions.text
    item = next(i for i in subscriptions.json()["items"] if i["id"] == ids["subscription_id"])
    assert item["responsible_person"]["id"] == person["id"]
    assert item["responsible_person"]["name"] == "Pai"
    assert item["third_party_relationship_id"] == ids["third_party_relationship_id"]
    assert item["reimbursement_pending"] == pytest.approx(55.90)

    third = api.get(f"{BASE}/third-parties")
    assert third.status_code == 200, third.text
    relationship = next(
        i for i in third.json()["items"]
        if i["id"] == ids["third_party_relationship_id"]
    )
    assert relationship["source_module"] == "subscription"
    assert relationship["recurring"] is True
    assert relationship["card_commitment_id"] == ids["commitment_id"]
    assert relationship["commitment_id"] == ids["third_party_commitment_id"]
    assert relationship["pending"] == pytest.approx(55.90)
    assert relationship["editable"] is False


def test_existing_subscription_can_gain_responsible_person_and_price_stays_synced(api):
    card, person = create_catalog(api)
    created = api.post(f"{BASE}/subscriptions", json={
        "name": "YouTube Premium",
        "amount": 24.90,
        "periodicity": "monthly",
        "billing_day": 12,
        "credit_card_id": card["id"],
        "start_competence": CURRENT,
    })
    assert created.status_code == 200, created.text
    subscription_id = created.json()["subscription_id"]

    assigned = api.patch(f"{BASE}/subscriptions/{subscription_id}", json={
        "responsible_person_id": person["id"],
        "amount": 29.90,
    })
    assert assigned.status_code == 200, assigned.text
    ids = assigned.json()
    assert ids["third_party_relationship_id"]
    assert ids["third_party_commitment_id"]

    listing = api.get(f"{BASE}/subscriptions").json()
    item = next(i for i in listing["items"] if i["id"] == subscription_id)
    assert item["amount"] == pytest.approx(29.90)
    assert item["responsible_person"]["id"] == person["id"]
    assert item["reimbursement_pending"] == pytest.approx(29.90)

    sub_detail = api.get(f"{BASE}/commitments/{item['commitment_id']}").json()
    recv_detail = api.get(f"{BASE}/commitments/{ids['third_party_commitment_id']}").json()
    sub_current = next(o for o in sub_detail["occurrences"] if o["competence"] == CURRENT)
    recv_current = next(o for o in recv_detail["occurrences"] if o["competence"] == CURRENT)
    assert sub_current["amount"] == pytest.approx(29.90)
    assert recv_current["amount"] == pytest.approx(29.90)

    removed = api.patch(f"{BASE}/subscriptions/{subscription_id}", json={
        "responsible_person_id": None,
    })
    assert removed.status_code == 200, removed.text
    assert removed.json()["third_party_relationship_id"] is None
    listing = api.get(f"{BASE}/subscriptions").json()
    item = next(i for i in listing["items"] if i["id"] == subscription_id)
    assert item["responsible_person"] is None
    assert item["third_party_relationship_id"] is None


def test_other_user_cannot_assign_someone_elses_card_or_person_to_subscription(api):
    card, person = create_catalog(api)
    other = register("subscription-other-user")
    created = other.post(f"{BASE}/subscriptions", json={
        "name": "Netflix",
        "amount": 55.90,
        "periodicity": "monthly",
        "billing_day": 10,
        "credit_card_id": card["id"],
        "responsible_person_id": person["id"],
        "start_competence": CURRENT,
    })
    assert created.status_code in (403, 404), created.text
