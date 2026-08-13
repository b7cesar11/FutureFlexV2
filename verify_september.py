#!/usr/bin/env python3
import requests
import json

BASE_URL = "https://b6aff91e-3130-4674-8c37-26c515188945.preview.emergentagent.com/api"

# Use the same user from investigation
email = "investigate_multicard@futureflex.dev"
password = "Test@2026"

# Login
r = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Get September month view
r = requests.get(f"{BASE_URL}/months/2026-09", headers=headers)
month_view = r.json()

print(f"\n=== MONTH VIEW (2026-09) ===")
print(json.dumps(month_view, indent=2))

# Check groups
groups = {g["key"]: g for g in month_view.get("groups", [])}
print(f"\n=== GROUPS ===")
for key, group in groups.items():
    print(f"{key}: total={group.get('total')}, items={len(group.get('items', []))}")

cards_total = groups.get("cards", {}).get("total", 0)
print(f"\n=== RESULT ===")
print(f"Cards total in September: {cards_total}")
print(f"Expected: 800.0")
print(f"Match: {abs(cards_total - 800.0) < 0.01}")
