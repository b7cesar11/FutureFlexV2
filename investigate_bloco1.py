#!/usr/bin/env python3
import requests
import json

BASE_URL = "https://b6aff91e-3130-4674-8c37-26c515188945.preview.emergentagent.com/api"

# Register fresh user
email = "investigate_multicard@futureflex.dev"
password = "Test@2026"

# Register
r = requests.post(f"{BASE_URL}/auth/register", json={"email": email, "password": password, "name": "Investigate"})
if r.status_code not in [200, 201]:
    print(f"Registration failed: {r.status_code}")
    exit(1)

token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Create account
r = requests.post(f"{BASE_URL}/accounts", json={"name": "Banco", "type": "checking", "opening_balance": 10000}, headers=headers)
account_id = r.json()["id"]

# Create 2 cards
r = requests.post(f"{BASE_URL}/credit-cards", json={"name": "Card1", "limit": 5000, "closing_day": 5, "due_day": 15}, headers=headers)
card1_id = r.json()["id"]

r = requests.post(f"{BASE_URL}/credit-cards", json={"name": "Card2", "limit": 5000, "closing_day": 5, "due_day": 15}, headers=headers)
card2_id = r.json()["id"]

# Create purchases
r = requests.post(f"{BASE_URL}/commitments", json={
    "type": "purchase_installment",
    "description": "Purchase 1",
    "total_amount": 300.0,
    "installments_total": 1,
    "payment_method": "credit_card",
    "credit_card_id": card1_id
}, headers=headers)

r = requests.post(f"{BASE_URL}/commitments", json={
    "type": "purchase_installment",
    "description": "Purchase 2",
    "total_amount": 500.0,
    "installments_total": 1,
    "payment_method": "credit_card",
    "credit_card_id": card2_id
}, headers=headers)

# Get invoices
r = requests.get(f"{BASE_URL}/invoices", headers=headers)
invoices = r.json()
print(f"\n=== INVOICES ({len(invoices)}) ===")
for inv in invoices:
    print(json.dumps(inv, indent=2))

# Get dashboard
r = requests.get(f"{BASE_URL}/dashboard", headers=headers)
dashboard = r.json()
comp = dashboard.get("competence")
print(f"\n=== DASHBOARD (competence: {comp}) ===")
print(json.dumps(dashboard, indent=2))

# Get month view
r = requests.get(f"{BASE_URL}/months/{comp}", headers=headers)
month_view = r.json()
print(f"\n=== MONTH VIEW ({comp}) ===")
print(json.dumps(month_view, indent=2))

# Check groups
groups = {g["key"]: g for g in month_view.get("groups", [])}
print(f"\n=== GROUPS ===")
for key, group in groups.items():
    print(f"{key}: total={group.get('total')}, items={len(group.get('items', []))}")
