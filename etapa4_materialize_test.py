#!/usr/bin/env python3
"""
ETAPA 4 Materialize Test: Verify materialize does not duplicate overdue occurrences
"""
import requests
from datetime import datetime, timedelta

BASE_URL = "https://flex-qa-stage6.preview.emergentagent.com/api"

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

print("Testing materialize does not duplicate overdue occurrences...")

# Register fresh user
timestamp = int(datetime.now().timestamp())
email = f"mattest+{timestamp}@futureflex.dev"
token = register_user(email, "Test@2026", "Materialize Tester")

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

# Get past competence (last month)
past_comp = (datetime.now() - timedelta(days=35)).strftime("%Y-%m")
print(f"✅ Past competence: {past_comp}")

# Create a recurring commitment starting in the past
status, commitment = api_post(token, "/commitments", {
    "type": "fixed_expense",
    "description": "Aluguel Recorrente",
    "total_amount": 1500,
    "payment_method": "account",
    "day_of_month": 5,
    "start_competence": past_comp
})
if status != 200:
    print("❌ Failed to create commitment")
    exit(1)

commitment_id = commitment.get("id")
print(f"✅ Commitment created: {commitment_id}")

# Materialize first time
status, mat1 = api_post(token, "/commitments/materialize", {})
if status != 200:
    print("❌ Failed to materialize (first time)")
    exit(1)

print(f"✅ First materialize: {mat1.get('slots')} slots")

# Get occurrences for past month
status, occs1 = api_get(token, f"/occurrences?competence={past_comp}")
if status != 200:
    print("❌ Failed to get occurrences")
    exit(1)

past_occs_count1 = len([o for o in occs1 if o.get("competence") == past_comp])
print(f"✅ Past month occurrences (before 2nd materialize): {past_occs_count1}")

# Materialize second time (should not duplicate)
status, mat2 = api_post(token, "/commitments/materialize", {})
if status != 200:
    print("❌ Failed to materialize (second time)")
    exit(1)

print(f"✅ Second materialize: {mat2.get('slots')} slots")

# Get occurrences for past month again
status, occs2 = api_get(token, f"/occurrences?competence={past_comp}")
if status != 200:
    print("❌ Failed to get occurrences after 2nd materialize")
    exit(1)

past_occs_count2 = len([o for o in occs2 if o.get("competence") == past_comp])
print(f"✅ Past month occurrences (after 2nd materialize): {past_occs_count2}")

# Verify no duplication
if past_occs_count1 == past_occs_count2:
    print(f"✅ PASS: Materialize did not duplicate overdue occurrences (count stayed at {past_occs_count1})")
    exit(0)
else:
    print(f"❌ FAIL: Occurrence count changed from {past_occs_count1} to {past_occs_count2}")
    exit(1)
