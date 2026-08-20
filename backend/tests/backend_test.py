"""End-to-end backend regression for the current Future Flex V2 API.

This suite intentionally validates public API contracts without changing the financial
engine. Every synthetic user provisions its own catalog data so tests do not depend on
demo seed side effects or execution order.
"""
import os
import uuid

import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"

DEMO_EMAIL = "demo@futureflex.dev"
DEMO_PASSWORD = "Demo@2026"
CURRENT_COMPETENCE = "2026-08"


def _rand_email():
    return f"test_{uuid.uuid4().hex[:12]}@example.com"


def _groups_dict(month):
    return {g["key"]: g for g in month.get("groups", [])}


def _auth(sess: requests.Session, token: str) -> requests.Session:
    sess.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return sess


def _post_ok(sess, path, payload):
    response = sess.post(f"{API}{path}", json=payload)
    assert response.status_code in (200, 201), response.text
    return response.json()


@pytest.fixture(scope="module")
def demo():
    sess = requests.Session()
    response = sess.post(
        f"{API}/auth/login",
        json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 200, response.text
    return _auth(sess, response.json()["access_token"])


@pytest.fixture(scope="module")
def newuser():
    sess = requests.Session()
    email = _rand_email()
    response = sess.post(
        f"{API}/auth/register",
        json={"email": email, "password": "Passw0rd!TEST", "name": "TEST User"},
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code in (200, 201), response.text
    sess = _auth(sess, response.json()["access_token"])

    account = _post_ok(sess, "/accounts", {
        "name": "E2E Checking",
        "type": "checking",
        "opening_balance": 5000,
    })
    card = _post_ok(sess, "/credit-cards", {
        "name": "E2E Card",
        "limit": 10000,
        "closing_day": 28,
        "due_day": 5,
        "default_account_id": account["id"],
    })
    person = _post_ok(sess, "/people", {"name": "E2E Person"})

    sess.account_id = account["id"]  # type: ignore[attr-defined]
    sess.card_id = card["id"]  # type: ignore[attr-defined]
    sess.person_id = person["id"]  # type: ignore[attr-defined]
    return sess


# ---------- auth ----------

class TestAuth:
    def test_login_demo(self, demo):
        response = demo.get(f"{API}/auth/me")
        assert response.status_code == 200
        assert response.json()["email"] == DEMO_EMAIL

    def test_register_and_relogin(self):
        sess = requests.Session()
        email = _rand_email()
        response = sess.post(
            f"{API}/auth/register",
            json={"email": email, "password": "Passw0rd!TEST", "name": "X"},
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code in (200, 201), response.text
        csrf = response.headers.get("X-CSRF-Token")
        assert csrf
        response = sess.post(f"{API}/auth/logout", headers={"X-CSRF-Token": csrf})
        assert response.status_code == 200, response.text
        response = sess.post(
            f"{API}/auth/login",
            json={"email": email, "password": "Passw0rd!TEST"},
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200, response.text
        assert "access_token" in response.json()

    def test_google_session_invalid(self):
        response = requests.post(
            f"{API}/auth/google/session",
            headers={"X-Session-ID": "invalid-xyz"},
        )
        assert response.status_code == 401


# ---------- dashboard / single source ----------

class TestDashboard:
    def test_dashboard_has_expected_keys(self, demo):
        response = demo.get(f"{API}/dashboard")
        assert response.status_code == 200
        data = response.json()
        for key in (
            "balance", "committed", "income_expected", "free_now", "free_optimistic",
            "paid", "pending", "overdue", "accounts", "open_invoices", "next_months",
        ):
            assert key in data


class TestAntiDoubleCount:
    def test_invoice_child_not_counted_twice(self, demo):
        response = demo.get(f"{API}/months/{CURRENT_COMPETENCE}")
        assert response.status_code == 200
        groups = _groups_dict(response.json())
        for item in groups.get("installments", {}).get("items", []):
            if item.get("refs", {}).get("invoice_id"):
                assert item["counts_in_total"] is False

    def test_month_committed_equals_counted_items(self, demo):
        response = demo.get(f"{API}/months/{CURRENT_COMPETENCE}")
        assert response.status_code == 200
        month = response.json()
        counted = sum(
            float(item["amount"])
            for group in month.get("groups", [])
            for item in group.get("items", [])
            if item.get("counts_in_total") and item.get("direction") == "outflow"
        )
        assert round(counted, 2) == round(float(month["committed"]), 2)


class TestInstallments:
    def test_installment_schedule_exact_sum(self, newuser):
        response = newuser.get(f"{API}/credit-cards")
        assert response.status_code == 200
        assert any(card["id"] == newuser.card_id for card in response.json())

        commitment = _post_ok(newuser, "/commitments", {
            "type": "purchase_installment",
            "description": "Notebook E2E",
            "total_amount": 1000.01,
            "installments_total": 3,
            "payment_method": "credit_card",
            "credit_card_id": newuser.card_id,
            "start_date": "2026-08-10T12:00:00+00:00",
        })
        detail = newuser.get(f"{API}/commitments/{commitment['id']}")
        assert detail.status_code == 200, detail.text
        occurrences = detail.json()["occurrences"]
        amounts = [float(item["amount"]) for item in occurrences]
        assert len(amounts) == 3
        assert round(sum(amounts), 2) == 1000.01


class TestInvoice:
    def test_invoice_detail_composition(self, demo):
        invoices = demo.get(f"{API}/invoices").json()
        if not invoices:
            pytest.skip("Demo has no invoices")
        response = demo.get(f"{API}/invoices/{invoices[0]['id']}")
        assert response.status_code == 200
        detail = response.json()
        assert "items" in detail
        assert "total" in detail


class TestPayment:
    def test_occurrence_payment_is_idempotent(self, newuser):
        commitment = _post_ok(newuser, "/commitments", {
            "type": "fixed_expense",
            "description": "Conta E2E pagamento",
            "total_amount": 42.55,
            "payment_method": "account",
            "default_account_id": newuser.account_id,
            "start_competence": CURRENT_COMPETENCE,
            "day_of_month": 20,
        })
        detail = newuser.get(f"{API}/commitments/{commitment['id']}")
        assert detail.status_code == 200, detail.text
        occurrence = next(
            item for item in detail.json()["occurrences"]
            if item["competence"] == CURRENT_COMPETENCE
        )

        first = newuser.post(
            f"{API}/occurrences/{occurrence['id']}/pay",
            json={"account_id": newuser.account_id},
        )
        assert first.status_code == 200, first.text
        second = newuser.post(
            f"{API}/occurrences/{occurrence['id']}/pay",
            json={"account_id": newuser.account_id},
        )
        assert second.status_code == 409


class TestThirdParty:
    def test_third_party_card_use_no_double_expense(self, newuser):
        body = _post_ok(newuser, "/third-parties", {
            "person_id": newuser.person_id,
            "direction": "receivable",
            "description": "Uso terceiro E2E",
            "total_amount": 99.90,
            "installments": 1,
            "credit_card_id": newuser.card_id,
            "start_date": "2026-08-12T12:00:00+00:00",
        })
        assert body["commitment_id"]
        assert body["card_commitment_id"]

        receivable = newuser.get(f"{API}/commitments/{body['commitment_id']}")
        card_obligation = newuser.get(f"{API}/commitments/{body['card_commitment_id']}")
        assert receivable.status_code == 200 and card_obligation.status_code == 200
        assert receivable.json()["direction"] == "inflow"
        assert card_obligation.json()["direction"] == "outflow"
        assert card_obligation.json()["linked_commitment_id"] == body["commitment_id"]


class TestFreeze:
    def test_freeze_unfreeze(self, newuser):
        commitment = _post_ok(newuser, "/commitments", {
            "type": "fixed_expense",
            "description": "Freeze E2E",
            "total_amount": 25,
            "payment_method": "account",
            "default_account_id": newuser.account_id,
            "start_competence": CURRENT_COMPETENCE,
            "day_of_month": 15,
        })
        frozen = newuser.post(f"{API}/commitments/{commitment['id']}/freeze")
        assert frozen.status_code == 200, frozen.text
        assert frozen.json()["frozen"] is True
        unfrozen = newuser.post(f"{API}/commitments/{commitment['id']}/unfreeze")
        assert unfrozen.status_code == 200, unfrozen.text
        assert unfrozen.json()["frozen"] is False


class TestProjection:
    def test_projection_24_months(self, demo):
        response = demo.get(f"{API}/projection?months=24")
        assert response.status_code == 200
        data = response.json()
        assert data["months"] == 24
        assert len(data["rows"]) == 24


class TestSimulation:
    def test_simulation_read_only(self, demo):
        before = demo.get(f"{API}/transactions").json()
        response = demo.post(f"{API}/simulations", json={
            "months": 24,
            "add_installment_purchase": {
                "description": "Compra simulada E2E",
                "total_amount": 3000,
                "installments": 10,
            },
        })
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["read_only"] is True
        assert len(result["after"]["rows"]) == 24
        after = demo.get(f"{API}/transactions").json()
        assert [item["id"] for item in after] == [item["id"] for item in before]


class TestTenantIsolation:
    def test_foreign_commitment_not_accessible(self, demo, newuser):
        commitment = _post_ok(newuser, "/commitments", {
            "type": "fixed_expense",
            "description": "Ownership E2E",
            "total_amount": 15,
            "payment_method": "account",
            "default_account_id": newuser.account_id,
            "start_competence": CURRENT_COMPETENCE,
            "day_of_month": 25,
        })
        response = demo.get(f"{API}/commitments/{commitment['id']}")
        assert response.status_code == 404


class TestIdempotency:
    def test_materialize_is_idempotent(self, newuser):
        before = newuser.get(f"{API}/occurrences").json()
        first = newuser.post(f"{API}/commitments/materialize")
        second = newuser.post(f"{API}/commitments/materialize")
        assert first.status_code == 200 and second.status_code == 200
        after = newuser.get(f"{API}/occurrences").json()
        assert len(after) == len(set(item["id"] for item in after))
        assert len(after) >= len(before)


class TestQuickAdd:
    def test_quick_add_expense(self, newuser):
        response = newuser.post(f"{API}/commitments", json={
            "type": "fixed_expense",
            "description": "Quick E2E",
            "total_amount": 18.75,
            "payment_method": "account",
            "default_account_id": newuser.account_id,
            "start_competence": CURRENT_COMPETENCE,
            "day_of_month": 25,
        })
        assert response.status_code in (200, 201), response.text


class TestTransactions:
    def test_transactions_endpoint(self, demo):
        response = demo.get(f"{API}/transactions")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestMonthsNavigation:
    def test_previous_next_months(self, demo):
        for competence in ("2026-07", "2026-08", "2026-09"):
            response = demo.get(f"{API}/months/{competence}")
            assert response.status_code == 200
            assert response.json()["competence"] == competence
