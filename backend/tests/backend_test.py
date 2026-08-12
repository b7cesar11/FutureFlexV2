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
        # logout + relogin
        s.post(f"{API}/auth/logout")
        r = s.post(f"{API}/auth/login", json={"email": email, "password": "Passw0rd!TEST"},
                   headers={"Content-Type": "application/json"})
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_google_session_invalid(self):
        r = requests.post(f"{API}/auth/google/session",
                          headers={"X-Session-ID": "invalid-xyz"})
        assert r.status_code == 401


# ---------- dashboard / single source ----------

class TestDashboardSingleSource:
    def test_demo_dashboard_values(self, demo):
        r = demo.get(f"{API}/dashboard")
        assert r.status_code == 200
        d = r.json()
        assert d["balance"] == 7000.0
        assert d["income_expected"] == 5500.0
        assert d["committed"] == 2221.9
        assert d["progress_pct"] == 0

    def test_dashboard_equals_month_view(self, demo):
        d = demo.get(f"{API}/dashboard").json()
        comp = d["competence"]
        m = demo.get(f"{API}/months/{comp}").json()
        for k in ("committed", "paid", "pending", "income_expected", "progress_pct"):
            assert d[k] == m[k], f"mismatch {k}: dashboard={d[k]} months={m[k]}"

    def test_free_money_matches_dashboard(self, demo):
        d = demo.get(f"{API}/dashboard").json()
        f = demo.get(f"{API}/free-money").json()
        assert d["free_now"] == f["free_now"]


# ---------- ANTI-DUPLA-CONTAGEM ----------

class TestAntiDoubleCount:
    def test_committed_only_counts_invoice_not_children(self, demo):
        d = demo.get(f"{API}/dashboard").json()
        comp = d["competence"]
        m = demo.get(f"{API}/months/{comp}").json()
        # groups is a list
        groups = _groups_dict(m)
        cards_total = groups.get("cards", {}).get("total", 0)
        assert abs(cards_total - 421.9) < 0.01
        for key in ("installments", "subscriptions"):
            g = groups.get(key)
            if g:
                assert g.get("total", 0) == 0, f"group {key} total should be 0 (composes invoice); got {g}"
        # Rent (fixed) = 1800 + invoice 421.9 = 2221.9
        assert abs(m["committed"] - 2221.9) < 0.01
        # verify children (installments) marked counts_in_total=false
        agg_children = []
        for g in groups.values():
            if g.get("key") == "cards":
                continue
            for it in g.get("items", []):
                if it.get("counts_in_total") is False:
                    agg_children.append(it)
        # iPhone (installments) + Spotify (subscriptions) + Ana card side is on installments as well
        assert len(agg_children) >= 2, f"expected aggregated children with counts_in_total=false, got {len(agg_children)}"


# ---------- invoice composition ----------

class TestInvoiceComposition:
    def test_invoice_items_sum_equals_total(self, demo):
        d = demo.get(f"{API}/dashboard").json()
        inv = d["open_invoices"][0]
        r = demo.get(f"{API}/invoices/{inv['id']}")
        assert r.status_code == 200
        det = r.json()
        s = sum(it["amount"] for it in det["items"])
        assert abs(s - det["total"]) < 0.01
        assert abs(det["total"] - 421.9) < 0.01


# ---------- installments ----------

class TestInstallments:
    def test_installment_creation_no_transaction(self, newuser):
        # need a credit card
        cards = newuser.get(f"{API}/credit-cards").json()
        if not cards:
            c = newuser.post(f"{API}/credit-cards", json={
                "name": "TEST Card", "limit": 5000, "closing_day": 25, "due_day": 5
            })
            assert c.status_code in (200, 201), c.text
            card_id = c.json()["id"]
        else:
            card_id = cards[0]["id"]
        # baseline account balance
        accs = newuser.get(f"{API}/accounts").json()
        if not accs:
            a = newuser.post(f"{API}/accounts", json={
                "name": "TEST Acc", "type": "checking", "opening_balance": 1000
            })
            assert a.status_code in (200, 201)
            accs = newuser.get(f"{API}/accounts").json()
        acc_id = accs[0]["id"]
        before_balance = accs[0]["current_balance"]

        r = newuser.post(f"{API}/commitments", json={
            "type": "purchase_installment",
            "direction": "expense",
            "description": "TEST iPhone",
            "total_amount": 1200.0,
            "installments_total": 12,
            "credit_card_id": card_id,
        })
        assert r.status_code in (200, 201), r.text
        cid = r.json()["id"]

        # verify 12 occurrences
        det = newuser.get(f"{API}/commitments/{cid}").json()
        occs = [o for o in det["occurrences"] if o.get("kind") != "invoice"]
        assert len(occs) == 12
        total = sum(o["amount"] for o in occs)
        assert abs(total - 1200.0) < 0.01

        # no transaction created
        tx = newuser.get(f"{API}/transactions").json()
        assert all(t.get("description") != "TEST iPhone" for t in tx)
        # account balance unchanged
        accs2 = newuser.get(f"{API}/accounts").json()
        after = next(a["current_balance"] for a in accs2 if a["id"] == acc_id)
        assert after == before_balance


# ---------- pay invoice ----------

class TestPayInvoice:
    def test_pay_invoice_debits_chosen_account(self, newuser):
        # Need commitment on card first
        cards = newuser.get(f"{API}/credit-cards").json()
        card_id = cards[0]["id"]
        accs = newuser.get(f"{API}/accounts").json()
        acc_id = accs[0]["id"]
        before = accs[0]["current_balance"]

        # create small purchase to have invoice
        newuser.post(f"{API}/commitments", json={
            "type": "purchase_installment", "direction": "expense",
            "description": "TEST small buy", "total_amount": 100.0,
            "installments_total": 1, "credit_card_id": card_id,
        })
        invs = newuser.get(f"{API}/invoices", params={"credit_card_id": card_id}).json()
        open_invs = [i for i in invs if i["total"] > 0 and i.get("status") != "paid"]
        assert open_invs, "expected open invoice"
        inv = open_invs[0]

        idk = f"TEST-{uuid.uuid4().hex[:10]}"
        r = newuser.post(f"{API}/invoices/{inv['id']}/pay",
                         json={"account_id": acc_id, "amount": inv["total"]},
                         headers={"Idempotency-Key": idk})
        assert r.status_code in (200, 201), r.text

        accs2 = newuser.get(f"{API}/accounts").json()
        after = next(a["current_balance"] for a in accs2 if a["id"] == acc_id)
        assert abs((before - after) - inv["total"]) < 0.01, f"expected debit {inv['total']} before={before} after={after}"

        # invoice_payment tx exists
        tx = newuser.get(f"{API}/transactions").json()
        assert any(t.get("type") == "invoice_payment" for t in tx)

        # idempotency: same key returns 409 or same result, does not double debit
        r2 = newuser.post(f"{API}/invoices/{inv['id']}/pay",
                          json={"account_id": acc_id, "amount": inv["total"]},
                          headers={"Idempotency-Key": idk})
        accs3 = newuser.get(f"{API}/accounts").json()
        after2 = next(a["current_balance"] for a in accs3 if a["id"] == acc_id)
        assert after2 == after, "idempotency should not double debit"


# ---------- pay occurrence outside card ----------

class TestPayOccurrence:
    def test_pay_fixed_expense_uses_chosen_account_and_blocks_double(self, newuser):
        # create fixed expense (rent-like)
        accs = newuser.get(f"{API}/accounts").json()
        if not accs:
            newuser.post(f"{API}/accounts", json={"name": "TEST Acc2", "type": "checking", "opening_balance": 2000})
            accs = newuser.get(f"{API}/accounts").json()
        acc_id = accs[0]["id"]
        r = newuser.post(f"{API}/commitments", json={
            "type": "fixed_expense", "direction": "expense",
            "description": "TEST Rent", "total_amount": 500.0,
            "recurrence": "monthly", "day_of_month": 5,
        })
        assert r.status_code in (200, 201), r.text
        cid = r.json()["id"]
        det = newuser.get(f"{API}/commitments/{cid}").json()
        occ = det["occurrences"][0]
        occ_id = occ["id"]

        before = next(a["current_balance"] for a in accs if a["id"] == acc_id)
        idk = f"TEST-{uuid.uuid4().hex[:10]}"
        r = newuser.post(f"{API}/occurrences/{occ_id}/pay",
                         json={"account_id": acc_id, "amount": occ["amount"]},
                         headers={"Idempotency-Key": idk})
        assert r.status_code in (200, 201), r.text
        accs2 = newuser.get(f"{API}/accounts").json()
        after = next(a["current_balance"] for a in accs2 if a["id"] == acc_id)
        assert abs((before - after) - occ["amount"]) < 0.01

        # Trying to pay again -> 409
        idk2 = f"TEST-{uuid.uuid4().hex[:10]}"
        r2 = newuser.post(f"{API}/occurrences/{occ_id}/pay",
                          json={"account_id": acc_id, "amount": occ["amount"]},
                          headers={"Idempotency-Key": idk2})
        assert r2.status_code == 409, f"expected 409 on second pay, got {r2.status_code}: {r2.text}"


# ---------- third party ----------

class TestThirdParty:
    def test_demo_ana_third_party(self, demo):
        r = demo.get(f"{API}/third-parties")
        assert r.status_code == 200
        data = r.json()
        rec = data.get("total_receivable")
        pay = data.get("total_payable")
        assert rec is not None
        assert abs(float(rec) - 600.0) < 0.01
        assert abs(float(pay or 0) - 0.0) < 0.01


# ---------- freeze ----------

class TestFreeze:
    def test_freeze_and_unfreeze(self, newuser):
        r = newuser.post(f"{API}/commitments", json={
            "type": "fixed_expense", "direction": "expense",
            "description": "TEST Freeze", "total_amount": 300.0,
            "recurrence": "monthly", "day_of_month": 10,
        })
        assert r.status_code in (200, 201)
        cid = r.json()["id"]

        # get a future competence
        proj = newuser.get(f"{API}/projection").json()
        rows = proj if isinstance(proj, list) else proj.get("rows", [])
        assert rows
        # use 2nd future month
        comp = rows[1]["competence"] if isinstance(rows[1], dict) else None
        before_m = newuser.get(f"{API}/months/{comp}").json()
        before_committed = before_m["committed"]
        before_frozen = before_m.get("frozen_total", 0)

        rf = newuser.post(f"{API}/commitments/{cid}/freeze")
        assert rf.status_code in (200, 201), rf.text

        after_m = newuser.get(f"{API}/months/{comp}").json()
        assert after_m["committed"] < before_committed, "freeze should reduce committed"
        assert after_m.get("frozen_total", 0) > before_frozen

        newuser.post(f"{API}/commitments/{cid}/unfreeze")
        restored = newuser.get(f"{API}/months/{comp}").json()
        assert abs(restored["committed"] - before_committed) < 0.01


# ---------- month navigation ----------

class TestMonthNav:
    def test_last_installment_appears_in_final_month(self, demo):
        # demo has iPhone 12x starting current month
        dash = demo.get(f"{API}/dashboard").json()
        comp = dash["competence"]  # e.g. 2026-08
        y, m = map(int, comp.split("-"))
        # last iPhone installment = current + 11
        for _ in range(11):
            m += 1
            if m > 12:
                m = 1
                y += 1
        last = f"{y:04d}-{m:02d}"
        r = demo.get(f"{API}/months/{last}").json()
        # invoice for last competence should exist
        groups = _groups_dict(r)
        cards = groups.get("cards", {})
        assert cards.get("total", 0) > 0


# ---------- projection ----------

class TestProjection:
    def test_projection_24_rows(self, demo):
        r = demo.get(f"{API}/projection").json()
        rows = r if isinstance(r, list) else r.get("rows", r.get("months", []))
        assert len(rows) == 24


# ---------- simulator read-only ----------

class TestSimulation:
    def test_simulation_is_readonly(self, demo):
        before_dash = demo.get(f"{API}/dashboard").json()
        before_month = demo.get(f"{API}/months/{before_dash['competence']}").json()
        before_tx = demo.get(f"{API}/transactions").json()

        r = demo.post(f"{API}/simulations", json={
            "purchase_amount": 1200, "installments": 12,
            "income_delta": 500, "prepay": None
        })
        assert r.status_code in (200, 201), r.text
        result = r.json()
        assert result  # has some impact fields

        after_dash = demo.get(f"{API}/dashboard").json()
        after_month = demo.get(f"{API}/months/{before_dash['competence']}").json()
        after_tx = demo.get(f"{API}/transactions").json()

        assert before_dash["balance"] == after_dash["balance"]
        assert before_dash["committed"] == after_dash["committed"]
        assert before_month == after_month
        assert len(before_tx) == len(after_tx)


# ---------- transactions purity ----------

class TestTransactions:
    def test_only_real_facts(self, demo):
        tx = demo.get(f"{API}/transactions").json()
        # no card purchases (installments) should appear
        for t in tx:
            # invoice_payment or expense (avulso) or income only
            assert t.get("type") != "purchase_installment"


# ---------- tenant isolation ----------

class TestIsolation:
    def test_new_user_sees_nothing(self, newuser):
        # a fresh new user (before we created stuff) should have their own only
        s2 = requests.Session()
        email = _rand_email()
        r = s2.post(f"{API}/auth/register",
                    json={"email": email, "password": "Passw0rd!TEST", "name": "X2"},
                    headers={"Content-Type": "application/json"})
        assert r.status_code in (200, 201)
        _auth(s2, r.json()["access_token"])
        occs = s2.get(f"{API}/occurrences").json()
        assert occs == [] or all("user_id" not in o for o in occs)

    def test_cannot_access_other_user_commitment(self, demo, newuser):
        # get a commitment id from demo
        cs = demo.get(f"{API}/commitments").json()
        cid = cs[0]["id"]
        r = newuser.get(f"{API}/commitments/{cid}")
        assert r.status_code in (403, 404)


# ---------- idempotency of materialize ----------

class TestMaterializeIdempotent:
    def test_materialize_twice(self, demo):
        r1 = demo.post(f"{API}/commitments/materialize")
        assert r1.status_code in (200, 201)
        cs = demo.get(f"{API}/commitments").json()
        # pick a recurring commitment
        rec = next((c for c in cs if c.get("type") in ("fixed_expense", "subscription", "recurring_income")), None)
        if not rec:
            pytest.skip("no recurring commitment on demo")
        before = demo.get(f"{API}/commitments/{rec['id']}").json()
        before_n = len([o for o in before["occurrences"] if o.get("kind") != "invoice"])
        r2 = demo.post(f"{API}/commitments/materialize")
        assert r2.status_code in (200, 201)
        after = demo.get(f"{API}/commitments/{rec['id']}").json()
        after_n = len([o for o in after["occurrences"] if o.get("kind") != "invoice"])
        assert after_n == before_n, f"materialize duplicated: {before_n} -> {after_n}"
