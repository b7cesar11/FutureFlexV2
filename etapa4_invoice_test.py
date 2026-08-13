#!/usr/bin/env python3
"""
ETAPA 4 Invoice Test: Verify invoice-child occurrence cannot be paid directly
"""
import requests
from datetime import datetime

BASE_URL = "https://5e88b598-cbef-4739-9a5d-a884398bfa5d.preview.emergentagent.com/api"

def register_user(email: str, password: str, name: str):
    response = requests.post(f"{BASE_URL}/auth/register",
                           json={"email": email, "password": password, "name": name},
                           timeout=10)
    return response.json().get("access_token") if response.status_code == 200 else None

def api_post(token: str, endpoint: str, payload: dict):
    response = requests.post(f"{BASE_URL}{endpoint}", json=payload,
                           headers={"Authorization": f"Bearer {token}"}, timeout=10)
    return response.status_code, response.json() if response.status_code in [200, 400, 409] else None

def api_get(token: str, endpoint: str):
    response = requests.get(f"{BASE_URL}{endpoint}",
                          headers={"Authorization": f"Bearer {token}"}, timeout=10)
    return response.status_code, response.json() if response.status_code == 200 else None

print("Testing invoice-child payment rejection...")

# Register fresh user
timestamp = int(datetime.now().timestamp())
email = f"invoicetest+{timestamp}@futureflex.dev"
token = register_user(email, "Test@2026", "Invoice Tester")

if not token:
    print("❌ Failed to register user")
    exit(1)

print(f"✅ User registered: {email}")

# Create account
status, account = api_post(token, "/accounts", {
    "name": "Banco Teste", "type": "checking", "opening_balance": 10000
})
if status != 200:
    print("❌ Failed to create account")
    exit(1)

account_id = account.get("id")
print(f"✅ Account created: {account_id}")

# Create credit card
status, card = api_post(token, "/credit-cards", {
    "name": "Cartão Teste", "limit": 5000, "closing_day": 28, "due_day": 5
})
if status != 200:
    print("❌ Failed to create credit card")
    exit(1)

card_id = card.get("id")
print(f"✅ Credit card created: {card_id}")

# Create purchase installment
status, purchase = api_post(token, "/commitments", {
    "type": "purchase_installment",
    "description": "Notebook Dell",
    "total_amount": 2400,
    "installments_total": 12,
    "payment_method": "credit_card",
    "credit_card_id": card_id
})
if status != 200:
    print("❌ Failed to create purchase")
    exit(1)

print("✅ Purchase created")

# Materialize
status, _ = api_post(token, "/commitments/materialize", {})
if status != 200:
    print("❌ Failed to materialize")
    exit(1)

print("✅ Materialized")

# Get all occurrences (no competence filter)
status, occs = api_get(token, "/occurrences")
if status != 200:
    print("❌ Failed to get occurrences")
    exit(1)

print(f"✅ Found {len(occs)} occurrences")

# Debug: print first few occurrences
for i, occ in enumerate(occs[:3]):
    print(f"  Occ {i+1}: kind={occ.get('kind')}, label={occ.get('label')}, refs={occ.get('refs')}")

# Find purchase occurrence (has invoice_id in refs but kind != 'invoice')
purchase_occ = next((o for o in occs 
                    if o.get("refs", {}).get("invoice_id") and o.get("kind") != "invoice"), None)

if not purchase_occ:
    print("❌ No purchase occurrence found")
    exit(1)

print(f"✅ Found purchase occurrence: {purchase_occ['id']}")

# Try to pay purchase occurrence directly (should return 400)
status, response = api_post(token, f"/occurrences/{purchase_occ['id']}/pay",
                          {"account_id": account_id})

if status == 400:
    print("✅ PASS: Purchase occurrence payment correctly rejected with 400")
    print(f"   Response: {response}")
    exit(0)
else:
    print(f"❌ FAIL: Expected 400, got {status}")
    print(f"   Response: {response}")
    exit(1)
