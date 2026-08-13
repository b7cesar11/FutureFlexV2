#!/usr/bin/env python3
"""
ETAPA 5 Backend Regression Testing
Validates the additive change: 'overdue' field now exposed in dashboard/overview
"""
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Backend URL from frontend/.env
BASE_URL = "https://5e88b598-cbef-4739-9a5d-a884398bfa5d.preview.emergentagent.com/api"

# Test credentials
DEMO_EMAIL = "demo@futureflex.dev"
DEMO_PASSWORD = "Demo@2026"

# Test results tracking
test_results = []


class TestResult:
    def __init__(self, test_name: str, passed: bool, details: str, response: Optional[Dict] = None):
        self.test_name = test_name
        self.passed = passed
        self.details = details
        self.response = response


def log_test(test_name: str, passed: bool, details: str, response: Optional[Dict] = None):
    """Log test result"""
    test_results.append(TestResult(test_name, passed, details, response))
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"\n{status} | {test_name}")
    print(f"Details: {details}")
    if response and not passed:
        print(f"Response: {json.dumps(response, indent=2)[:500]}")


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


def get_current_competence() -> str:
    """Get current competence (YYYY-MM)"""
    return datetime.now().strftime("%Y-%m")


def get_past_competence() -> str:
    """Get past competence (last month)"""
    last_month = datetime.now() - timedelta(days=35)
    return last_month.strftime("%Y-%m")


def api_get(token: str, endpoint: str) -> tuple[int, Optional[Dict]]:
    """Generic GET request"""
    try:
        response = requests.get(
            f"{BASE_URL}{endpoint}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        data = response.json() if response.status_code == 200 else None
        return response.status_code, data
    except Exception as e:
        print(f"GET {endpoint} error: {e}")
        return 0, None


def api_post(token: str, endpoint: str, payload: Dict) -> tuple[int, Optional[Dict]]:
    """Generic POST request"""
    try:
        response = requests.post(
            f"{BASE_URL}{endpoint}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        data = response.json() if response.status_code in [200, 201] else None
        return response.status_code, data
    except Exception as e:
        print(f"POST {endpoint} error: {e}")
        return 0, None


def run_etapa5_tests():
    """Run ETAPA 5 regression tests"""
    print("=" * 80)
    print("ETAPA 5 Backend Regression Testing")
    print("=" * 80)

    # Login with demo user
    print("\n[SETUP] Logging in with demo user...")
    token = login(DEMO_EMAIL, DEMO_PASSWORD)
    if not token:
        print("❌ CRITICAL: Failed to login. Aborting tests.")
        return

    print(f"✅ Logged in as {DEMO_EMAIL}")

    current_comp = get_current_competence()
    print(f"\n[INFO] Current competence: {current_comp}")

    # ========================================================================
    # TEST 1: GET /api/overview returns 'overdue' field
    # ========================================================================
    print("\n" + "=" * 80)
    print("TEST 1: GET /api/overview returns 'overdue' field")
    print("=" * 80)

    status, overview_data = api_get(token, "/overview")
    if status != 200 or not overview_data:
        log_test("1. GET /api/overview returns 'overdue'", False, 
                f"Failed to get overview: status={status}", overview_data)
    else:
        has_overdue = "overdue" in overview_data
        overdue_value = overview_data.get("overdue")
        is_numeric = isinstance(overdue_value, (int, float))
        
        if has_overdue and is_numeric:
            log_test("1. GET /api/overview returns 'overdue'", True,
                    f"'overdue' field present and numeric: {overdue_value}", None)
        else:
            log_test("1. GET /api/overview returns 'overdue'", False,
                    f"'overdue' field missing or not numeric. has_overdue={has_overdue}, is_numeric={is_numeric}",
                    overview_data)

    # ========================================================================
    # TEST 2: GET /api/overview anti-double-counting (committed == paid + pending)
    # ========================================================================
    print("\n" + "=" * 80)
    print("TEST 2: GET /api/overview anti-double-counting")
    print("=" * 80)

    if overview_data:
        committed = overview_data.get("committed", 0)
        paid = overview_data.get("paid", 0)
        pending = overview_data.get("pending", 0)
        overdue = overview_data.get("overdue", 0)
        
        # Check committed == paid + pending (within rounding tolerance)
        expected_committed = paid + pending
        diff = abs(committed - expected_committed)
        
        checks = []
        if diff <= 0.02:  # Allow 2 cent rounding tolerance
            checks.append(f"committed ({committed}) == paid ({paid}) + pending ({pending}) ✓")
        else:
            checks.append(f"committed ({committed}) != paid ({paid}) + pending ({pending}), diff={diff} ✗")
        
        # Check overdue <= pending
        if overdue <= pending + 0.01:  # Small tolerance
            checks.append(f"overdue ({overdue}) <= pending ({pending}) ✓")
        else:
            checks.append(f"overdue ({overdue}) > pending ({pending}) ✗")
        
        all_passed = all("✓" in c for c in checks)
        log_test("2. GET /api/overview anti-double-counting", all_passed, "; ".join(checks), None)
    else:
        log_test("2. GET /api/overview anti-double-counting", False, "No overview data available", None)

    # ========================================================================
    # TEST 3: GET /api/overview backward compatibility (all expected fields)
    # ========================================================================
    print("\n" + "=" * 80)
    print("TEST 3: GET /api/overview backward compatibility")
    print("=" * 80)

    if overview_data:
        required_fields = [
            "balance", "free_now", "income_expected", "committed", "paid", "pending",
            "next_invoice", "next_commitments", "subscriptions", "health",
            "third_parties", "frozen", "trend", "next_months"
        ]
        
        missing_fields = [f for f in required_fields if f not in overview_data]
        
        if not missing_fields:
            log_test("3. GET /api/overview backward compatibility", True,
                    f"All {len(required_fields)} required fields present", None)
        else:
            log_test("3. GET /api/overview backward compatibility", False,
                    f"Missing fields: {missing_fields}", overview_data)
    else:
        log_test("3. GET /api/overview backward compatibility", False, "No overview data available", None)

    # ========================================================================
    # TEST 4: GET /api/dashboard returns 'overdue' field
    # ========================================================================
    print("\n" + "=" * 80)
    print("TEST 4: GET /api/dashboard returns 'overdue' field")
    print("=" * 80)

    status, dashboard_data = api_get(token, "/dashboard")
    if status != 200 or not dashboard_data:
        log_test("4. GET /api/dashboard returns 'overdue'", False,
                f"Failed to get dashboard: status={status}", dashboard_data)
    else:
        has_overdue = "overdue" in dashboard_data
        overdue_value = dashboard_data.get("overdue")
        is_numeric = isinstance(overdue_value, (int, float))
        
        if has_overdue and is_numeric:
            log_test("4. GET /api/dashboard returns 'overdue'", True,
                    f"'overdue' field present and numeric: {overdue_value}", None)
        else:
            log_test("4. GET /api/dashboard returns 'overdue'", False,
                    f"'overdue' field missing or not numeric. has_overdue={has_overdue}, is_numeric={is_numeric}",
                    dashboard_data)

    # ========================================================================
    # TEST 5: GET /api/dashboard backward compatibility
    # ========================================================================
    print("\n" + "=" * 80)
    print("TEST 5: GET /api/dashboard backward compatibility")
    print("=" * 80)

    if dashboard_data:
        required_fields = [
            "competence", "balance", "free_now", "income_expected", "committed",
            "paid", "pending", "progress_pct", "accounts", "open_invoices",
            "next_months", "insights"
        ]
        
        missing_fields = [f for f in required_fields if f not in dashboard_data]
        
        if not missing_fields:
            log_test("5. GET /api/dashboard backward compatibility", True,
                    f"All {len(required_fields)} required fields present", None)
        else:
            log_test("5. GET /api/dashboard backward compatibility", False,
                    f"Missing fields: {missing_fields}", dashboard_data)
    else:
        log_test("5. GET /api/dashboard backward compatibility", False, "No dashboard data available", None)

    # ========================================================================
    # TEST 6: GET /api/months/{current} anti-double-counting
    # ========================================================================
    print("\n" + "=" * 80)
    print("TEST 6: GET /api/months/{current} anti-double-counting")
    print("=" * 80)

    status, month_data = api_get(token, f"/months/{current_comp}")
    if status != 200 or not month_data:
        log_test("6. GET /api/months/{current} anti-double-counting", False,
                f"Failed to get month view: status={status}", month_data)
    else:
        committed = month_data.get("committed", 0)
        paid = month_data.get("paid", 0)
        pending = month_data.get("pending", 0)
        overdue = month_data.get("overdue", 0)
        
        expected_committed = paid + pending
        diff = abs(committed - expected_committed)
        
        checks = []
        if diff <= 0.02:
            checks.append(f"committed ({committed}) == paid ({paid}) + pending ({pending}) ✓")
        else:
            checks.append(f"committed ({committed}) != paid ({paid}) + pending ({pending}), diff={diff} ✗")
        
        if overdue <= pending + 0.01:
            checks.append(f"overdue ({overdue}) <= pending ({pending}) ✓")
        else:
            checks.append(f"overdue ({overdue}) > pending ({pending}) ✗")
        
        all_passed = all("✓" in c for c in checks)
        log_test("6. GET /api/months/{current} anti-double-counting", all_passed, "; ".join(checks), None)

    # ========================================================================
    # ETAPA 4 QUICK REGRESSION CHECKS
    # ========================================================================
    print("\n" + "=" * 80)
    print("ETAPA 4 QUICK REGRESSION CHECKS")
    print("=" * 80)

    # Create a fresh user for clean testing
    print("\n[SETUP] Creating fresh test user for ETAPA 4 regression...")
    timestamp = int(datetime.now().timestamp())
    test_email = f"etapa5reg+{timestamp}@futureflex.dev"
    test_password = "Test@2026"
    test_name = "Etapa 5 Regression Tester"
    
    test_token = register_user(test_email, test_password, test_name)
    if not test_token:
        log_test("ETAPA 4 Regression Setup", False, "Failed to register test user", None)
    else:
        print(f"✅ Test user registered: {test_email}")
        
        # Create account
        account_id = create_account(test_token, "Banco Teste", "checking", 10000.0)
        if not account_id:
            log_test("ETAPA 4 Regression Setup", False, "Failed to create account", None)
        else:
            print(f"✅ Account created: {account_id}")
            
            # Create a past-due commitment (last month, day 5)
            past_comp = get_past_competence()
            past_commitment = create_commitment(test_token, {
                "type": "fixed_expense",
                "description": "Aluguel Atrasado",
                "total_amount": 1500,
                "payment_method": "account",
                "day_of_month": 5,
                "start_competence": past_comp
            })
            
            if past_commitment:
                print(f"✅ Past commitment created for {past_comp}")
                
                # Materialize to create occurrences
                mat_status, mat_data = api_post(test_token, "/commitments/materialize", {})
                if mat_status == 200:
                    print("✅ Commitments materialized")
                    
                    # Get occurrences for past month
                    status, occs = api_get(test_token, f"/occurrences?competence={past_comp}")
                    if status == 200 and occs:
                        past_occ = next((o for o in occs if o.get("competence") == past_comp), None)
                        
                        if past_occ:
                            # TEST 7a: Past-due unpaid occurrence derives status 'overdue'
                            occ_status = past_occ.get("status")
                            if occ_status == "overdue":
                                log_test("7a. Past-due occurrence derives 'overdue'", True,
                                        f"Occurrence status: {occ_status}", None)
                            else:
                                log_test("7a. Past-due occurrence derives 'overdue'", False,
                                        f"Expected 'overdue', got '{occ_status}'", past_occ)
                            
                            # TEST 7b: Pay the overdue occurrence
                            pay_status, pay_data = api_post(test_token, 
                                                           f"/occurrences/{past_occ['id']}/pay",
                                                           {"account_id": account_id})
                            if pay_status == 200:
                                log_test("7b. Pay overdue occurrence", True,
                                        "Overdue occurrence paid successfully", None)
                                
                                # TEST 7c: Verify occurrence is now 'paid'
                                status, occs_after = api_get(test_token, f"/occurrences?competence={past_comp}")
                                if status == 200 and occs_after:
                                    paid_occ = next((o for o in occs_after if o.get("id") == past_occ["id"]), None)
                                    if paid_occ and paid_occ.get("status") == "paid":
                                        log_test("7c. Paid occurrence status is 'paid'", True,
                                                f"Status after payment: {paid_occ.get('status')}", None)
                                    else:
                                        log_test("7c. Paid occurrence status is 'paid'", False,
                                                f"Expected 'paid', got '{paid_occ.get('status') if paid_occ else 'N/A'}'",
                                                paid_occ)
                                
                                # TEST 7d: Try to pay again (should return 409)
                                pay2_status, pay2_data = api_post(test_token,
                                                                 f"/occurrences/{past_occ['id']}/pay",
                                                                 {"account_id": account_id})
                                if pay2_status == 409:
                                    log_test("7d. Double-payment protection (409)", True,
                                            "Second payment correctly rejected with 409", None)
                                else:
                                    log_test("7d. Double-payment protection (409)", False,
                                            f"Expected 409, got {pay2_status}", pay2_data)
                            else:
                                log_test("7b. Pay overdue occurrence", False,
                                        f"Payment failed: status={pay_status}", pay_data)
            
            # Create credit card for invoice test
            card_status, card_data = api_post(test_token, "/credit-cards", {
                "name": "Cartão Teste",
                "limit": 5000,
                "closing_day": 28,
                "due_day": 5
            })
            
            if card_status == 200 and card_data:
                card_id = card_data.get("id")
                print(f"✅ Credit card created: {card_id}")
                
                # Create purchase installment
                purchase = create_commitment(test_token, {
                    "type": "purchase_installment",
                    "description": "Notebook",
                    "total_amount": 2400,
                    "installments_total": 12,
                    "payment_method": "credit_card",
                    "credit_card_id": card_id
                })
                
                if purchase:
                    print("✅ Purchase installment created")
                    
                    # Materialize
                    mat_status, mat_data = api_post(test_token, "/commitments/materialize", {})
                    if mat_status == 200:
                        # Get purchase occurrences
                        status, purchase_occs = api_get(test_token, f"/occurrences?competence={current_comp}")
                        if status == 200 and purchase_occs:
                            purchase_occ = next((o for o in purchase_occs 
                                               if o.get("kind") == "purchase" and o.get("competence") == current_comp),
                                              None)
                            
                            if purchase_occ:
                                # TEST 7e: Cannot pay purchase occurrence directly (should return 400)
                                pay_status, pay_data = api_post(test_token,
                                                               f"/occurrences/{purchase_occ['id']}/pay",
                                                               {"account_id": account_id})
                                if pay_status == 400:
                                    log_test("7e. Cannot pay invoice-child directly (400)", True,
                                            "Purchase occurrence payment correctly rejected with 400", None)
                                else:
                                    log_test("7e. Cannot pay invoice-child directly (400)", False,
                                            f"Expected 400, got {pay_status}", pay_data)

    # ========================================================================
    # SMOKE TESTS
    # ========================================================================
    print("\n" + "=" * 80)
    print("SMOKE TESTS")
    print("=" * 80)

    smoke_endpoints = [
        ("/dashboard", "Dashboard"),
        ("/overview", "Overview"),
        (f"/months/{current_comp}", "Month view"),
        ("/free-money", "Free money"),
        ("/projection", "Projection"),
        ("/health-score", "Health score"),
        ("/subscriptions", "Subscriptions"),
        ("/ai/context", "AI context"),
        ("/frozen", "Frozen"),
        ("/third-parties", "Third parties"),
    ]

    for endpoint, name in smoke_endpoints:
        status, data = api_get(token, endpoint)
        if status == 200 and data:
            log_test(f"SMOKE: {name}", True, f"GET {endpoint} returned 200", None)
        else:
            log_test(f"SMOKE: {name}", False, f"GET {endpoint} failed: status={status}", data)

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
        print(f"{i}. {status} {result.test_name}")
        if not result.passed:
            print(f"   └─ {result.details}")

    return test_results


if __name__ == "__main__":
    results = run_etapa5_tests()
    
    # Exit with appropriate code
    failed_count = sum(1 for r in results if not r.passed)
    exit(0 if failed_count == 0 else 1)
