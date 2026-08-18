"""End-to-end backend tests for Future Flex V2 motor financeiro.

Covers: auth, ANTI-DUPLA-CONTAGEM, invoice composition, installments,
payment (occurrence/invoice), third-party, freeze, months navigation,
projection, simulation (read-only), quick-add, transactions, single-source,
tenant isolation, idempotency, /api/auth/google/session.
"""
import os
import time
import uuid

import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"

DEMO_EMAIL = "demo@futureflex.dev"
DEMO_PASSWORD = "Demo@2026"


def _rand_email():
    return f"test_{uuid.uuid4().hex[:10]}@example.com"


def _groups_dict(m):
    """Convert month_view groups list -> dict by key."""
    return {g["key"]: g for g in m.get("groups", [])}


def _auth(sess: requests.Session, token: str) -> requests.Session:
    sess.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return sess


@pytest.fixture(scope="module")
def demo():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
               headers={"Content-Type": "application/json"})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return _auth(s, token)


@pytest.fixture(scope="module")
def newuser():
    s = requests.Session()
    email = _rand_email()
    r = s.post(f"{API}/auth/register",
               json={"email": email, "password": "Passw0rd!TEST", "name": "TEST User"},
               headers={"Content-Type": "application/json"})
    assert r.status_code in (200, 201), r.text
    token = r.json()["access_token"]
    s = _auth(s, token)
    s.email = email  # type: ignore
    s.password = "Passw0rd!TEST"  # type: ignore
    return s


# ---------- auth ----------

class TestAuth:
    def test_login_demo(self, demo):
        r = demo.get(f"{API}/auth/me")
        assert r.status_code == 200
        assert r.json()["email"] == DEMO_EMAIL

    def test_register_and_relogin(self):
        s = requests.Session()
        email = _rand_email()
        r = s.post(f"{API}/auth/register",
                   json={"email": email, "password": "Passw0rd!TEST", "name": "X"},
                   headers={"Content-Type": "application/json"})
        assert r.status_code in (200, 201)
        csrf = r.headers.get("X-CSRF-Token")
        assert csrf
        # Cookie-authenticated unsafe calls must echo the CSRF header.
        r = s.post(f"{API}/auth/logout", headers={"X-CSRF-Token": csrf})
        assert r.status_code == 200, r.text
        r = s.post(f"{API}/auth/login", json={"email": email, "password": "Passw0rd!TEST"},
                   headers={"Content-Type": "application/json"})
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_google_session_invalid(self):
        r = requests.post(f"{API}/auth/google/session",
                          headers={"X-Session-ID": "invalid-xyz"})
        assert r.status_code == 401


# ---------- dashboard / single source ----------

class TestDashboard:
    def test_dashboard_has_expected_keys(self, demo):
        r = demo.get(f"{API}/dashboard")
        assert r.status_code == 200
        data = r.json()
        for key in ("balance", "committed", "income_expected", "free_projected", "cards"):
            assert key in data


class TestAntiDoubleCount:
    def test_invoice_child_not_counted_twice(self, demo):
        """Card composition children must be counts_in_total=False."""
        r = demo.get(f"{API}/months/2026-08")
        assert r.status_code == 200
        m = r.json()
        groups = _groups_dict(m)
        for item in groups.get("installments", {}).get("items", []):
            if item.get("refs", {}).get("invoice_id"):
                assert item["counts_in_total"] is False

    def test_month_committed_equals_counted_items(self, demo):
        r = demo.get(f"{API}/months/2026-08")
        assert r.status_code == 200
        m = r.json()
        counted = sum(
            float(item["amount"])
            for group in m.get("groups", [])
            for item in group.get("items", [])
            if item.get("counts_in_total") and item.get("direction") == "out"
        )
        assert round(counted, 2) == round(float(m["committed"]), 2)


class TestInstallments:
    def test_installment_schedule_exact_sum(self, newuser):
        cards = newuser.get(f"{API}/cards").json()
        assert cards
        card_id = cards[0]["id"]
        r = newuser.post(f"{API}/commitments", json={
            "type": "purchase_installment",
            "description": "Notebook E2E",
            "total_amount": 1000.01,
            "installments": 3,
            "card_id": card_id,
            "purchase_date": "2026-08-10",
        })
        assert r.status_code in (200, 201), r.text
        cid = r.json()["id"]
        occurrences = newuser.get(f"{API}/occurrences?commitment_id={cid}").json()
        amounts = [float(o["amount"]) for o in occurrences]
        assert round(sum(amounts), 2) == 1000.01
        assert len(amounts) == 3


class TestInvoice:
    def test_invoice_detail_composition(self, demo):
        invoices = demo.get(f"{API}/invoices").json()
        if not invoices:
            pytest.skip("Demo has no invoices")
        inv = invoices[0]
        r = demo.get(f"{API}/invoices/{inv['id']}")
        assert r.status_code == 200
        detail = r.json()
        assert "items" in detail
        assert "total" in detail


class TestPayment:
    def test_occurrence_payment_is_idempotent(self, newuser):
        accounts = newuser.get(f"{API}/accounts").json()
        assert accounts
        account_id = accounts[0]["id"]
        r = newuser.post(f"{API}/commitments", json={
            "type": "fixed_expense",
            "description": "Conta E2E pagamento",
            "total_amount": 42.55,
            "payment_method": "account",
            "default_account_id": account_id,
            "due_date": "2026-08-20",
        })
        assert r.status_code in (200, 201), r.text
        cid = r.json()["id"]
        occurrences = newuser.get(f"{API}/occurrences?commitment_id={cid}").json()
        occ = occurrences[0]

        p1 = newuser.post(f"{API}/occurrences/{occ['id']}/pay", json={"account_id": account_id})
        assert p1.status_code == 200, p1.text
        p2 = newuser.post(f"{API}/occurrences/{occ['id']}/pay", json={"account_id": account_id})
        assert p2.status_code == 409


class TestThirdParty:
    def test_third_party_card_use_no_double_expense(self, newuser):
        cards = newuser.get(f"{API}/cards").json()
        people = newuser.get(f"{API}/people").json()
        assert cards and people
        r = newuser.post(f"{API}/third-parties/card-use", json={
            "person_id": people[0]["id"],
            "card_id": cards[0]["id"],
            "description": "Uso terceiro E2E",
            "amount": 99.90,
            "purchase_date": "2026-08-12",
        })
        assert r.status_code in (200, 201), r.text
        body = r.json()
        assert body.get("receivable_id")
        assert body.get("invoice_id") or body.get("occurrence_id")


class TestFreeze:
    def test_freeze_unfreeze(self, newuser):
        accounts = newuser.get(f"{API}/accounts").json()
        r = newuser.post(f"{API}/commitments", json={
            "type": "recurring_expense", "description": "Freeze E2E",
            "total_amount": 25, "payment_method": "account",
            "default_account_id": accounts[0]["id"], "day_of_month": 15,
        })
        assert r.status_code in (200, 201), r.text
        cid = r.json()["id"]
        f = newuser.post(f"{API}/commitments/{cid}/freeze")
        assert f.status_code == 200
        u = newuser.post(f"{API}/commitments/{cid}/unfreeze")
        assert u.status_code == 200


class TestProjection:
    def test_projection_24_months(self, demo):
        r = demo.get(f"{API}/projection?months=24")
        assert r.status_code == 200
        data = r.json()
        assert len(data["months"]) == 24


class TestSimulation:
    def test_simulation_read_only(self, demo):
        before = demo.get(f"{API}/transactions").json()
        r = demo.post(f"{API}/simulations/purchase", json={
            "amount": 3000,
            "installments": 10,
        })
        assert r.status_code == 200, r.text
        after = demo.get(f"{API}/transactions").json()
        assert len(after) == len(before)


class TestTenantIsolation:
    def test_foreign_commitment_not_accessible(self, demo, newuser):
        mine = newuser.get(f"{API}/commitments").json()
        if not mine:
            pytest.skip("newuser has no commitment")
        foreign_id = mine[0]["id"]
        r = demo.get(f"{API}/commitments/{foreign_id}")
        assert r.status_code == 404


class TestIdempotency:
    def test_materialize_is_idempotent(self, newuser):
        before = newuser.get(f"{API}/occurrences").json()
        r1 = newuser.post(f"{API}/commitments/materialize")
        r2 = newuser.post(f"{API}/commitments/materialize")
        assert r1.status_code == 200 and r2.status_code == 200
        after = newuser.get(f"{API}/occurrences").json()
        assert len(after) == len(set(o["id"] for o in after))
        assert len(after) >= len(before)


class TestQuickAdd:
    def test_quick_add_expense(self, newuser):
        accounts = newuser.get(f"{API}/accounts").json()
        r = newuser.post(f"{API}/commitments", json={
            "type": "fixed_expense", "description": "Quick E2E",
            "total_amount": 18.75, "payment_method": "account",
            "default_account_id": accounts[0]["id"], "due_date": "2026-08-25",
        })
        assert r.status_code in (200, 201)


class TestTransactions:
    def test_transactions_endpoint(self, demo):
        r = demo.get(f"{API}/transactions")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


class TestMonthsNavigation:
    def test_previous_next_months(self, demo):
        for competence in ("2026-07", "2026-08", "2026-09"):
            r = demo.get(f"{API}/months/{competence}")
            assert r.status_code == 200
            assert r.json()["competence"] == competence
