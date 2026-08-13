#!/usr/bin/env python3
"""
ETAPA 3 Backend Testing: Dynamic Occurrence Amounts
Tests PATCH /api/occurrences/{occurrence_id} with 3 modes: single, this_and_future, default
"""
import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional

# Backend URL from frontend/.env
BASE_URL = "https://5e88b598-cbef-4739-9a5d-a884398bfa5d.preview.emergentagent.com/api"

# Test credentials
DEMO_EMAIL = "demo@futureflex.dev"
DEMO_PASSWORD = "Demo@2026"

# Test results tracking
test_results = []


class TestResult:
    def __init__(self, rule: str, passed: bool, details: str, response: Optional[Dict] = None):
        self.rule = rule
        self.passed = passed
        self.details = details
        self.response = response


def log_test(rule: str, passed: bool, details: str, response: Optional[Dict] = None):
    """Log test result"""
    test_results.append(TestResult(rule, passed, details, response))
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"\n{status} | {rule}")
    print(f"Details: {details}")
    if response:
        print(f"Response: {json.dumps(response, indent=2)}")


def register_user(email: str, password: str, name: str) -> Optional[str]:
    """Register a new user and return access token"""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/register",
            json={"email": email, "password": password, "name": name},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
        else:
            print(f"Registration failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Registration error: {e}")
        return None


def login(email: str, password: str) -> Optional[str]:
    """Login and return access token"""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": email, "password": password},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
        else:
            print(f"Login failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Login error: {e}")
        return None


def create_account(token: str, name: str, account_type: str, opening_balance: float) -> Optional[str]:
    """Create an account and return account_id"""
    try:
        response = requests.post(
            f"{BASE_URL}/accounts",
            json={"name": name, "type": account_type, "opening_balance": opening_balance},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("id")
        else:
            print(f"Account creation failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Account creation error: {e}")
        return None


def create_commitment(token: str, payload: Dict) -> Optional[Dict]:
    """Create a commitment and return the commitment data"""
    try:
        response = requests.post(
            f"{BASE_URL}/commitments",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Commitment creation failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Commitment creation error: {e}")
        return None


def get_commitment_detail(token: str, commitment_id: str) -> Optional[Dict]:
    """Get commitment detail with occurrences"""
    try:
        response = requests.get(
            f"{BASE_URL}/commitments/{commitment_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Get commitment failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Get commitment error: {e}")
        return None


def patch_occurrence(token: str, occurrence_id: str, amount: Any, mode: str) -> tuple[int, Optional[Dict]]:
    """Patch occurrence amount and return (status_code, response_data)"""
    try:
        response = requests.patch(
            f"{BASE_URL}/occurrences/{occurrence_id}",
            json={"amount": amount, "mode": mode},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        data = response.json() if response.status_code in [200, 422, 409, 404] else None
        return response.status_code, data
    except Exception as e:
        print(f"Patch occurrence error: {e}")
        return 0, None


def pay_occurrence(token: str, occurrence_id: str, account_id: str) -> tuple[int, Optional[Dict]]:
    """Pay an occurrence"""
    try:
        response = requests.post(
            f"{BASE_URL}/occurrences/{occurrence_id}/pay",
            json={"account_id": account_id},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        data = response.json() if response.status_code in [200, 404, 409] else None
        return response.status_code, data
    except Exception as e:
        print(f"Pay occurrence error: {e}")
        return 0, None


def materialize_all(token: str) -> tuple[int, Optional[Dict]]:
    """Materialize all commitments"""
    try:
        response = requests.post(
            f"{BASE_URL}/commitments/materialize",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        data = response.json() if response.status_code == 200 else None
        return response.status_code, data
    except Exception as e:
        print(f"Materialize error: {e}")
        return 0, None


def get_month_view(token: str, competence: str) -> Optional[Dict]:
    """Get month view"""
    try:
        response = requests.get(
            f"{BASE_URL}/months/{competence}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Get month view error: {e}")
        return None


def get_free_money(token: str) -> Optional[Dict]:
    """Get free money"""
    try:
        response = requests.get(
            f"{BASE_URL}/free-money",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Get free money error: {e}")
        return None


def get_projection(token: str, months: int = 24) -> Optional[Dict]:
    """Get projection"""
    try:
        response = requests.get(
            f"{BASE_URL}/projection?months={months}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Get projection error: {e}")
        return None


def create_credit_card(token: str, name: str, limit: float, closing_day: int, due_day: int) -> Optional[str]:
    """Create a credit card and return card_id"""
    try:
        response = requests.post(
            f"{BASE_URL}/credit-cards",
            json={"name": name, "limit": limit, "closing_day": closing_day, "due_day": due_day},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("id")
        else:
            print(f"Credit card creation failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Credit card creation error: {e}")
        return None


def get_dashboard(token: str) -> Optional[Dict]:
    """Get dashboard"""
    try:
        response = requests.get(
            f"{BASE_URL}/dashboard",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Get dashboard error: {e}")
        return None


def get_ai_context(token: str) -> Optional[Dict]:
    """Get AI context"""
    try:
        response = requests.get(
            f"{BASE_URL}/ai/context",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Get AI context error: {e}")
        return None


def get_current_competence() -> str:
    """Get current competence (YYYY-MM)"""
    return datetime.now().strftime("%Y-%m")


def get_next_competences(count: int) -> list[str]:
    """Get next N competences"""
    current = datetime.now()
    competences = []
    for i in range(1, count + 1):
        month = current.month + i
        year = current.year
        while month > 12:
            month -= 12
            year += 1
        competences.append(f"{year:04d}-{month:02d}")
    return competences


def run_tests():
    """Run all ETAPA 3 tests"""
    print("=" * 80)
    print("ETAPA 3 Backend Testing: Dynamic Occurrence Amounts")
    print("=" * 80)

    # Setup: Register fresh user
    print("\n[SETUP] Registering fresh test user...")
    timestamp = int(datetime.now().timestamp())
    test_email = f"etapa3test+{timestamp}@futureflex.dev"
    test_password = "Test@2026"
    test_name = "Etapa 3 Tester"
    
    token = register_user(test_email, test_password, test_name)
    if not token:
        print("❌ CRITICAL: Failed to register test user. Aborting tests.")
        return

    print(f"✅ User registered: {test_email}")

    # Create account
    print("\n[SETUP] Creating checking account...")
    account_id = create_account(token, "Banco Itaú", "checking", 20000.0)
    if not account_id:
        print("❌ CRITICAL: Failed to create account. Aborting tests.")
        return
    print(f"✅ Account created: {account_id}")

    # Get competences
    current_comp = get_current_competence()
    next_comps = get_next_competences(4)
    c1, c2, c3, c4 = next_comps[0], next_comps[1], next_comps[2], next_comps[3]
    print(f"\n[INFO] Competences: CURRENT={current_comp}, C1={c1}, C2={c2}, C3={c3}, C4={c4}")

    # ========================================================================
    # TEST 1: Single mode
    # ========================================================================
    print("\n" + "=" * 80)
    print("TEST 1: Single mode")
    print("=" * 80)
    
    commitment1 = create_commitment(token, {
        "type": "fixed_expense",
        "description": "Evolução de Obra",
        "total_amount": 750,
        "payment_method": "account",
        "day_of_month": 10
    })
    
    if not commitment1:
        log_test("Test 1: Single mode", False, "Failed to create commitment", None)
    else:
        detail1 = get_commitment_detail(token, commitment1["id"])
        if not detail1:
            log_test("Test 1: Single mode", False, "Failed to get commitment detail", None)
        else:
            occurrences1 = detail1.get("occurrences", [])
            current_occ = next((o for o in occurrences1 if o["competence"] == current_comp), None)
            c1_occ = next((o for o in occurrences1 if o["competence"] == c1), None)
            c2_occ = next((o for o in occurrences1 if o["competence"] == c2), None)
            
            if not c1_occ:
                log_test("Test 1: Single mode", False, f"C1 occurrence not found", None)
            else:
                # Patch C1 to 950 with single mode
                status, response = patch_occurrence(token, c1_occ["id"], 950, "single")
                
                if status != 200:
                    log_test("Test 1: Single mode", False, f"Expected 200, got {status}", response)
                elif response.get("affected_occurrences") != 1:
                    log_test("Test 1: Single mode", False, f"Expected affected_occurrences=1, got {response.get('affected_occurrences')}", response)
                else:
                    # Verify: CURRENT=750, C1=950 (override), C2=750 (default)
                    detail1_after = get_commitment_detail(token, commitment1["id"])
                    if detail1_after:
                        occs_after = detail1_after.get("occurrences", [])
                        current_after = next((o for o in occs_after if o["competence"] == current_comp), None)
                        c1_after = next((o for o in occs_after if o["competence"] == c1), None)
                        c2_after = next((o for o in occs_after if o["competence"] == c2), None)
                        
                        checks = []
                        if current_after and current_after["amount"] == 750:
                            checks.append("CURRENT=750 ✓")
                        else:
                            checks.append(f"CURRENT={current_after['amount'] if current_after else 'N/A'} ✗ (expected 750)")
                        
                        if c1_after and c1_after["amount"] == 950 and c1_after["amount_source"] == "override":
                            checks.append("C1=950 (override) ✓")
                        else:
                            checks.append(f"C1={c1_after['amount'] if c1_after else 'N/A'} ({c1_after['amount_source'] if c1_after else 'N/A'}) ✗ (expected 950/override)")
                        
                        if c2_after and c2_after["amount"] == 750 and c2_after["amount_source"] == "default":
                            checks.append("C2=750 (default) ✓")
                        else:
                            checks.append(f"C2={c2_after['amount'] if c2_after else 'N/A'} ({c2_after['amount_source'] if c2_after else 'N/A'}) ✗ (expected 750/default)")
                        
                        all_passed = all("✓" in c for c in checks)
                        log_test("Test 1: Single mode", all_passed, "; ".join(checks), response)
                    else:
                        log_test("Test 1: Single mode", False, "Failed to verify after patch", response)

    # ========================================================================
    # TEST 2: this_and_future mode
    # ========================================================================
    print("\n" + "=" * 80)
    print("TEST 2: this_and_future mode")
    print("=" * 80)
    
    commitment2 = create_commitment(token, {
        "type": "fixed_expense",
        "description": "Aluguel Escritório",
        "total_amount": 750,
        "payment_method": "account",
        "day_of_month": 10
    })
    
    if not commitment2:
        log_test("Test 2: this_and_future", False, "Failed to create commitment", None)
    else:
        detail2 = get_commitment_detail(token, commitment2["id"])
        if not detail2:
            log_test("Test 2: this_and_future", False, "Failed to get commitment detail", None)
        else:
            occurrences2 = detail2.get("occurrences", [])
            c1_occ2 = next((o for o in occurrences2 if o["competence"] == c1), None)
            
            if not c1_occ2:
                log_test("Test 2: this_and_future", False, "C1 occurrence not found", None)
            else:
                # Patch C1 to 1000 with this_and_future mode
                status, response = patch_occurrence(token, c1_occ2["id"], 1000, "this_and_future")
                
                if status != 200:
                    log_test("Test 2: this_and_future", False, f"Expected 200, got {status}", response)
                else:
                    # Verify: CURRENT=750, C1=1000, C2=1000, C3=1000 (all future override)
                    detail2_after = get_commitment_detail(token, commitment2["id"])
                    if detail2_after:
                        occs_after = detail2_after.get("occurrences", [])
                        current_after = next((o for o in occs_after if o["competence"] == current_comp), None)
                        c1_after = next((o for o in occs_after if o["competence"] == c1), None)
                        c2_after = next((o for o in occs_after if o["competence"] == c2), None)
                        c3_after = next((o for o in occs_after if o["competence"] == c3), None)
                        
                        checks = []
                        if current_after and current_after["amount"] == 750:
                            checks.append("CURRENT=750 ✓")
                        else:
                            checks.append(f"CURRENT={current_after['amount'] if current_after else 'N/A'} ✗")
                        
                        if c1_after and c1_after["amount"] == 1000 and c1_after["amount_source"] == "override":
                            checks.append("C1=1000 (override) ✓")
                        else:
                            checks.append(f"C1={c1_after['amount'] if c1_after else 'N/A'} ✗")
                        
                        if c2_after and c2_after["amount"] == 1000 and c2_after["amount_source"] == "override":
                            checks.append("C2=1000 (override) ✓")
                        else:
                            checks.append(f"C2={c2_after['amount'] if c2_after else 'N/A'} ✗")
                        
                        if c3_after and c3_after["amount"] == 1000 and c3_after["amount_source"] == "override":
                            checks.append("C3=1000 (override) ✓")
                        else:
                            checks.append(f"C3={c3_after['amount'] if c3_after else 'N/A'} ✗")
                        
                        all_passed = all("✓" in c for c in checks)
                        log_test("Test 2: this_and_future", all_passed, "; ".join(checks), response)
                    else:
                        log_test("Test 2: this_and_future", False, "Failed to verify after patch", response)

    # ========================================================================
    # TEST 3: this_and_future preserves prior override
    # ========================================================================
    print("\n" + "=" * 80)
    print("TEST 3: this_and_future preserves prior override")
    print("=" * 80)
    
    commitment3 = create_commitment(token, {
        "type": "fixed_expense",
        "description": "Manutenção Predial",
        "total_amount": 750,
        "payment_method": "account",
        "day_of_month": 10
    })
    
    if not commitment3:
        log_test("Test 3: Preserve override", False, "Failed to create commitment", None)
    else:
        detail3 = get_commitment_detail(token, commitment3["id"])
        if not detail3:
            log_test("Test 3: Preserve override", False, "Failed to get commitment detail", None)
        else:
            occurrences3 = detail3.get("occurrences", [])
            c1_occ3 = next((o for o in occurrences3 if o["competence"] == c1), None)
            c3_occ3 = next((o for o in occurrences3 if o["competence"] == c3), None)
            
            if not c1_occ3 or not c3_occ3:
                log_test("Test 3: Preserve override", False, "C1 or C3 occurrence not found", None)
            else:
                # First: PATCH C3 to 500 (single)
                status1, resp1 = patch_occurrence(token, c3_occ3["id"], 500, "single")
                if status1 != 200:
                    log_test("Test 3: Preserve override", False, f"Failed to patch C3: {status1}", resp1)
                else:
                    # Then: PATCH C1 to 1100 (this_and_future)
                    status2, resp2 = patch_occurrence(token, c1_occ3["id"], 1100, "this_and_future")
                    if status2 != 200:
                        log_test("Test 3: Preserve override", False, f"Failed to patch C1: {status2}", resp2)
                    else:
                        # Verify: C1=1100, C2=1100, C3=500 (preserved), C4=1100
                        detail3_after = get_commitment_detail(token, commitment3["id"])
                        if detail3_after:
                            occs_after = detail3_after.get("occurrences", [])
                            c1_after = next((o for o in occs_after if o["competence"] == c1), None)
                            c2_after = next((o for o in occs_after if o["competence"] == c2), None)
                            c3_after = next((o for o in occs_after if o["competence"] == c3), None)
                            c4_after = next((o for o in occs_after if o["competence"] == c4), None)
                            
                            checks = []
                            if c1_after and c1_after["amount"] == 1100:
                                checks.append("C1=1100 ✓")
                            else:
                                checks.append(f"C1={c1_after['amount'] if c1_after else 'N/A'} ✗")
                            
                            if c2_after and c2_after["amount"] == 1100:
                                checks.append("C2=1100 ✓")
                            else:
                                checks.append(f"C2={c2_after['amount'] if c2_after else 'N/A'} ✗")
                            
                            if c3_after and c3_after["amount"] == 500:
                                checks.append("C3=500 (preserved) ✓")
                            else:
                                checks.append(f"C3={c3_after['amount'] if c3_after else 'N/A'} ✗")
                            
                            if c4_after and c4_after["amount"] == 1100:
                                checks.append("C4=1100 ✓")
                            else:
                                checks.append(f"C4={c4_after['amount'] if c4_after else 'N/A'} ✗")
                            
                            all_passed = all("✓" in c for c in checks)
                            log_test("Test 3: Preserve override", all_passed, "; ".join(checks), resp2)
                        else:
                            log_test("Test 3: Preserve override", False, "Failed to verify after patch", resp2)

    # ========================================================================
    # TEST 4: default mode
    # ========================================================================
    print("\n" + "=" * 80)
    print("TEST 4: default mode")
    print("=" * 80)
    
    commitment4 = create_commitment(token, {
        "type": "fixed_expense",
        "description": "Seguro Empresarial",
        "total_amount": 750,
        "payment_method": "account",
        "day_of_month": 10
    })
    
    if not commitment4:
        log_test("Test 4: default mode", False, "Failed to create commitment", None)
    else:
        detail4 = get_commitment_detail(token, commitment4["id"])
        if not detail4:
            log_test("Test 4: default mode", False, "Failed to get commitment detail", None)
        else:
            occurrences4 = detail4.get("occurrences", [])
            c1_occ4 = next((o for o in occurrences4 if o["competence"] == c1), None)
            c2_occ4 = next((o for o in occurrences4 if o["competence"] == c2), None)
            
            if not c1_occ4 or not c2_occ4:
                log_test("Test 4: default mode", False, "C1 or C2 occurrence not found", None)
            else:
                # First: PATCH C2 to 500 (single override)
                status1, resp1 = patch_occurrence(token, c2_occ4["id"], 500, "single")
                if status1 != 200:
                    log_test("Test 4: default mode", False, f"Failed to patch C2: {status1}", resp1)
                else:
                    # Then: PATCH C1 to 820 (default mode)
                    status2, resp2 = patch_occurrence(token, c1_occ4["id"], 820, "default")
                    if status2 != 200:
                        log_test("Test 4: default mode", False, f"Failed to patch C1 with default: {status2}", resp2)
                    else:
                        # Verify: CURRENT=820, C1=820, C2=500 (preserved), C3=820
                        detail4_after = get_commitment_detail(token, commitment4["id"])
                        if detail4_after:
                            occs_after = detail4_after.get("occurrences", [])
                            current_after = next((o for o in occs_after if o["competence"] == current_comp), None)
                            c1_after = next((o for o in occs_after if o["competence"] == c1), None)
                            c2_after = next((o for o in occs_after if o["competence"] == c2), None)
                            c3_after = next((o for o in occs_after if o["competence"] == c3), None)
                            
                            checks = []
                            if current_after and current_after["amount"] == 820:
                                checks.append("CURRENT=820 ✓")
                            else:
                                checks.append(f"CURRENT={current_after['amount'] if current_after else 'N/A'} ✗")
                            
                            if c1_after and c1_after["amount"] == 820:
                                checks.append("C1=820 ✓")
                            else:
                                checks.append(f"C1={c1_after['amount'] if c1_after else 'N/A'} ✗")
                            
                            if c2_after and c2_after["amount"] == 500:
                                checks.append("C2=500 (preserved) ✓")
                            else:
                                checks.append(f"C2={c2_after['amount'] if c2_after else 'N/A'} ✗")
                            
                            if c3_after and c3_after["amount"] == 820:
                                checks.append("C3=820 ✓")
                            else:
                                checks.append(f"C3={c3_after['amount'] if c3_after else 'N/A'} ✗")
                            
                            # Check commitment total_amount updated to 820
                            if detail4_after.get("total_amount") == 820:
                                checks.append("commitment.total_amount=820 ✓")
                            else:
                                checks.append(f"commitment.total_amount={detail4_after.get('total_amount')} ✗")
                            
                            all_passed = all("✓" in c for c in checks)
                            log_test("Test 4: default mode", all_passed, "; ".join(checks), resp2)
                        else:
                            log_test("Test 4: default mode", False, "Failed to verify after patch", resp2)

    # ========================================================================
    # TEST 5: default rejected for installments
    # ========================================================================
    print("\n" + "=" * 80)
    print("TEST 5: default rejected for installments")
    print("=" * 80)
    
    # Create credit card
    card_id = create_credit_card(token, "Cartão Itaú Platinum", 9000, 28, 5)
    if not card_id:
        log_test("Test 5: default rejected", False, "Failed to create credit card", None)
    else:
        commitment5 = create_commitment(token, {
            "type": "purchase_installment",
            "description": "Notebook Dell",
            "total_amount": 1200,
            "installments_total": 12,
            "payment_method": "credit_card",
            "credit_card_id": card_id
        })
        
        if not commitment5:
            log_test("Test 5: default rejected", False, "Failed to create installment commitment", None)
        else:
            detail5 = get_commitment_detail(token, commitment5["id"])
            if not detail5:
                log_test("Test 5: default rejected", False, "Failed to get commitment detail", None)
            else:
                occurrences5 = detail5.get("occurrences", [])
                if not occurrences5:
                    log_test("Test 5: default rejected", False, "No occurrences found", None)
                else:
                    first_occ = occurrences5[0]
                    # Try to patch with default mode -> expect 422
                    status, response = patch_occurrence(token, first_occ["id"], 150, "default")
                    
                    if status == 422:
                        log_test("Test 5: default rejected", True, "Correctly rejected default mode for installment (422)", response)
                    else:
                        log_test("Test 5: default rejected", False, f"Expected 422, got {status}", response)

    # ========================================================================
    # TEST 6: paid occurrence immutable
    # ========================================================================
    print("\n" + "=" * 80)
    print("TEST 6: paid occurrence immutable")
    print("=" * 80)
    
    commitment6 = create_commitment(token, {
        "type": "fixed_expense",
        "description": "Conta de Luz",
        "total_amount": 750,
        "payment_method": "account",
        "day_of_month": 10
    })
    
    if not commitment6:
        log_test("Test 6: paid immutable", False, "Failed to create commitment", None)
    else:
        detail6 = get_commitment_detail(token, commitment6["id"])
        if not detail6:
            log_test("Test 6: paid immutable", False, "Failed to get commitment detail", None)
        else:
            occurrences6 = detail6.get("occurrences", [])
            current_occ6 = next((o for o in occurrences6 if o["competence"] == current_comp), None)
            
            if not current_occ6:
                log_test("Test 6: paid immutable", False, "CURRENT occurrence not found", None)
            else:
                # Pay the occurrence
                pay_status, pay_resp = pay_occurrence(token, current_occ6["id"], account_id)
                if pay_status != 200:
                    log_test("Test 6: paid immutable", False, f"Failed to pay occurrence: {pay_status}", pay_resp)
                else:
                    # Try to patch the paid occurrence -> expect 409
                    patch_status, patch_resp = patch_occurrence(token, current_occ6["id"], 900, "single")
                    
                    if patch_status == 409:
                        log_test("Test 6: paid immutable", True, "Correctly rejected patch on paid occurrence (409)", patch_resp)
                    else:
                        log_test("Test 6: paid immutable", False, f"Expected 409, got {patch_status}", patch_resp)

    # ========================================================================
    # TEST 7: ownership
    # ========================================================================
    print("\n" + "=" * 80)
    print("TEST 7: ownership")
    print("=" * 80)
    
    # Register second user
    timestamp2 = int(datetime.now().timestamp()) + 1
    test_email2 = f"etapa3test2+{timestamp2}@futureflex.dev"
    token2 = register_user(test_email2, test_password, "Second User")
    
    if not token2:
        log_test("Test 7: ownership", False, "Failed to register second user", None)
    else:
        # Use first user's occurrence from commitment1
        if commitment1:
            detail1_for_ownership = get_commitment_detail(token, commitment1["id"])
            if detail1_for_ownership:
                occurrences_own = detail1_for_ownership.get("occurrences", [])
                if occurrences_own:
                    first_occ_id = occurrences_own[0]["id"]
                    original_amount = occurrences_own[0]["amount"]
                    
                    # Try to patch with second user's token -> expect 404
                    status, response = patch_occurrence(token2, first_occ_id, 999, "single")
                    
                    if status == 404:
                        # Verify original value unchanged for owner
                        detail_verify = get_commitment_detail(token, commitment1["id"])
                        if detail_verify:
                            occs_verify = detail_verify.get("occurrences", [])
                            occ_verify = next((o for o in occs_verify if o["id"] == first_occ_id), None)
                            if occ_verify and occ_verify["amount"] == original_amount:
                                log_test("Test 7: ownership", True, f"Correctly rejected other user's access (404); original value {original_amount} unchanged", response)
                            else:
                                log_test("Test 7: ownership", False, f"Value changed unexpectedly", response)
                        else:
                            log_test("Test 7: ownership", True, "Correctly rejected other user's access (404)", response)
                    else:
                        log_test("Test 7: ownership", False, f"Expected 404, got {status}", response)
                else:
                    log_test("Test 7: ownership", False, "No occurrences to test", None)
            else:
                log_test("Test 7: ownership", False, "Failed to get commitment detail", None)
        else:
            log_test("Test 7: ownership", False, "No commitment available for test", None)

    # ========================================================================
    # TEST 8: validation
    # ========================================================================
    print("\n" + "=" * 80)
    print("TEST 8: validation")
    print("=" * 80)
    
    commitment8 = create_commitment(token, {
        "type": "fixed_expense",
        "description": "Internet Fibra",
        "total_amount": 750,
        "payment_method": "account",
        "day_of_month": 10
    })
    
    if not commitment8:
        log_test("Test 8: validation", False, "Failed to create commitment", None)
    else:
        detail8 = get_commitment_detail(token, commitment8["id"])
        if not detail8:
            log_test("Test 8: validation", False, "Failed to get commitment detail", None)
        else:
            occurrences8 = detail8.get("occurrences", [])
            test_occ = occurrences8[0] if occurrences8 else None
            
            if not test_occ:
                log_test("Test 8: validation", False, "No occurrence to test", None)
            else:
                validation_tests = [
                    (0, "amount=0"),
                    (-100, "amount=-100"),
                    ("abc", "amount='abc'"),
                    (None, "amount=None")
                ]
                
                validation_results = []
                for test_val, desc in validation_tests:
                    status, resp = patch_occurrence(token, test_occ["id"], test_val, "single")
                    if status == 422:
                        validation_results.append(f"{desc} → 422 ✓")
                    else:
                        validation_results.append(f"{desc} → {status} ✗")
                
                all_passed = all("✓" in r for r in validation_results)
                log_test("Test 8: validation", all_passed, "; ".join(validation_results), None)

    # ========================================================================
    # TEST 9: single source of truth
    # ========================================================================
    print("\n" + "=" * 80)
    print("TEST 9: single source of truth")
    print("=" * 80)
    
    commitment9 = create_commitment(token, {
        "type": "fixed_expense",
        "description": "Telefonia Móvel",
        "total_amount": 750,
        "payment_method": "account",
        "day_of_month": 10
    })
    
    if not commitment9:
        log_test("Test 9: single source", False, "Failed to create commitment", None)
    else:
        # Get initial values
        month_before = get_month_view(token, current_comp)
        free_before = get_free_money(token)
        projection_before = get_projection(token, 24)
        
        if not month_before or not free_before:
            log_test("Test 9: single source", False, "Failed to get initial values", None)
        else:
            committed_before = month_before.get("committed", 0)
            free_now_before = free_before.get("free_now", 0)
            
            detail9 = get_commitment_detail(token, commitment9["id"])
            if not detail9:
                log_test("Test 9: single source", False, "Failed to get commitment detail", None)
            else:
                occurrences9 = detail9.get("occurrences", [])
                current_occ9 = next((o for o in occurrences9 if o["competence"] == current_comp), None)
                c1_occ9 = next((o for o in occurrences9 if o["competence"] == c1), None)
                
                if not current_occ9:
                    log_test("Test 9: single source", False, "CURRENT occurrence not found", None)
                else:
                    # Patch CURRENT +150 (750 -> 900)
                    status, resp = patch_occurrence(token, current_occ9["id"], 900, "single")
                    if status != 200:
                        log_test("Test 9: single source", False, f"Failed to patch: {status}", resp)
                    else:
                        # Get values after
                        month_after = get_month_view(token, current_comp)
                        free_after = get_free_money(token)
                        projection_after = get_projection(token, 24)
                        
                        if not month_after or not free_after:
                            log_test("Test 9: single source", False, "Failed to get values after patch", None)
                        else:
                            committed_after = month_after.get("committed", 0)
                            free_now_after = free_after.get("free_now", 0)
                            
                            committed_delta = round(committed_after - committed_before, 2)
                            free_delta = round(free_now_after - free_now_before, 2)
                            
                            checks = []
                            if committed_delta == 150:
                                checks.append(f"committed +{committed_delta} ✓")
                            else:
                                checks.append(f"committed +{committed_delta} ✗ (expected +150)")
                            
                            if free_delta == -150:
                                checks.append(f"free_now {free_delta} ✓")
                            else:
                                checks.append(f"free_now {free_delta} ✗ (expected -150)")
                            
                            # Check projection for C1
                            if projection_before and projection_after and c1_occ9:
                                # Patch C1 as well to test projection
                                status_c1, resp_c1 = patch_occurrence(token, c1_occ9["id"], 1000, "single")
                                if status_c1 == 200:
                                    projection_after2 = get_projection(token, 24)
                                    if projection_after2:
                                        c1_row_before = next((r for r in projection_before.get("rows", []) if r.get("competence") == c1), None)
                                        c1_row_after = next((r for r in projection_after2.get("rows", []) if r.get("competence") == c1), None)
                                        if c1_row_before and c1_row_after:
                                            c1_commit_delta = round(c1_row_after.get("commitments", 0) - c1_row_before.get("commitments", 0), 2)
                                            if c1_commit_delta == 250:  # 750 -> 1000
                                                checks.append(f"projection C1 commitments +{c1_commit_delta} ✓")
                                            else:
                                                checks.append(f"projection C1 commitments +{c1_commit_delta} ✗ (expected +250)")
                            
                            all_passed = all("✓" in c for c in checks)
                            log_test("Test 9: single source", all_passed, "; ".join(checks), resp)

    # ========================================================================
    # TEST 10: materialize preservation
    # ========================================================================
    print("\n" + "=" * 80)
    print("TEST 10: materialize preservation")
    print("=" * 80)
    
    commitment10 = create_commitment(token, {
        "type": "fixed_expense",
        "description": "Limpeza Escritório",
        "total_amount": 750,
        "payment_method": "account",
        "day_of_month": 10
    })
    
    if not commitment10:
        log_test("Test 10: materialize", False, "Failed to create commitment", None)
    else:
        detail10 = get_commitment_detail(token, commitment10["id"])
        if not detail10:
            log_test("Test 10: materialize", False, "Failed to get commitment detail", None)
        else:
            occurrences10 = detail10.get("occurrences", [])
            c1_occ10 = next((o for o in occurrences10 if o["competence"] == c1), None)
            
            if not c1_occ10:
                log_test("Test 10: materialize", False, "C1 occurrence not found", None)
            else:
                # Patch C1 to 1234
                status, resp = patch_occurrence(token, c1_occ10["id"], 1234, "single")
                if status != 200:
                    log_test("Test 10: materialize", False, f"Failed to patch: {status}", resp)
                else:
                    # Materialize
                    mat_status, mat_resp = materialize_all(token)
                    if mat_status != 200:
                        log_test("Test 10: materialize", False, f"Failed to materialize: {mat_status}", mat_resp)
                    else:
                        # Re-fetch C1
                        detail10_after = get_commitment_detail(token, commitment10["id"])
                        if not detail10_after:
                            log_test("Test 10: materialize", False, "Failed to get commitment after materialize", None)
                        else:
                            occs_after = detail10_after.get("occurrences", [])
                            c1_after = next((o for o in occs_after if o["competence"] == c1), None)
                            
                            if c1_after and c1_after["amount"] == 1234 and c1_after["amount_source"] == "override":
                                log_test("Test 10: materialize", True, f"C1 preserved: amount=1234, amount_source=override", mat_resp)
                            else:
                                log_test("Test 10: materialize", False, f"C1 NOT preserved: amount={c1_after['amount'] if c1_after else 'N/A'}, source={c1_after['amount_source'] if c1_after else 'N/A'}", mat_resp)

    # ========================================================================
    # TEST 11: non-existent occurrence
    # ========================================================================
    print("\n" + "=" * 80)
    print("TEST 11: non-existent occurrence")
    print("=" * 80)
    
    fake_id = "000000000000000000000000"
    status, response = patch_occurrence(token, fake_id, 500, "single")
    
    if status == 404:
        log_test("Test 11: non-existent", True, "Correctly returned 404 for non-existent occurrence", response)
    else:
        log_test("Test 11: non-existent", False, f"Expected 404, got {status}", response)

    # ========================================================================
    # REGRESSION SMOKE TESTS
    # ========================================================================
    print("\n" + "=" * 80)
    print("REGRESSION SMOKE TESTS")
    print("=" * 80)
    
    # Test login with demo user
    print("\n[SMOKE] Testing demo user login...")
    demo_token = login(DEMO_EMAIL, DEMO_PASSWORD)
    if demo_token:
        log_test("Smoke: Demo login", True, "Demo user login successful", None)
    else:
        log_test("Smoke: Demo login", False, "Demo user login failed", None)
    
    # Test dashboard
    print("\n[SMOKE] Testing dashboard...")
    dashboard = get_dashboard(token)
    if dashboard and isinstance(dashboard, dict):
        log_test("Smoke: Dashboard", True, f"Dashboard returned valid data with keys: {list(dashboard.keys())}", None)
    else:
        log_test("Smoke: Dashboard", False, "Dashboard failed or returned invalid data", None)
    
    # Test AI context
    print("\n[SMOKE] Testing AI context...")
    ai_context = get_ai_context(token)
    if ai_context and isinstance(ai_context, dict):
        log_test("Smoke: AI context", True, f"AI context returned valid data", None)
    else:
        log_test("Smoke: AI context", False, "AI context failed or returned invalid data", None)

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for r in test_results if r.passed)
    failed = sum(1 for r in test_results if not r.passed)
    total = len(test_results)
    
    print(f"\nTotal: {total} | Passed: {passed} | Failed: {failed}")
    print("\nDetailed Results:")
    for i, result in enumerate(test_results, 1):
        status = "✅" if result.passed else "❌"
        print(f"{i}. {status} {result.rule}")
        if not result.passed:
            print(f"   └─ {result.details}")
    
    return test_results


if __name__ == "__main__":
    results = run_tests()
    
    # Exit with appropriate code
    failed_count = sum(1 for r in results if not r.passed)
    exit(0 if failed_count == 0 else 1)
