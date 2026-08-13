#!/usr/bin/env python3
"""
ETAPA 4 Backend Validation: Financial Lifecycle (PENDING/PAID/OVERDUE + Payment)
This is a VALIDATION-ONLY script - NO code modifications.
"""
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Backend URL
BASE_URL = "https://5e88b598-cbef-4739-9a5d-a884398bfa5d.preview.emergentagent.com/api"

# Test credentials
DEMO_EMAIL = "demo@futureflex.dev"
DEMO_PASSWORD = "Demo@2026"

# Test results tracking
test_results = []


class TestResult:
    def __init__(self, scenario: str, passed: bool, details: str, response: Optional[Dict] = None):
        self.scenario = scenario
        self.passed = passed
        self.details = details
        self.response = response


def log_test(scenario: str, passed: bool, details: str, response: Optional[Dict] = None):
    """Log test result"""
    test_results.append(TestResult(scenario, passed, details, response))
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"\n{status} | Scenario {scenario}")
    print(f"Details: {details}")
    if response and not passed:
        print(f"Response: {json.dumps(response, indent=2)[:500]}")


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
        return None
    except Exception as e:
        print(f"Account creation error: {e}")
        return None


def get_account(token: str, account_id: str) -> Optional[Dict]:
    """Get account details by fetching list and filtering"""
    try:
        response = requests.get(
            f"{BASE_URL}/accounts",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if response.status_code == 200:
            accounts = response.json()
            return next((acc for acc in accounts if acc["id"] == account_id), None)
        return None
    except Exception as e:
        print(f"Get account error: {e}")
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
        return None
    except Exception as e:
        print(f"Get commitment error: {e}")
        return None


def get_occurrences(token: str, competence: str = None, status: str = None) -> Optional[list]:
    """Get occurrences with optional filters"""
    try:
        params = {}
        if competence:
            params["competence"] = competence
        if status:
            params["status"] = status
        response = requests.get(
            f"{BASE_URL}/occurrences",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Get occurrences error: {e}")
        return None


def pay_occurrence(token: str, occurrence_id: str, account_id: str, amount: float = None) -> tuple[int, Optional[Dict]]:
    """Pay an occurrence"""
    try:
        payload = {"account_id": account_id}
        if amount:
            payload["amount"] = amount
        response = requests.post(
            f"{BASE_URL}/occurrences/{occurrence_id}/pay",
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": f"test-{occurrence_id}-{datetime.now().timestamp()}"
            },
            timeout=10
        )
        data = response.json() if response.status_code in [200, 404, 409, 400] else None
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


def get_transactions(token: str, occurrence_id: str = None) -> Optional[list]:
    """Get transactions with optional filter"""
    try:
        params = {}
        if occurrence_id:
            params["occurrence_id"] = occurrence_id
        response = requests.get(
            f"{BASE_URL}/transactions",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Get transactions error: {e}")
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
        return None
    except Exception as e:
        print(f"Credit card creation error: {e}")
        return None


def pay_invoice(token: str, invoice_id: str, account_id: str) -> tuple[int, Optional[Dict]]:
    """Pay an invoice"""
    try:
        response = requests.post(
            f"{BASE_URL}/invoices/{invoice_id}/pay",
            json={"account_id": account_id},
            headers={
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": f"test-invoice-{invoice_id}-{datetime.now().timestamp()}"
            },
            timeout=10
        )
        data = response.json() if response.status_code in [200, 404, 409] else None
        return response.status_code, data
    except Exception as e:
        print(f"Pay invoice error: {e}")
        return 0, None


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
        return None


def get_subscriptions(token: str) -> Optional[list]:
    """Get subscriptions"""
    try:
        response = requests.get(
            f"{BASE_URL}/subscriptions",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        return None


def get_health_score(token: str) -> Optional[Dict]:
    """Get health score"""
    try:
        response = requests.get(
            f"{BASE_URL}/health-score",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        return None


def get_current_competence() -> str:
    """Get current competence (YYYY-MM)"""
    return datetime.now().strftime("%Y-%m")


def get_past_competence(months_ago: int) -> str:
    """Get past competence"""
    dt = datetime.now() - timedelta(days=30 * months_ago)
    return dt.strftime("%Y-%m")


def get_future_competence(months_ahead: int) -> str:
    """Get future competence"""
    current = datetime.now()
    month = current.month + months_ahead
    year = current.year
    while month > 12:
        month -= 12
        year += 1
    return f"{year:04d}-{month:02d}"


def run_etapa4_tests():
    """Run all ETAPA 4 validation tests"""
    print("=" * 80)
    print("ETAPA 4 Backend Validation: Financial Lifecycle")
    print("=" * 80)

    # Setup: Register fresh user
    print("\n[SETUP] Registering fresh test user...")
    timestamp = int(datetime.now().timestamp())
    test_email = f"etapa4test+{timestamp}@futureflex.dev"
    test_password = "Test@2026"
    test_name = "Etapa 4 Tester"
    
    token = register_user(test_email, test_password, test_name)
    if not token:
        print("❌ CRITICAL: Failed to register test user. Aborting tests.")
        return

    print(f"✅ User registered: {test_email}")

    # Create account
    print("\n[SETUP] Creating checking account...")
    account_id = create_account(token, "Banco Itaú", "checking", 50000.0)
    if not account_id:
        print("❌ CRITICAL: Failed to create account. Aborting tests.")
        return
    print(f"✅ Account created: {account_id}")

    # Get competences
    current_comp = get_current_competence()
    past_comp = get_past_competence(2)  # 2 months ago for overdue
    future_comp = get_future_competence(1)
    print(f"\n[INFO] Competences: PAST={past_comp}, CURRENT={current_comp}, FUTURE={future_comp}")

    # ========================================================================
    # SCENARIO 1: Future not-yet-due occurrence => status future/due (PENDING)
    # ========================================================================
    print("\n" + "=" * 80)
    print("SCENARIO 1: Future not-yet-due occurrence => status future/due")
    print("=" * 80)
    
    commitment1 = create_commitment(token, {
        "type": "fixed_expense",
        "description": "Aluguel Escritório",
        "total_amount": 2500,
        "payment_method": "account",
        "day_of_month": 5
    })
    
    if not commitment1:
        log_test("1", False, "Failed to create commitment", None)
    else:
        detail1 = get_commitment_detail(token, commitment1["id"])
        if detail1:
            future_occ = next((o for o in detail1["occurrences"] if o["competence"] == future_comp), None)
            if future_occ:
                status = future_occ.get("status")
                if status in ["future", "due"]:
                    log_test("1", True, f"Future occurrence has status '{status}' (PENDING equivalent)", None)
                else:
                    log_test("1", False, f"Expected status 'future' or 'due', got '{status}'", future_occ)
            else:
                log_test("1", False, "Future occurrence not found", None)
        else:
            log_test("1", False, "Failed to get commitment detail", None)

    # ========================================================================
    # SCENARIO 2: Past-due unpaid occurrence => status overdue
    # ========================================================================
    print("\n" + "=" * 80)
    print("SCENARIO 2: Past-due unpaid occurrence => status overdue")
    print("=" * 80)
    
    # Create a recurring commitment with day_of_month=1 so past occurrences are overdue
    commitment2 = create_commitment(token, {
        "type": "fixed_expense",
        "description": "Conta de Luz",
        "total_amount": 750,
        "payment_method": "account",
        "day_of_month": 1
    })
    
    if not commitment2:
        log_test("2", False, "Failed to create commitment", None)
    else:
        # Materialize to ensure past occurrences exist
        materialize_all(token)
        detail2 = get_commitment_detail(token, commitment2["id"])
        if detail2:
            past_occ = next((o for o in detail2["occurrences"] if o["competence"] == past_comp and o["paid_amount"] == 0), None)
            if past_occ:
                status = past_occ.get("status")
                if status == "overdue":
                    log_test("2", True, f"Past-due unpaid occurrence has status 'overdue'", None)
                else:
                    log_test("2", False, f"Expected status 'overdue', got '{status}'", past_occ)
            else:
                log_test("2", False, f"Past unpaid occurrence not found in {past_comp}", None)
        else:
            log_test("2", False, "Failed to get commitment detail", None)

    # ========================================================================
    # SCENARIO 3: Fully-paid occurrence => status paid
    # ========================================================================
    print("\n" + "=" * 80)
    print("SCENARIO 3: Fully-paid occurrence => status paid")
    print("=" * 80)
    
    commitment3 = create_commitment(token, {
        "type": "fixed_expense",
        "description": "Internet Fibra",
        "total_amount": 150,
        "payment_method": "account",
        "day_of_month": 10
    })
    
    if not commitment3:
        log_test("3", False, "Failed to create commitment", None)
    else:
        detail3 = get_commitment_detail(token, commitment3["id"])
        if detail3:
            current_occ = next((o for o in detail3["occurrences"] if o["competence"] == current_comp), None)
            if current_occ:
                # Pay the occurrence
                pay_status, pay_resp = pay_occurrence(token, current_occ["id"], account_id)
                if pay_status == 200:
                    # Re-fetch to check status
                    detail3_after = get_commitment_detail(token, commitment3["id"])
                    if detail3_after:
                        paid_occ = next((o for o in detail3_after["occurrences"] if o["id"] == current_occ["id"]), None)
                        if paid_occ and paid_occ.get("status") == "paid":
                            log_test("3", True, "Fully-paid occurrence has status 'paid'", None)
                        else:
                            log_test("3", False, f"Expected status 'paid', got '{paid_occ.get('status') if paid_occ else 'N/A'}'", paid_occ)
                    else:
                        log_test("3", False, "Failed to re-fetch commitment", None)
                else:
                    log_test("3", False, f"Failed to pay occurrence: {pay_status}", pay_resp)
            else:
                log_test("3", False, "Current occurrence not found", None)
        else:
            log_test("3", False, "Failed to get commitment detail", None)

    # ========================================================================
    # SCENARIO 4: OVERDUE occurrence can be paid => becomes paid + Transaction created
    # ========================================================================
    print("\n" + "=" * 80)
    print("SCENARIO 4: OVERDUE occurrence can be paid => becomes paid + Transaction created")
    print("=" * 80)
    
    if commitment2:
        detail2_s4 = get_commitment_detail(token, commitment2["id"])
        if detail2_s4:
            overdue_occ = next((o for o in detail2_s4["occurrences"] 
                               if o["competence"] == past_comp and o["status"] == "overdue"), None)
            if overdue_occ:
                # Get transactions before payment
                txs_before = get_transactions(token, overdue_occ["id"])
                count_before = len(txs_before) if txs_before else 0
                
                # Pay the overdue occurrence
                pay_status, pay_resp = pay_occurrence(token, overdue_occ["id"], account_id)
                if pay_status == 200:
                    # Check status changed to paid
                    detail2_after = get_commitment_detail(token, commitment2["id"])
                    if detail2_after:
                        paid_occ = next((o for o in detail2_after["occurrences"] if o["id"] == overdue_occ["id"]), None)
                        
                        # Check transaction created
                        txs_after = get_transactions(token, overdue_occ["id"])
                        count_after = len(txs_after) if txs_after else 0
                        
                        if paid_occ and paid_occ.get("status") == "paid" and count_after == count_before + 1:
                            log_test("4", True, f"Overdue occurrence paid successfully, status='paid', Transaction created (count: {count_before} -> {count_after})", None)
                        else:
                            log_test("4", False, f"Status={paid_occ.get('status') if paid_occ else 'N/A'}, Tx count: {count_before} -> {count_after}", paid_occ)
                    else:
                        log_test("4", False, "Failed to re-fetch commitment", None)
                else:
                    log_test("4", False, f"Failed to pay overdue occurrence: {pay_status}", pay_resp)
            else:
                log_test("4", False, "No overdue occurrence found to test", None)
        else:
            log_test("4", False, "Failed to get commitment detail", None)
    else:
        log_test("4", False, "No commitment available for test", None)

    # ========================================================================
    # SCENARIO 5: Payment uses account chosen in request body and debits THAT account
    # ========================================================================
    print("\n" + "=" * 80)
    print("SCENARIO 5: Payment uses account chosen in request body and debits THAT account")
    print("=" * 80)
    
    # Create second account
    account2_id = create_account(token, "Nubank", "checking", 10000.0)
    if not account2_id:
        log_test("5", False, "Failed to create second account", None)
    else:
        commitment5 = create_commitment(token, {
            "type": "fixed_expense",
            "description": "Telefonia Móvel",
            "total_amount": 200,
            "payment_method": "account",
            "day_of_month": 15
        })
        
        if commitment5:
            detail5 = get_commitment_detail(token, commitment5["id"])
            if detail5:
                current_occ5 = next((o for o in detail5["occurrences"] if o["competence"] == current_comp), None)
                if current_occ5:
                    # Get account2 balance before
                    acc2_before = get_account(token, account2_id)
                    balance_before = acc2_before["current_balance"] if acc2_before else 0
                    
                    # Pay using account2
                    pay_status, pay_resp = pay_occurrence(token, current_occ5["id"], account2_id)
                    if pay_status == 200:
                        # Check account2 balance decreased
                        acc2_after = get_account(token, account2_id)
                        balance_after = acc2_after["current_balance"] if acc2_after else 0
                        expected_balance = balance_before - current_occ5["amount"]
                        
                        if abs(balance_after - expected_balance) < 0.01:
                            log_test("5", True, f"Account2 debited correctly: {balance_before} -> {balance_after} (expected {expected_balance})", None)
                        else:
                            log_test("5", False, f"Account2 balance mismatch: {balance_before} -> {balance_after} (expected {expected_balance})", None)
                    else:
                        log_test("5", False, f"Failed to pay: {pay_status}", pay_resp)
                else:
                    log_test("5", False, "Current occurrence not found", None)
            else:
                log_test("5", False, "Failed to get commitment detail", None)
        else:
            log_test("5", False, "Failed to create commitment", None)

    # ========================================================================
    # SCENARIO 6: Already fully-paid occurrence returns 409 on second pay
    # ========================================================================
    print("\n" + "=" * 80)
    print("SCENARIO 6: Already fully-paid occurrence returns 409 on second pay")
    print("=" * 80)
    
    commitment6 = create_commitment(token, {
        "type": "fixed_expense",
        "description": "Seguro Empresarial",
        "total_amount": 300,
        "payment_method": "account",
        "day_of_month": 20
    })
    
    if commitment6:
        detail6 = get_commitment_detail(token, commitment6["id"])
        if detail6:
            current_occ6 = next((o for o in detail6["occurrences"] if o["competence"] == current_comp), None)
            if current_occ6:
                # Pay once
                pay_status1, _ = pay_occurrence(token, current_occ6["id"], account_id)
                if pay_status1 == 200:
                    # Try to pay again
                    pay_status2, pay_resp2 = pay_occurrence(token, current_occ6["id"], account_id)
                    if pay_status2 == 409:
                        log_test("6", True, "Second payment correctly rejected with 409", None)
                    else:
                        log_test("6", False, f"Expected 409, got {pay_status2}", pay_resp2)
                else:
                    log_test("6", False, f"First payment failed: {pay_status1}", None)
            else:
                log_test("6", False, "Current occurrence not found", None)
        else:
            log_test("6", False, "Failed to get commitment detail", None)
    else:
        log_test("6", False, "Failed to create commitment", None)

    # ========================================================================
    # SCENARIO 7: Second pay attempt creates NO second Transaction
    # ========================================================================
    print("\n" + "=" * 80)
    print("SCENARIO 7: Second pay attempt creates NO second Transaction")
    print("=" * 80)
    
    commitment7 = create_commitment(token, {
        "type": "fixed_expense",
        "description": "Limpeza Escritório",
        "total_amount": 400,
        "payment_method": "account",
        "day_of_month": 25
    })
    
    if commitment7:
        detail7 = get_commitment_detail(token, commitment7["id"])
        if detail7:
            current_occ7 = next((o for o in detail7["occurrences"] if o["competence"] == current_comp), None)
            if current_occ7:
                # Pay once
                pay_status1, _ = pay_occurrence(token, current_occ7["id"], account_id)
                if pay_status1 == 200:
                    # Count transactions
                    txs_after_first = get_transactions(token, current_occ7["id"])
                    count_after_first = len(txs_after_first) if txs_after_first else 0
                    
                    # Try to pay again (should fail with 409)
                    pay_status2, _ = pay_occurrence(token, current_occ7["id"], account_id)
                    
                    # Count transactions again
                    txs_after_second = get_transactions(token, current_occ7["id"])
                    count_after_second = len(txs_after_second) if txs_after_second else 0
                    
                    if count_after_first == 1 and count_after_second == 1:
                        log_test("7", True, f"Transaction count stayed at 1 (no duplicate created)", None)
                    else:
                        log_test("7", False, f"Transaction count: {count_after_first} -> {count_after_second} (expected 1 -> 1)", None)
                else:
                    log_test("7", False, f"First payment failed: {pay_status1}", None)
            else:
                log_test("7", False, "Current occurrence not found", None)
        else:
            log_test("7", False, "Failed to get commitment detail", None)
    else:
        log_test("7", False, "Failed to create commitment", None)

    # ========================================================================
    # SCENARIO 8: NO 'não pago' action creating Transaction
    # ========================================================================
    print("\n" + "=" * 80)
    print("SCENARIO 8: NO 'não pago' action creating Transaction (unpaid has 0 transactions)")
    print("=" * 80)
    
    commitment8 = create_commitment(token, {
        "type": "fixed_expense",
        "description": "Manutenção Predial",
        "total_amount": 500,
        "payment_method": "account",
        "day_of_month": 3
    })
    
    if commitment8:
        materialize_all(token)
        detail8 = get_commitment_detail(token, commitment8["id"])
        if detail8:
            # Find an unpaid occurrence (past or current)
            unpaid_occ = next((o for o in detail8["occurrences"] 
                              if o["paid_amount"] == 0 and o["status"] in ["overdue", "due", "future"]), None)
            if unpaid_occ:
                txs = get_transactions(token, unpaid_occ["id"])
                count = len(txs) if txs else 0
                status = unpaid_occ.get("status")
                
                if count == 0 and status in ["overdue", "due", "future"]:
                    log_test("8", True, f"Unpaid occurrence has 0 transactions and status='{status}' (pending/overdue)", None)
                else:
                    log_test("8", False, f"Unpaid occurrence has {count} transactions and status='{status}'", unpaid_occ)
            else:
                log_test("8", False, "No unpaid occurrence found to test", None)
        else:
            log_test("8", False, "Failed to get commitment detail", None)
    else:
        log_test("8", False, "Failed to create commitment", None)

    # ========================================================================
    # SCENARIO 9: Paid overdue occurrence KEEPS original competence
    # ========================================================================
    print("\n" + "=" * 80)
    print("SCENARIO 9: Paid overdue occurrence KEEPS original competence")
    print("=" * 80)
    
    if commitment2:
        detail2_s9 = get_commitment_detail(token, commitment2["id"])
        if detail2_s9:
            # Find another overdue occurrence
            overdue_occ9 = next((o for o in detail2_s9["occurrences"] 
                                if o["status"] == "overdue" and o["paid_amount"] == 0), None)
            if overdue_occ9:
                original_competence = overdue_occ9["competence"]
                
                # Pay it
                pay_status, _ = pay_occurrence(token, overdue_occ9["id"], account_id)
                if pay_status == 200:
                    # Re-fetch and check competence unchanged
                    detail2_after = get_commitment_detail(token, commitment2["id"])
                    if detail2_after:
                        paid_occ9 = next((o for o in detail2_after["occurrences"] if o["id"] == overdue_occ9["id"]), None)
                        if paid_occ9 and paid_occ9["competence"] == original_competence:
                            log_test("9", True, f"Paid overdue occurrence kept original competence '{original_competence}'", None)
                        else:
                            log_test("9", False, f"Competence changed: {original_competence} -> {paid_occ9['competence'] if paid_occ9 else 'N/A'}", paid_occ9)
                    else:
                        log_test("9", False, "Failed to re-fetch commitment", None)
                else:
                    log_test("9", False, f"Failed to pay: {pay_status}", None)
            else:
                log_test("9", False, "No overdue occurrence found to test", None)
        else:
            log_test("9", False, "Failed to get commitment detail", None)
    else:
        log_test("9", False, "No commitment available for test", None)

    # ========================================================================
    # SCENARIO 10: Materialize does NOT duplicate overdue occurrence
    # ========================================================================
    print("\n" + "=" * 80)
    print("SCENARIO 10: Materialize does NOT duplicate overdue occurrence")
    print("=" * 80)
    
    if commitment2:
        detail2_s10 = get_commitment_detail(token, commitment2["id"])
        if detail2_s10:
            # Count occurrences for past_comp before materialize
            past_occs_before = [o for o in detail2_s10["occurrences"] if o["competence"] == past_comp]
            count_before = len(past_occs_before)
            
            # Materialize again
            mat_status, _ = materialize_all(token)
            if mat_status == 200:
                # Count occurrences for past_comp after materialize
                detail2_after = get_commitment_detail(token, commitment2["id"])
                if detail2_after:
                    past_occs_after = [o for o in detail2_after["occurrences"] if o["competence"] == past_comp]
                    count_after = len(past_occs_after)
                    
                    if count_after == count_before:
                        log_test("10", True, f"Materialize did NOT duplicate: {past_comp} count stayed at {count_before}", None)
                    else:
                        log_test("10", False, f"Materialize duplicated: {past_comp} count {count_before} -> {count_after}", None)
                else:
                    log_test("10", False, "Failed to re-fetch commitment", None)
            else:
                log_test("10", False, f"Materialize failed: {mat_status}", None)
        else:
            log_test("10", False, "Failed to get commitment detail", None)
    else:
        log_test("10", False, "No commitment available for test", None)

    # ========================================================================
    # SCENARIO 11: August overdue and September pending remain distinct
    # ========================================================================
    print("\n" + "=" * 80)
    print("SCENARIO 11: August overdue and September pending remain distinct competences")
    print("=" * 80)
    
    if commitment2:
        detail2_s11 = get_commitment_detail(token, commitment2["id"])
        if detail2_s11:
            # Find past overdue and current/future pending
            past_occ11 = next((o for o in detail2_s11["occurrences"] if o["competence"] == past_comp), None)
            current_occ11 = next((o for o in detail2_s11["occurrences"] if o["competence"] == current_comp), None)
            
            if past_occ11 and current_occ11:
                if past_occ11["competence"] != current_occ11["competence"]:
                    log_test("11", True, f"Two distinct competences exist: {past_occ11['competence']} and {current_occ11['competence']}", None)
                else:
                    log_test("11", False, "Competences are not distinct", None)
            else:
                log_test("11", False, f"Missing occurrences: past={bool(past_occ11)}, current={bool(current_occ11)}", None)
        else:
            log_test("11", False, "Failed to get commitment detail", None)
    else:
        log_test("11", False, "No commitment available for test", None)

    # ========================================================================
    # SCENARIO 12: Credit card purchase does NOT create debit Transaction at purchase
    # ========================================================================
    print("\n" + "=" * 80)
    print("SCENARIO 12: Credit card purchase does NOT create debit Transaction at purchase")
    print("=" * 80)
    
    # Create credit card
    card_id = create_credit_card(token, "Cartão Itaú Platinum", 15000, 28, 5)
    if not card_id:
        log_test("12", False, "Failed to create credit card", None)
    else:
        # Get account balance before
        acc_before = get_account(token, account_id)
        balance_before = acc_before["current_balance"] if acc_before else 0
        
        # Create purchase_installment
        commitment12 = create_commitment(token, {
            "type": "purchase_installment",
            "description": "Notebook Dell",
            "total_amount": 3600,
            "installments_total": 12,
            "payment_method": "credit_card",
            "credit_card_id": card_id
        })
        
        if commitment12:
            # Get account balance after
            acc_after = get_account(token, account_id)
            balance_after = acc_after["current_balance"] if acc_after else 0
            
            # Check balance unchanged
            if abs(balance_after - balance_before) < 0.01:
                # Try to pay occurrence directly (should fail with 400)
                detail12 = get_commitment_detail(token, commitment12["id"])
                if detail12:
                    first_occ = detail12["occurrences"][0] if detail12["occurrences"] else None
                    if first_occ:
                        pay_status, pay_resp = pay_occurrence(token, first_occ["id"], account_id)
                        if pay_status == 400:
                            log_test("12", True, "Purchase did NOT debit account, and direct payment rejected with 400", None)
                        else:
                            log_test("12", False, f"Direct payment should return 400, got {pay_status}", pay_resp)
                    else:
                        log_test("12", False, "No occurrence found", None)
                else:
                    log_test("12", False, "Failed to get commitment detail", None)
            else:
                log_test("12", False, f"Account balance changed unexpectedly: {balance_before} -> {balance_after}", None)
        else:
            log_test("12", False, "Failed to create purchase_installment", None)

    # ========================================================================
    # SCENARIO 13: Paying invoice debits account at that moment
    # ========================================================================
    print("\n" + "=" * 80)
    print("SCENARIO 13: Paying invoice debits account at that moment")
    print("=" * 80)
    
    if card_id:
        # Materialize to create invoices
        materialize_all(token)
        
        # Get invoices for the card
        try:
            response = requests.get(
                f"{BASE_URL}/invoices?credit_card_id={card_id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            if response.status_code == 200:
                invoices = response.json()
                unpaid_invoice = next((inv for inv in invoices if inv["status"] != "paid"), None)
                
                if unpaid_invoice:
                    # Get account balance before
                    acc_before = get_account(token, account_id)
                    balance_before = acc_before["current_balance"] if acc_before else 0
                    
                    invoice_amount = unpaid_invoice["total"]
                    
                    # Pay invoice
                    pay_status, pay_resp = pay_invoice(token, unpaid_invoice["id"], account_id)
                    if pay_status == 200:
                        # Get account balance after
                        acc_after = get_account(token, account_id)
                        balance_after = acc_after["current_balance"] if acc_after else 0
                        expected_balance = balance_before - invoice_amount
                        
                        if abs(balance_after - expected_balance) < 0.01:
                            log_test("13", True, f"Invoice payment debited account: {balance_before} -> {balance_after} (expected {expected_balance})", None)
                        else:
                            log_test("13", False, f"Balance mismatch: {balance_before} -> {balance_after} (expected {expected_balance})", None)
                    else:
                        log_test("13", False, f"Failed to pay invoice: {pay_status}", pay_resp)
                else:
                    log_test("13", False, "No unpaid invoice found", None)
            else:
                log_test("13", False, f"Failed to get invoices: {response.status_code}", None)
        except Exception as e:
            log_test("13", False, f"Error getting invoices: {e}", None)
    else:
        log_test("13", False, "No credit card available for test", None)

    # ========================================================================
    # SCENARIO 14: Month view totals have NO double counting
    # ========================================================================
    print("\n" + "=" * 80)
    print("SCENARIO 14: Month view totals have NO double counting")
    print("=" * 80)
    
    month_view = get_month_view(token, current_comp)
    if month_view:
        committed = month_view.get("committed", 0)
        paid = month_view.get("paid", 0)
        pending = month_view.get("pending", 0)
        overdue = month_view.get("overdue", 0)
        
        # Check committed = paid + pending (approximately, due to rounding)
        expected_committed = paid + pending
        
        # Manual sum of countable outflows from groups
        manual_committed = 0
        for group in month_view.get("groups", []):
            if group.get("counts_in_total"):
                for item in group.get("items", []):
                    if item.get("direction") == "outflow" and item.get("counts_in_total") and not item.get("frozen"):
                        manual_committed += item.get("amount", 0)
        
        checks = []
        if abs(committed - expected_committed) < 1:  # Allow small rounding difference
            checks.append(f"committed={committed} ≈ paid+pending={expected_committed} ✓")
        else:
            checks.append(f"committed={committed} ≠ paid+pending={expected_committed} ✗")
        
        if abs(committed - manual_committed) < 1:
            checks.append(f"committed={committed} ≈ manual_sum={manual_committed} ✓")
        else:
            checks.append(f"committed={committed} ≠ manual_sum={manual_committed} ✗")
        
        all_passed = all("✓" in c for c in checks)
        log_test("14", all_passed, "; ".join(checks), None)
    else:
        log_test("14", False, "Failed to get month view", None)

    # ========================================================================
    # SCENARIO 15: Projection stays consistent (no duplicated overdue)
    # ========================================================================
    print("\n" + "=" * 80)
    print("SCENARIO 15: Projection stays consistent (no duplicated overdue)")
    print("=" * 80)
    
    projection = get_projection(token, 24)
    if projection:
        rows = projection.get("rows", [])
        
        # Check that each competence appears only once
        competences = [row.get("competence") for row in rows]
        unique_competences = set(competences)
        
        if len(competences) == len(unique_competences):
            log_test("15", True, f"Projection has {len(rows)} unique competences (no duplicates)", None)
        else:
            duplicates = [c for c in competences if competences.count(c) > 1]
            log_test("15", False, f"Projection has duplicate competences: {set(duplicates)}", None)
    else:
        log_test("15", False, "Failed to get projection", None)

    # ========================================================================
    # SCENARIO 16: Free money stays consistent
    # ========================================================================
    print("\n" + "=" * 80)
    print("SCENARIO 16: Free money stays consistent")
    print("=" * 80)
    
    free_money = get_free_money(token)
    if free_money:
        free_now = free_money.get("free_now", 0)
        
        # Get total balance and current month pending
        accounts = []
        try:
            response = requests.get(
                f"{BASE_URL}/accounts",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            if response.status_code == 200:
                accounts = response.json()
        except Exception:
            pass
        
        total_balance = sum(acc.get("current_balance", 0) for acc in accounts)
        
        month_view = get_month_view(token, current_comp)
        pending_outflows = month_view.get("pending", 0) if month_view else 0
        
        # free_now should be approximately balance - pending outflows
        expected_free = total_balance - pending_outflows
        
        if abs(free_now - expected_free) < 100:  # Allow some tolerance
            log_test("16", True, f"free_now={free_now} ≈ balance-pending={expected_free} (balance={total_balance}, pending={pending_outflows})", None)
        else:
            log_test("16", False, f"free_now={free_now} ≠ expected={expected_free} (balance={total_balance}, pending={pending_outflows})", None)
    else:
        log_test("16", False, "Failed to get free money", None)

    # ========================================================================
    # SMOKE TESTS
    # ========================================================================
    print("\n" + "=" * 80)
    print("SMOKE TESTS")
    print("=" * 80)
    
    smoke_results = []
    
    # Login
    demo_token = login(DEMO_EMAIL, DEMO_PASSWORD)
    smoke_results.append(("Login", bool(demo_token)))
    
    # Dashboard
    dashboard = get_dashboard(token)
    smoke_results.append(("Dashboard", bool(dashboard)))
    
    # Month view
    month = get_month_view(token, current_comp)
    smoke_results.append(("Month view", bool(month)))
    
    # Free money
    free = get_free_money(token)
    smoke_results.append(("Free money", bool(free)))
    
    # Projection
    proj = get_projection(token, 24)
    smoke_results.append(("Projection", bool(proj)))
    
    # AI context
    ai = get_ai_context(token)
    smoke_results.append(("AI context", bool(ai)))
    
    # Subscriptions
    subs = get_subscriptions(token)
    smoke_results.append(("Subscriptions", bool(subs is not None)))
    
    # Health score
    health = get_health_score(token)
    smoke_results.append(("Health score", bool(health)))
    
    passed_smoke = sum(1 for _, p in smoke_results if p)
    total_smoke = len(smoke_results)
    
    print(f"\nSmoke tests: {passed_smoke}/{total_smoke} passed")
    for name, passed in smoke_results:
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for r in test_results if r.passed)
    failed = sum(1 for r in test_results if not r.passed)
    total = len(test_results)
    
    print(f"\nETAPA 4 Scenarios: {passed}/{total} passed, {failed} failed")
    print(f"Smoke Tests: {passed_smoke}/{total_smoke} passed")
    print("\nDetailed Results:")
    for result in test_results:
        status = "✅" if result.passed else "❌"
        print(f"Scenario {result.scenario}: {status} - {result.details}")
    
    return test_results, smoke_results


if __name__ == "__main__":
    results, smoke = run_etapa4_tests()
    
    # Exit with appropriate code
    failed_count = sum(1 for r in results if not r.passed)
    exit(0 if failed_count == 0 else 1)
