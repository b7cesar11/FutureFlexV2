"""QA repro: new user with TWO credit cards -> invoices in same competence -> E11000?"""
import sys, time, requests

BASE = "http://localhost:8001/api"


def call(method, path, token=None, json_data=None, params=None):
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    r = requests.request(method, BASE + path, headers=h, json=json_data, params=params, timeout=30)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, r.text


def main():
    email = f"qa_multicard_{int(time.time())}@test.dev"
    st, d = call("POST", "/auth/register", json_data={"email": email, "password": "Qa@123456", "name": "QA"})
    assert st in (200, 201), (st, d)
    token = d["access_token"]
    # account
    st, acc = call("POST", "/accounts", token=token, json_data={"name": "Conta", "type": "checking", "opening_balance": 10000})
    print("account:", st)
    # two credit cards
    cards = []
    for name in ("Nubank", "Itau"):
        st, c = call("POST", "/credit-cards", token=token, json_data={"name": name, "limit": 5000, "closing_day": 5, "due_day": 15})
        print(f"card {name}:", st, c if st >= 400 else c.get("id"))
        cards.append(c)
    # purchase on each card (single installment) -> creates invoice occ in a competence
    results = []
    for c in cards:
        st, p = call("POST", "/commitments", token=token, json_data={
            "type": "purchase_installment", "description": f"Compra {c.get('name')}",
            "total_amount": 300, "installments_total": 1, "payment_method": "credit_card",
            "credit_card_id": c.get("id"), "day_of_month": 10})
        print(f"purchase on {c.get('name')}: HTTP {st}", "" if st < 400 else p)
        results.append(st)
    # list invoices
    st, invs = call("GET", "/invoices", token=token)
    print("invoices count:", len(invs) if isinstance(invs, list) else invs)
    ok = all(s < 400 for s in results)
    print("RESULT:", "PASS (no 500)" if ok else "FAIL (multi-card collision)")
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
