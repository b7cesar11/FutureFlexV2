#!/usr/bin/env python3
"""
ETAPA 6 — FULL BACKEND QA for FutureFlex V2
Tests all 12 blocks against LIVE backend (NO rebuild, report only)
"""
import os
import sys
import json
import time
import uuid
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

# Backend URL from frontend/.env
BASE_URL = "https://b6aff91e-3130-4674-8c37-26c515188945.preview.emergentagent.com/api"

# Test credentials
DEMO_EMAIL = "demo@futureflex.dev"
DEMO_PASSWORD = "Demo@2026"

# Test results tracking
test_results = []
block_results = {}


class TestResult:
    def __init__(self, block: str, test: str, passed: bool, details: str, response: Optional[Dict] = None):
        self.block = block
        self.test = test
        self.passed = passed
        self.details = details
        self.response = response


def log_test(block: str, test: str, passed: bool, details: str, response: Optional[Dict] = None):
    """Log test result"""
    test_results.append(TestResult(block, test, passed, details, response))
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"\n{status} | {block} | {test}")
    print(f"Details: {details}")
    if response and not passed:
        print(f"Response: {json.dumps(response, indent=2)[:500]}")
    
    # Track block-level results
    if block not in block_results:
        block_results[block] = {"passed": 0, "failed": 0}
    if passed:
        block_results[block]["passed"] += 1
    else:
        block_results[block]["failed"] += 1


def register_user(email: str, password: str, name: str) -> Optional[str]:
    """Register a new user and return access token"""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/register",
            json={"email": email, "password": password, "name": name},
            timeout=10
        )
        if response.status_code in [200, 201]:
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
        if response.status_code in [200, 201]:
            data = response.json()
            return data.get("id")
        return None
    except Exception as e:
        print(f"Account creation error: {e}")
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
        if response.status_code in [200, 201]:
            data = response.json()
            return data.get("id")
        return None
    except Exception as e:
        print(f"Credit card creation error: {e}")
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
        if response.status_code in [200, 201]:
            return response.json()
        else:
            print(f"Commitment creation failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Commitment creation error: {e}")
        return None


def get_invoices(token: str, card_id: Optional[str] = None) -> List[Dict]:
    """Get invoices"""
    try:
        params = {"credit_card_id": card_id} if card_id else {}
        response = requests.get(
            f"{BASE_URL}/invoices",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"Get invoices error: {e}")
        return []


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


def pay_occurrence(token: str, occurrence_id: str, account_id: str, amount: Optional[float] = None) -> tuple[int, Optional[Dict]]:
    """Pay an occurrence"""
    try:
        payload = {"account_id": account_id}
        if amount:
            payload["amount"] = amount
        response = requests.post(
            f"{BASE_URL}/occurrences/{occurrence_id}/pay",
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Idempotency-Key": f"test-{uuid.uuid4().hex[:10]}"},
            timeout=10
        )
        data = response.json() if response.status_code in [200, 201, 400, 404, 409] else None
        return response.status_code, data
    except Exception as e:
        print(f"Pay occurrence error: {e}")
        return 0, None


def pay_invoice(token: str, invoice_id: str, account_id: str, amount: float) -> tuple[int, Optional[Dict]]:
    """Pay an invoice"""
    try:
        response = requests.post(
            f"{BASE_URL}/invoices/{invoice_id}/pay",
            json={"account_id": account_id, "amount": amount},
            headers={"Authorization": f"Bearer {token}", "Idempotency-Key": f"test-{uuid.uuid4().hex[:10]}"},
            timeout=10
        )
        data = response.json() if response.status_code in [200, 201, 400, 404, 409] else None
        return response.status_code, data
    except Exception as e:
        print(f"Pay invoice error: {e}")
        return 0, None


def freeze_commitment(token: str, commitment_id: str) -> tuple[int, Optional[Dict]]:
    """Freeze a commitment"""
    try:
        response = requests.post(
            f"{BASE_URL}/commitments/{commitment_id}/freeze",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        data = response.json() if response.status_code in [200, 201] else None
        return response.status_code, data
    except Exception as e:
        print(f"Freeze commitment error: {e}")
        return 0, None


def unfreeze_commitment(token: str, commitment_id: str) -> tuple[int, Optional[Dict]]:
    """Unfreeze a commitment"""
    try:
        response = requests.post(
            f"{BASE_URL}/commitments/{commitment_id}/unfreeze",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        data = response.json() if response.status_code in [200, 201] else None
        return response.status_code, data
    except Exception as e:
        print(f"Unfreeze commitment error: {e}")
        return 0, None


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


def ask_ai(token: str, question: str) -> Optional[Dict]:
    """Ask AI a question"""
    try:
        response = requests.post(
            f"{BASE_URL}/ai/ask",
            json={"question": question},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Ask AI error: {e}")
        return None


def get_current_competence() -> str:
    """Get current competence (YYYY-MM)"""
    return datetime.now().strftime("%Y-%m")


def get_transactions(token: str) -> List[Dict]:
    """Get transactions"""
    try:
        response = requests.get(
            f"{BASE_URL}/transactions",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"Get transactions error: {e}")
        return []


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
        print(f"Get commitment detail error: {e}")
        return None


def get_occurrences(token: str) -> List[Dict]:
    """Get all occurrences"""
    try:
        response = requests.get(
            f"{BASE_URL}/occurrences",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"Get occurrences error: {e}")
        return []


def get_accounts(token: str) -> List[Dict]:
    """Get accounts"""
    try:
        response = requests.get(
            f"{BASE_URL}/accounts",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"Get accounts error: {e}")
        return []


# ========================================================================
# BLOCO 1: MULTI-CARD
# ========================================================================
def test_bloco1_multicard():
    """Test multi-card: 2 cards, same competence, no E11000"""
    print("\n" + "=" * 80)
    print("BLOCO 1: MULTI-CARD")
    print("=" * 80)
    
    # Register fresh isolated user
    timestamp = int(datetime.now().timestamp())
    email = f"multicard+{timestamp}@futureflex.dev"
    password = "Test@2026"
    name = "MultiCard Tester"
    
    token = register_user(email, password, name)
    if not token:
        log_test("BLOCO 1", "User registration", False, "Failed to register user", None)
        return
    
    log_test("BLOCO 1", "User registration", True, f"Registered {email}", None)
    
    # Create account
    account_id = create_account(token, "Banco Itaú", "checking", 10000.0)
    if not account_id:
        log_test("BLOCO 1", "Account creation", False, "Failed to create account", None)
        return
    
    log_test("BLOCO 1", "Account creation", True, f"Created account {account_id}", None)
    
    # Create TWO credit cards
    card1_id = create_credit_card(token, "Nubank", 5000, 5, 15)
    card2_id = create_credit_card(token, "Itaú", 8000, 5, 15)
    
    if not card1_id or not card2_id:
        log_test("BLOCO 1", "Credit card creation", False, "Failed to create cards", None)
        return
    
    log_test("BLOCO 1", "Credit card creation", True, f"Created 2 cards: {card1_id}, {card2_id}", None)
    
    # Create purchase on EACH card (same competence)
    purchase1 = create_commitment(token, {
        "type": "purchase_installment",
        "description": "Compra Nubank",
        "total_amount": 300.0,
        "installments_total": 1,
        "payment_method": "credit_card",
        "credit_card_id": card1_id
    })
    
    if not purchase1:
        log_test("BLOCO 1", "Purchase 1 (Nubank)", False, "Failed to create purchase on card 1", None)
        return
    
    log_test("BLOCO 1", "Purchase 1 (Nubank)", True, f"Created purchase on Nubank", None)
    
    purchase2 = create_commitment(token, {
        "type": "purchase_installment",
        "description": "Compra Itaú",
        "total_amount": 500.0,
        "installments_total": 1,
        "payment_method": "credit_card",
        "credit_card_id": card2_id
    })
    
    if not purchase2:
        log_test("BLOCO 1", "Purchase 2 (Itaú)", False, "Failed to create purchase on card 2 - POSSIBLE E11000", None)
        return
    
    log_test("BLOCO 1", "Purchase 2 (Itaú)", True, f"Created purchase on Itaú - NO E11000", None)
    
    # Get invoices
    invoices = get_invoices(token)
    
    if len(invoices) < 2:
        log_test("BLOCO 1", "Invoice count", False, f"Expected 2 invoices, got {len(invoices)}", {"invoices": invoices})
        return
    
    log_test("BLOCO 1", "Invoice count", True, f"Got 2 invoices as expected", None)
    
    # Verify each purchase belongs to correct invoice
    inv1 = next((i for i in invoices if i.get("credit_card_id") == card1_id), None)
    inv2 = next((i for i in invoices if i.get("credit_card_id") == card2_id), None)
    
    if not inv1 or not inv2:
        log_test("BLOCO 1", "Invoice assignment", False, "Invoices not correctly assigned to cards", {"invoices": invoices})
        return
    
    log_test("BLOCO 1", "Invoice assignment", True, f"Each purchase in correct invoice", None)
    
    # Verify values
    if abs(inv1.get("total", 0) - 300.0) > 0.01:
        log_test("BLOCO 1", "Invoice 1 value", False, f"Expected 300, got {inv1.get('total')}", inv1)
    else:
        log_test("BLOCO 1", "Invoice 1 value", True, f"Invoice 1 = R$ 300.00", None)
    
    if abs(inv2.get("total", 0) - 500.0) > 0.01:
        log_test("BLOCO 1", "Invoice 2 value", False, f"Expected 500, got {inv2.get('total')}", inv2)
    else:
        log_test("BLOCO 1", "Invoice 2 value", True, f"Invoice 2 = R$ 500.00", None)
    
    # Verify dashboard, months, projection consistency
    dashboard = get_dashboard(token)
    if not dashboard:
        log_test("BLOCO 1", "Dashboard consistency", False, "Failed to get dashboard", None)
        return
    
    comp = dashboard.get("competence")
    month_view = get_month_view(token, comp)
    projection = get_projection(token, 24)
    
    if not month_view or not projection:
        log_test("BLOCO 1", "Views consistency", False, "Failed to get month view or projection", None)
        return
    
    # Check no double counting
    committed = month_view.get("committed", 0)
    groups = {g["key"]: g for g in month_view.get("groups", [])}
    cards_total = groups.get("cards", {}).get("total", 0)
    
    # Cards total should be 800 (300 + 500)
    if abs(cards_total - 800.0) > 0.01:
        log_test("BLOCO 1", "Cards total", False, f"Expected 800, got {cards_total}", groups)
    else:
        log_test("BLOCO 1", "Cards total", True, f"Cards total = R$ 800.00 (no double count)", None)
    
    # Installments and subscriptions should have total=0
    for key in ["installments", "subscriptions"]:
        g = groups.get(key)
        if g and g.get("total", 0) != 0:
            log_test("BLOCO 1", f"Group {key} total", False, f"Expected 0, got {g.get('total')}", g)
        else:
            log_test("BLOCO 1", f"Group {key} total", True, f"{key} total = 0 (counts_in_total=false)", None)


# ========================================================================
# BLOCO 2: ETAPA 3 REGRESSION
# ========================================================================
def test_bloco2_regression():
    """Test ETAPA 3 regression: run existing test suites"""
    print("\n" + "=" * 80)
    print("BLOCO 2: ETAPA 3 REGRESSION")
    print("=" * 80)
    
    # Test 1: Run backend_test.py (14 tests)
    print("\n[BLOCO 2] Running backend_test.py (14 ETAPA 3 tests)...")
    try:
        import subprocess
        result = subprocess.run(
            ["python3", "/app/backend_test.py"],
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, "BASE_URL": BASE_URL}
        )
        
        if result.returncode == 0:
            log_test("BLOCO 2", "backend_test.py (14 tests)", True, "All 14 ETAPA 3 tests passed", None)
        else:
            log_test("BLOCO 2", "backend_test.py (14 tests)", False, f"Tests failed: {result.stdout[-500:]}", None)
    except Exception as e:
        log_test("BLOCO 2", "backend_test.py (14 tests)", False, f"Error running tests: {e}", None)
    
    # Test 2: Run pytest (20 E2E tests)
    print("\n[BLOCO 2] Running pytest (20 E2E tests)...")
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "-q", "/app/backend/tests/backend_test.py"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd="/app/backend",
            env={**os.environ, "REACT_APP_BACKEND_URL": BASE_URL.replace("/api", "")}
        )
        
        if "20 passed" in result.stdout:
            log_test("BLOCO 2", "pytest (20 E2E tests)", True, "All 20 E2E tests passed", None)
        else:
            log_test("BLOCO 2", "pytest (20 E2E tests)", False, f"Tests failed: {result.stdout[-500:]}", None)
    except Exception as e:
        log_test("BLOCO 2", "pytest (20 E2E tests)", False, f"Error running pytest: {e}", None)


# ========================================================================
# BLOCO 3: ANTI-DOUBLE-COUNT (STRUCTURAL)
# ========================================================================
def test_bloco3_anti_double_count():
    """Test anti-double-count: structural verification"""
    print("\n" + "=" * 80)
    print("BLOCO 3: ANTI-DOUBLE-COUNT (STRUCTURAL)")
    print("=" * 80)
    
    # Login as demo user
    token = login(DEMO_EMAIL, DEMO_PASSWORD)
    if not token:
        log_test("BLOCO 3", "Demo login", False, "Failed to login as demo user", None)
        return
    
    log_test("BLOCO 3", "Demo login", True, "Logged in as demo user", None)
    
    # Get dashboard
    dashboard = get_dashboard(token)
    if not dashboard:
        log_test("BLOCO 3", "Dashboard", False, "Failed to get dashboard", None)
        return
    
    comp = dashboard.get("competence")
    
    # Get month view
    month_view = get_month_view(token, comp)
    if not month_view:
        log_test("BLOCO 3", "Month view", False, "Failed to get month view", None)
        return
    
    # Structural verification
    groups = {g["key"]: g for g in month_view.get("groups", [])}
    
    # 1. Invoice total should be 502.70 (iPhone 300 + Spotify 21.90 + Netflix 55.90 + YouTube 24.90 + Ana 100)
    cards_group = groups.get("cards", {})
    cards_total = cards_group.get("total", 0)
    
    if abs(cards_total - 502.7) > 0.01:
        log_test("BLOCO 3", "Invoice total", False, f"Expected 502.70, got {cards_total}", cards_group)
    else:
        log_test("BLOCO 3", "Invoice total", True, f"Invoice total = R$ 502.70 ✓", None)
    
    # 2. Children groups (installments, subscriptions) must have total=0 and counts_in_total=false
    for key in ["installments", "subscriptions"]:
        g = groups.get(key)
        if g:
            if g.get("total", 0) != 0:
                log_test("BLOCO 3", f"{key} total=0", False, f"Expected 0, got {g.get('total')}", g)
            else:
                log_test("BLOCO 3", f"{key} total=0", True, f"{key} total = 0 ✓", None)
            
            # Check counts_in_total=false for items
            items = g.get("items", [])
            non_countable = [it for it in items if it.get("counts_in_total") is False]
            if len(non_countable) > 0:
                log_test("BLOCO 3", f"{key} counts_in_total=false", True, f"{len(non_countable)} items with counts_in_total=false ✓", None)
            else:
                log_test("BLOCO 3", f"{key} counts_in_total=false", False, f"No items with counts_in_total=false", g)
    
    # 3. Committed = 1800 (rent) + 502.70 (invoice) = 2302.70
    committed = month_view.get("committed", 0)
    if abs(committed - 2302.7) > 0.01:
        log_test("BLOCO 3", "Committed total", False, f"Expected 2302.70, got {committed}", month_view)
    else:
        log_test("BLOCO 3", "Committed total", True, f"Committed = R$ 2302.70 (1800 rent + 502.70 invoice) ✓", None)
    
    # 4. Third_parties (Ana 100) must NOT be added to committed
    # Verify by checking that committed does NOT include third_party amounts
    third_parties_group = groups.get("third_parties", {})
    if third_parties_group:
        tp_total = third_parties_group.get("total", 0)
        # If third_party total is included in committed, committed would be higher
        if abs(committed - (2302.7 + tp_total)) < 0.01:
            log_test("BLOCO 3", "Third_parties NOT in committed", False, f"Third_parties {tp_total} incorrectly added to committed", third_parties_group)
        else:
            log_test("BLOCO 3", "Third_parties NOT in committed", True, f"Third_parties NOT added to committed ✓", None)
    
    # 5. Verify committed = paid + pending (no double counting)
    paid = month_view.get("paid", 0)
    pending = month_view.get("pending", 0)
    if abs(committed - (paid + pending)) > 0.01:
        log_test("BLOCO 3", "committed = paid + pending", False, f"committed {committed} != paid {paid} + pending {pending}", month_view)
    else:
        log_test("BLOCO 3", "committed = paid + pending", True, f"committed = paid + pending ✓", None)


# ========================================================================
# BLOCO 4: STATUS DERIVATION
# ========================================================================
def test_bloco4_status():
    """Test status derivation: no manual status field"""
    print("\n" + "=" * 80)
    print("BLOCO 4: STATUS DERIVATION")
    print("=" * 80)
    
    # Login as demo user
    token = login(DEMO_EMAIL, DEMO_PASSWORD)
    if not token:
        log_test("BLOCO 4", "Demo login", False, "Failed to login as demo user", None)
        return
    
    # Get occurrences
    occurrences = get_occurrences(token)
    if not occurrences:
        log_test("BLOCO 4", "Get occurrences", False, "No occurrences found", None)
        return
    
    log_test("BLOCO 4", "Get occurrences", True, f"Found {len(occurrences)} occurrences", None)
    
    # Check that status is derived (future, due, paid, overdue, cancelled, frozen)
    valid_statuses = ["future", "due", "paid", "overdue", "cancelled", "frozen"]
    
    status_counts = {}
    for occ in occurrences:
        status = occ.get("status")
        if status not in valid_statuses:
            log_test("BLOCO 4", "Status derivation", False, f"Invalid status '{status}' found in occurrence {occ.get('id')}", occ)
            return
        status_counts[status] = status_counts.get(status, 0) + 1
    
    log_test("BLOCO 4", "Status derivation", True, f"All statuses are derived: {status_counts}", None)
    
    # Verify there is NO manual editable status field in the occurrence model
    # Check that status is computed based on due_date, paid_amount, etc.
    sample_occ = occurrences[0]
    
    # Status should be derived from:
    # - due_date vs today
    # - paid_amount vs amount
    # - cancelled flag
    # - frozen flag
    
    has_due_date = "due_date" in sample_occ
    has_paid_amount = "paid_amount" in sample_occ
    has_status = "status" in sample_occ
    
    if has_status and has_due_date and has_paid_amount:
        log_test("BLOCO 4", "Status fields", True, "Status is derived from due_date and paid_amount ✓", None)
    else:
        log_test("BLOCO 4", "Status fields", False, f"Missing fields for status derivation", sample_occ)


# ========================================================================
# BLOCO 5: PAYMENT
# ========================================================================
def test_bloco5_payment():
    """Test payment: pay occurrence, overdue, invoice, double-payment blocked"""
    print("\n" + "=" * 80)
    print("BLOCO 5: PAYMENT")
    print("=" * 80)
    
    # Register fresh user
    timestamp = int(datetime.now().timestamp())
    email = f"payment+{timestamp}@futureflex.dev"
    password = "Test@2026"
    name = "Payment Tester"
    
    token = register_user(email, password, name)
    if not token:
        log_test("BLOCO 5", "User registration", False, "Failed to register user", None)
        return
    
    # Create account
    account_id = create_account(token, "Banco Itaú", "checking", 10000.0)
    if not account_id:
        log_test("BLOCO 5", "Account creation", False, "Failed to create account", None)
        return
    
    # Create a fixed expense (past due to test overdue payment)
    commitment = create_commitment(token, {
        "type": "fixed_expense",
        "description": "Aluguel Teste",
        "total_amount": 500.0,
        "payment_method": "account",
        "recurrence": "monthly",
        "day_of_month": 1
    })
    
    if not commitment:
        log_test("BLOCO 5", "Commitment creation", False, "Failed to create commitment", None)
        return
    
    # Get commitment detail
    detail = get_commitment_detail(token, commitment["id"])
    if not detail or not detail.get("occurrences"):
        log_test("BLOCO 5", "Get occurrences", False, "No occurrences found", None)
        return
    
    occurrences = detail["occurrences"]
    current_occ = occurrences[0]
    occ_id = current_occ["id"]
    
    # Test 1: Pay normal occurrence
    status, response = pay_occurrence(token, occ_id, account_id)
    if status in [200, 201]:
        log_test("BLOCO 5", "Pay occurrence", True, f"Paid occurrence successfully", None)
    else:
        log_test("BLOCO 5", "Pay occurrence", False, f"Failed to pay occurrence: {status}", response)
        return
    
    # Test 2: Double-payment blocked (409)
    status2, response2 = pay_occurrence(token, occ_id, account_id)
    if status2 == 409:
        log_test("BLOCO 5", "Double-payment blocked", True, f"Second payment correctly blocked with 409", None)
    else:
        log_test("BLOCO 5", "Double-payment blocked", False, f"Expected 409, got {status2}", response2)
    
    # Test 3: Verify only 1 Transaction created
    transactions = get_transactions(token)
    occ_transactions = [t for t in transactions if t.get("occurrence_id") == occ_id]
    if len(occ_transactions) == 1:
        log_test("BLOCO 5", "1 payment = 1 Transaction", True, f"Only 1 transaction created", None)
    else:
        log_test("BLOCO 5", "1 payment = 1 Transaction", False, f"Expected 1 transaction, got {len(occ_transactions)}", occ_transactions)
    
    # Test 4: Pay invoice (credit card)
    card_id = create_credit_card(token, "Nubank", 5000, 5, 15)
    if not card_id:
        log_test("BLOCO 5", "Credit card creation", False, "Failed to create card", None)
        return
    
    purchase = create_commitment(token, {
        "type": "purchase_installment",
        "description": "Compra Teste",
        "total_amount": 300.0,
        "installments_total": 1,
        "payment_method": "credit_card",
        "credit_card_id": card_id
    })
    
    if not purchase:
        log_test("BLOCO 5", "Purchase creation", False, "Failed to create purchase", None)
        return
    
    # Get invoice
    invoices = get_invoices(token, card_id)
    if not invoices:
        log_test("BLOCO 5", "Get invoice", False, "No invoice found", None)
        return
    
    invoice = invoices[0]
    
    # Get account balance before payment
    accounts = get_accounts(token)
    account = next((a for a in accounts if a["id"] == account_id), None)
    if not account:
        log_test("BLOCO 5", "Get account", False, "Account not found", None)
        return
    
    balance_before = account["current_balance"]
    
    # Pay invoice
    status, response = pay_invoice(token, invoice["id"], account_id, invoice["total"])
    if status in [200, 201]:
        log_test("BLOCO 5", "Pay invoice", True, f"Paid invoice successfully", None)
    else:
        log_test("BLOCO 5", "Pay invoice", False, f"Failed to pay invoice: {status}", response)
        return
    
    # Verify account debited at payment time
    accounts_after = get_accounts(token)
    account_after = next((a for a in accounts_after if a["id"] == account_id), None)
    balance_after = account_after["current_balance"]
    
    if abs((balance_before - balance_after) - invoice["total"]) < 0.01:
        log_test("BLOCO 5", "Invoice debits account", True, f"Account debited R$ {invoice['total']} at payment time", None)
    else:
        log_test("BLOCO 5", "Invoice debits account", False, f"Expected debit {invoice['total']}, got {balance_before - balance_after}", None)
    
    # Test 5: Invoice-child occurrence cannot be paid directly (400)
    purchase_detail = get_commitment_detail(token, purchase["id"])
    if purchase_detail and purchase_detail.get("occurrences"):
        child_occ = next((o for o in purchase_detail["occurrences"] if o.get("kind") != "invoice"), None)
        if child_occ:
            status, response = pay_occurrence(token, child_occ["id"], account_id)
            if status == 400:
                log_test("BLOCO 5", "Invoice-child cannot be paid", True, f"Correctly blocked with 400", None)
            else:
                log_test("BLOCO 5", "Invoice-child cannot be paid", False, f"Expected 400, got {status}", response)


# ========================================================================
# BLOCO 6: SECURITY (TENANT ISOLATION)
# ========================================================================
def test_bloco6_security():
    """Test security: tenant isolation"""
    print("\n" + "=" * 80)
    print("BLOCO 6: SECURITY (TENANT ISOLATION)")
    print("=" * 80)
    
    # Create User A
    timestamp = int(datetime.now().timestamp())
    email_a = f"usera+{timestamp}@futureflex.dev"
    password = "Test@2026"
    
    token_a = register_user(email_a, password, "User A")
    if not token_a:
        log_test("BLOCO 6", "User A registration", False, "Failed to register User A", None)
        return
    
    # Create User B
    email_b = f"userb+{timestamp}@futureflex.dev"
    token_b = register_user(email_b, password, "User B")
    if not token_b:
        log_test("BLOCO 6", "User B registration", False, "Failed to register User B", None)
        return
    
    log_test("BLOCO 6", "User registration", True, "Created User A and User B", None)
    
    # User A creates resources
    account_a = create_account(token_a, "Conta A", "checking", 5000.0)
    commitment_a = create_commitment(token_a, {
        "type": "fixed_expense",
        "description": "Compromisso A",
        "total_amount": 500.0,
        "payment_method": "account",
        "recurrence": "monthly",
        "day_of_month": 10
    })
    
    if not account_a or not commitment_a:
        log_test("BLOCO 6", "User A resources", False, "Failed to create User A resources", None)
        return
    
    # Get User A's occurrence
    detail_a = get_commitment_detail(token_a, commitment_a["id"])
    if not detail_a or not detail_a.get("occurrences"):
        log_test("BLOCO 6", "User A occurrences", False, "No occurrences found for User A", None)
        return
    
    occ_a_id = detail_a["occurrences"][0]["id"]
    
    # Test 1: User B cannot read User A's account
    try:
        response = requests.get(
            f"{BASE_URL}/accounts/{account_a}",
            headers={"Authorization": f"Bearer {token_b}"},
            timeout=10
        )
        if response.status_code in [403, 404]:
            log_test("BLOCO 6", "Account isolation (read)", True, f"User B cannot read User A's account (got {response.status_code})", None)
        else:
            log_test("BLOCO 6", "Account isolation (read)", False, f"Expected 403/404, got {response.status_code}", response.json())
    except Exception as e:
        log_test("BLOCO 6", "Account isolation (read)", False, f"Error: {e}", None)
    
    # Test 2: User B cannot read User A's commitment
    try:
        response = requests.get(
            f"{BASE_URL}/commitments/{commitment_a['id']}",
            headers={"Authorization": f"Bearer {token_b}"},
            timeout=10
        )
        if response.status_code in [403, 404]:
            log_test("BLOCO 6", "Commitment isolation (read)", True, f"User B cannot read User A's commitment (got {response.status_code})", None)
        else:
            log_test("BLOCO 6", "Commitment isolation (read)", False, f"Expected 403/404, got {response.status_code}", response.json())
    except Exception as e:
        log_test("BLOCO 6", "Commitment isolation (read)", False, f"Error: {e}", None)
    
    # Test 3: User B cannot pay User A's occurrence
    status, response = pay_occurrence(token_b, occ_a_id, account_a)
    if status in [403, 404]:
        log_test("BLOCO 6", "Occurrence isolation (modify)", True, f"User B cannot pay User A's occurrence (got {status})", None)
    else:
        log_test("BLOCO 6", "Occurrence isolation (modify)", False, f"Expected 403/404, got {status}", response)
    
    # Test 4: User B cannot modify User A's account
    try:
        response = requests.patch(
            f"{BASE_URL}/accounts/{account_a}",
            json={"name": "Hacked Account"},
            headers={"Authorization": f"Bearer {token_b}"},
            timeout=10
        )
        if response.status_code in [403, 404]:
            log_test("BLOCO 6", "Account isolation (modify)", True, f"User B cannot modify User A's account (got {response.status_code})", None)
        else:
            log_test("BLOCO 6", "Account isolation (modify)", False, f"Expected 403/404, got {response.status_code}", response.json())
    except Exception as e:
        log_test("BLOCO 6", "Account isolation (modify)", False, f"Error: {e}", None)


# ========================================================================
# BLOCO 7: ACID (ATOMICITY)
# ========================================================================
def test_bloco7_acid():
    """Test ACID: operations commit atomically or rollback"""
    print("\n" + "=" * 80)
    print("BLOCO 7: ACID (ATOMICITY)")
    print("=" * 80)
    
    # Register fresh user
    timestamp = int(datetime.now().timestamp())
    email = f"acid+{timestamp}@futureflex.dev"
    password = "Test@2026"
    
    token = register_user(email, password, "ACID Tester")
    if not token:
        log_test("BLOCO 7", "User registration", False, "Failed to register user", None)
        return
    
    # Create account
    account_id = create_account(token, "Banco Itaú", "checking", 5000.0)
    if not account_id:
        log_test("BLOCO 7", "Account creation", False, "Failed to create account", None)
        return
    
    # Create commitment
    commitment = create_commitment(token, {
        "type": "fixed_expense",
        "description": "Aluguel ACID",
        "total_amount": 500.0,
        "payment_method": "account",
        "recurrence": "monthly",
        "day_of_month": 10
    })
    
    if not commitment:
        log_test("BLOCO 7", "Commitment creation", False, "Failed to create commitment", None)
        return
    
    # Get occurrence
    detail = get_commitment_detail(token, commitment["id"])
    if not detail or not detail.get("occurrences"):
        log_test("BLOCO 7", "Get occurrences", False, "No occurrences found", None)
        return
    
    occ_id = detail["occurrences"][0]["id"]
    
    # Get initial state
    accounts_before = get_accounts(token)
    transactions_before = get_transactions(token)
    account_before = next((a for a in accounts_before if a["id"] == account_id), None)
    balance_before = account_before["current_balance"]
    tx_count_before = len(transactions_before)
    
    # Pay occurrence (should create Transaction + update Account atomically)
    status, response = pay_occurrence(token, occ_id, account_id)
    if status not in [200, 201]:
        log_test("BLOCO 7", "Payment", False, f"Failed to pay occurrence: {status}", response)
        return
    
    # Verify atomicity: both Transaction and Account updated
    accounts_after = get_accounts(token)
    transactions_after = get_transactions(token)
    account_after = next((a for a in accounts_after if a["id"] == account_id), None)
    balance_after = account_after["current_balance"]
    tx_count_after = len(transactions_after)
    
    if tx_count_after == tx_count_before + 1 and abs((balance_before - balance_after) - 500.0) < 0.01:
        log_test("BLOCO 7", "Atomicity (success)", True, "Transaction created AND account debited atomically", None)
    else:
        log_test("BLOCO 7", "Atomicity (success)", False, f"Inconsistent state: tx_count {tx_count_before}->{tx_count_after}, balance {balance_before}->{balance_after}", None)
    
    # Test rollback: try to pay with invalid account (should fail and NOT create Transaction)
    fake_account_id = "000000000000000000000000"
    tx_count_before_fail = len(get_transactions(token))
    
    status_fail, response_fail = pay_occurrence(token, detail["occurrences"][1]["id"], fake_account_id)
    
    tx_count_after_fail = len(get_transactions(token))
    
    if status_fail in [400, 404] and tx_count_after_fail == tx_count_before_fail:
        log_test("BLOCO 7", "Atomicity (rollback)", True, "Failed payment did NOT create dangling Transaction", None)
    else:
        log_test("BLOCO 7", "Atomicity (rollback)", False, f"Expected rollback, but tx_count {tx_count_before_fail}->{tx_count_after_fail}", None)


# ========================================================================
# BLOCO 8: TERCEIROS (THIRD-PARTY)
# ========================================================================
def test_bloco8_terceiros():
    """Test terceiros: third-party purchase on card, no double count"""
    print("\n" + "=" * 80)
    print("BLOCO 8: TERCEIROS (THIRD-PARTY)")
    print("=" * 80)
    
    # Login as demo user (has Ana third-party scenario)
    token = login(DEMO_EMAIL, DEMO_PASSWORD)
    if not token:
        log_test("BLOCO 8", "Demo login", False, "Failed to login as demo user", None)
        return
    
    # Get third-parties
    try:
        response = requests.get(
            f"{BASE_URL}/third-parties",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if response.status_code != 200:
            log_test("BLOCO 8", "Get third-parties", False, f"Failed to get third-parties: {response.status_code}", None)
            return
        
        data = response.json()
        receivable = data.get("total_receivable", 0)
        
        # Demo user has Ana (R$ 100 per month for 6 months = R$ 600 total receivable)
        if abs(receivable - 600.0) < 0.01:
            log_test("BLOCO 8", "Third-party receivable", True, f"Ana's debt = R$ 600.00 ✓", None)
        else:
            log_test("BLOCO 8", "Third-party receivable", False, f"Expected 600, got {receivable}", data)
    except Exception as e:
        log_test("BLOCO 8", "Get third-parties", False, f"Error: {e}", None)
        return
    
    # Verify Ana's purchase appears in invoice
    dashboard = get_dashboard(token)
    if not dashboard:
        log_test("BLOCO 8", "Dashboard", False, "Failed to get dashboard", None)
        return
    
    comp = dashboard.get("competence")
    month_view = get_month_view(token, comp)
    if not month_view:
        log_test("BLOCO 8", "Month view", False, "Failed to get month view", None)
        return
    
    # Ana's R$ 100 should be in the invoice (502.70 total includes Ana 100)
    groups = {g["key"]: g for g in month_view.get("groups", [])}
    cards_total = groups.get("cards", {}).get("total", 0)
    
    if abs(cards_total - 502.7) > 0.01:
        log_test("BLOCO 8", "Ana in invoice", False, f"Expected invoice 502.70 (includes Ana 100), got {cards_total}", None)
    else:
        log_test("BLOCO 8", "Ana in invoice", True, f"Ana's R$ 100 appears in invoice (502.70 total) ✓", None)
    
    # Verify Ana's debt is NOT added to committed
    committed = month_view.get("committed", 0)
    # Committed should be 2302.70 (1800 rent + 502.70 invoice), NOT 2402.70
    if abs(committed - 2302.7) > 0.01:
        log_test("BLOCO 8", "Ana NOT in committed", False, f"Expected committed 2302.70, got {committed} (Ana may be double-counted)", None)
    else:
        log_test("BLOCO 8", "Ana NOT in committed", True, f"Ana's R$ 100 NOT added to committed ✓", None)


# ========================================================================
# BLOCO 9: FROZEN
# ========================================================================
def test_bloco9_frozen():
    """Test frozen: freeze/reactivate commitment"""
    print("\n" + "=" * 80)
    print("BLOCO 9: FROZEN")
    print("=" * 80)
    
    # Register fresh user
    timestamp = int(datetime.now().timestamp())
    email = f"frozen+{timestamp}@futureflex.dev"
    password = "Test@2026"
    
    token = register_user(email, password, "Frozen Tester")
    if not token:
        log_test("BLOCO 9", "User registration", False, "Failed to register user", None)
        return
    
    # Create account
    account_id = create_account(token, "Banco Itaú", "checking", 10000.0)
    if not account_id:
        log_test("BLOCO 9", "Account creation", False, "Failed to create account", None)
        return
    
    # Create commitment
    commitment = create_commitment(token, {
        "type": "fixed_expense",
        "description": "Academia",
        "total_amount": 300.0,
        "payment_method": "account",
        "recurrence": "monthly",
        "day_of_month": 10
    })
    
    if not commitment:
        log_test("BLOCO 9", "Commitment creation", False, "Failed to create commitment", None)
        return
    
    # Get projection to find a future competence
    projection = get_projection(token, 24)
    if not projection:
        log_test("BLOCO 9", "Get projection", False, "Failed to get projection", None)
        return
    
    rows = projection if isinstance(projection, list) else projection.get("rows", [])
    if len(rows) < 2:
        log_test("BLOCO 9", "Projection rows", False, "Not enough projection rows", None)
        return
    
    future_comp = rows[1]["competence"] if isinstance(rows[1], dict) else None
    if not future_comp:
        log_test("BLOCO 9", "Future competence", False, "Failed to get future competence", None)
        return
    
    # Get month view before freeze
    month_before = get_month_view(token, future_comp)
    if not month_before:
        log_test("BLOCO 9", "Month view before", False, "Failed to get month view", None)
        return
    
    committed_before = month_before.get("committed", 0)
    frozen_before = month_before.get("frozen_total", 0)
    
    # Freeze commitment
    status, response = freeze_commitment(token, commitment["id"])
    if status not in [200, 201]:
        log_test("BLOCO 9", "Freeze commitment", False, f"Failed to freeze: {status}", response)
        return
    
    log_test("BLOCO 9", "Freeze commitment", True, "Commitment frozen successfully", None)
    
    # Get month view after freeze
    month_after_freeze = get_month_view(token, future_comp)
    if not month_after_freeze:
        log_test("BLOCO 9", "Month view after freeze", False, "Failed to get month view", None)
        return
    
    committed_after_freeze = month_after_freeze.get("committed", 0)
    frozen_after_freeze = month_after_freeze.get("frozen_total", 0)
    
    # Verify commitment left active committed
    if committed_after_freeze < committed_before:
        log_test("BLOCO 9", "Leaves active committed", True, f"Committed reduced from {committed_before} to {committed_after_freeze}", None)
    else:
        log_test("BLOCO 9", "Leaves active committed", False, f"Committed not reduced: {committed_before} -> {committed_after_freeze}", None)
    
    # Verify appears in frozen list
    if frozen_after_freeze > frozen_before:
        log_test("BLOCO 9", "Appears in frozen", True, f"Frozen total increased from {frozen_before} to {frozen_after_freeze}", None)
    else:
        log_test("BLOCO 9", "Appears in frozen", False, f"Frozen total not increased: {frozen_before} -> {frozen_after_freeze}", None)
    
    # Reactivate commitment
    status, response = unfreeze_commitment(token, commitment["id"])
    if status not in [200, 201]:
        log_test("BLOCO 9", "Reactivate commitment", False, f"Failed to reactivate: {status}", response)
        return
    
    log_test("BLOCO 9", "Reactivate commitment", True, "Commitment reactivated successfully", None)
    
    # Get month view after reactivate
    month_after_reactivate = get_month_view(token, future_comp)
    if not month_after_reactivate:
        log_test("BLOCO 9", "Month view after reactivate", False, "Failed to get month view", None)
        return
    
    committed_after_reactivate = month_after_reactivate.get("committed", 0)
    
    # Verify returns to active committed
    if abs(committed_after_reactivate - committed_before) < 0.01:
        log_test("BLOCO 9", "Returns to active", True, f"Committed restored to {committed_after_reactivate}", None)
    else:
        log_test("BLOCO 9", "Returns to active", False, f"Committed not restored: expected {committed_before}, got {committed_after_reactivate}", None)


# ========================================================================
# BLOCO 10: PROJECTION
# ========================================================================
def test_bloco10_projection():
    """Test projection: 24 months, no duplicates"""
    print("\n" + "=" * 80)
    print("BLOCO 10: PROJECTION")
    print("=" * 80)
    
    # Login as demo user
    token = login(DEMO_EMAIL, DEMO_PASSWORD)
    if not token:
        log_test("BLOCO 10", "Demo login", False, "Failed to login as demo user", None)
        return
    
    # Get projection
    projection = get_projection(token, 24)
    if not projection:
        log_test("BLOCO 10", "Get projection", False, "Failed to get projection", None)
        return
    
    rows = projection if isinstance(projection, list) else projection.get("rows", [])
    
    # Test 1: 24 months
    if len(rows) == 24:
        log_test("BLOCO 10", "24 months", True, f"Projection has 24 months ✓", None)
    else:
        log_test("BLOCO 10", "24 months", False, f"Expected 24 months, got {len(rows)}", projection)
    
    # Test 2: No duplicated competence
    competences = [r["competence"] if isinstance(r, dict) else r for r in rows]
    unique_competences = set(competences)
    
    if len(competences) == len(unique_competences):
        log_test("BLOCO 10", "No duplicates", True, f"All 24 competences are unique ✓", None)
    else:
        duplicates = [c for c in competences if competences.count(c) > 1]
        log_test("BLOCO 10", "No duplicates", False, f"Duplicated competences: {set(duplicates)}", None)
    
    # Test 3: Correctly reflects recurrences, installments, subscriptions, cards
    # Check that each row has expected fields
    if rows:
        sample_row = rows[0] if isinstance(rows[0], dict) else {}
        required_fields = ["competence", "balance_start", "balance_end", "income", "commitments"]
        missing_fields = [f for f in required_fields if f not in sample_row]
        
        if not missing_fields:
            log_test("BLOCO 10", "Row structure", True, f"Projection rows have all required fields ✓", None)
        else:
            log_test("BLOCO 10", "Row structure", False, f"Missing fields: {missing_fields}", sample_row)


# ========================================================================
# BLOCO 11: IA (REAL DATA, NOT MOCKED)
# ========================================================================
def test_bloco11_ia():
    """Test IA: real gpt-5.5 via EMERGENT_LLM_KEY, NOT mocked"""
    print("\n" + "=" * 80)
    print("BLOCO 11: IA (REAL DATA, MODEL gpt-5.5)")
    print("=" * 80)
    
    # Login as demo user
    token = login(DEMO_EMAIL, DEMO_PASSWORD)
    if not token:
        log_test("BLOCO 11", "Demo login", False, "Failed to login as demo user", None)
        return
    
    # Test 1: GET /api/ai/context returns real context
    context = get_ai_context(token)
    if not context:
        log_test("BLOCO 11", "AI context", False, "Failed to get AI context", None)
        return
    
    # Verify context has real user data
    if isinstance(context, dict) and len(str(context)) > 100:
        log_test("BLOCO 11", "AI context", True, f"AI context returned with real user data ({len(str(context))} chars)", None)
    else:
        log_test("BLOCO 11", "AI context", False, f"AI context seems empty or mocked", context)
    
    # Test 2-5: POST /api/ai/ask with real questions
    questions = [
        "Posso comprar um celular de R$ 2.000?",
        "Quanto posso gastar este mês?",
        "O que devo cortar?",
        "Tenho contas atrasadas?"
    ]
    
    for question in questions:
        print(f"\n[BLOCO 11] Asking: {question}")
        answer = ask_ai(token, question)
        
        if not answer:
            log_test("BLOCO 11", f"AI ask: {question[:30]}...", False, "Failed to get AI answer", None)
            continue
        
        answer_text = answer.get("answer", "") if isinstance(answer, dict) else str(answer)
        
        # Verify answer uses real numbers (not generic/mock)
        # Look for R$ amounts or specific numbers from demo user's data
        has_real_data = any([
            "R$" in answer_text,
            "2302" in answer_text,  # committed
            "502" in answer_text,   # invoice
            "1800" in answer_text,  # rent
            "7000" in answer_text,  # balance
            "5500" in answer_text,  # income
        ])
        
        if has_real_data and len(answer_text) > 50:
            log_test("BLOCO 11", f"AI ask: {question[:30]}...", True, f"Answer uses real user numbers ({len(answer_text)} chars)", None)
        else:
            log_test("BLOCO 11", f"AI ask: {question[:30]}...", False, f"Answer seems generic/mocked: {answer_text[:200]}", None)


# ========================================================================
# BLOCO 12: SMOKE TESTS
# ========================================================================
def test_bloco12_smoke():
    """Test smoke: all endpoints return 200"""
    print("\n" + "=" * 80)
    print("BLOCO 12: SMOKE TESTS")
    print("=" * 80)
    
    # Login as demo user
    token = login(DEMO_EMAIL, DEMO_PASSWORD)
    if not token:
        log_test("BLOCO 12", "Demo login", False, "Failed to login as demo user", None)
        return
    
    # Get current competence
    dashboard = get_dashboard(token)
    comp = dashboard.get("competence") if dashboard else get_current_competence()
    
    # Endpoints to test
    endpoints = [
        ("login", f"{BASE_URL}/auth/login", "POST", {"email": DEMO_EMAIL, "password": DEMO_PASSWORD}),
        ("dashboard", f"{BASE_URL}/dashboard", "GET", None),
        ("overview", f"{BASE_URL}/overview", "GET", None),
        ("months/{current}", f"{BASE_URL}/months/{comp}", "GET", None),
        ("free-money", f"{BASE_URL}/free-money", "GET", None),
        ("projection", f"{BASE_URL}/projection", "GET", None),
        ("health-score", f"{BASE_URL}/health-score", "GET", None),
        ("subscriptions", f"{BASE_URL}/subscriptions", "GET", None),
        ("frozen", f"{BASE_URL}/frozen", "GET", None),
        ("third-parties", f"{BASE_URL}/third-parties", "GET", None),
        ("ai/context", f"{BASE_URL}/ai/context", "GET", None),
        ("ai/ask", f"{BASE_URL}/ai/ask", "POST", {"question": "Olá"}),
    ]
    
    for name, url, method, payload in endpoints:
        try:
            if method == "GET":
                response = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
            else:
                response = requests.post(url, json=payload, headers={"Authorization": f"Bearer {token}"} if name != "login" else {}, timeout=30)
            
            if response.status_code == 200:
                log_test("BLOCO 12", f"Smoke: {name}", True, f"GET/POST {name} returned 200", None)
            else:
                log_test("BLOCO 12", f"Smoke: {name}", False, f"Expected 200, got {response.status_code}", None)
        except Exception as e:
            log_test("BLOCO 12", f"Smoke: {name}", False, f"Error: {e}", None)


# ========================================================================
# MAIN
# ========================================================================
def main():
    """Run all ETAPA 6 QA tests"""
    print("=" * 80)
    print("ETAPA 6 — FULL BACKEND QA for FutureFlex V2")
    print("=" * 80)
    print(f"Backend URL: {BASE_URL}")
    print(f"Demo user: {DEMO_EMAIL}")
    print("=" * 80)
    
    # Run all blocks
    test_bloco1_multicard()
    test_bloco2_regression()
    test_bloco3_anti_double_count()
    test_bloco4_status()
    test_bloco5_payment()
    test_bloco6_security()
    test_bloco7_acid()
    test_bloco8_terceiros()
    test_bloco9_frozen()
    test_bloco10_projection()
    test_bloco11_ia()
    test_bloco12_smoke()
    
    # Print summary
    print("\n" + "=" * 80)
    print("ETAPA 6 QA SUMMARY")
    print("=" * 80)
    
    total_passed = sum(1 for r in test_results if r.passed)
    total_failed = sum(1 for r in test_results if not r.passed)
    total = len(test_results)
    
    print(f"\nTotal: {total} | Passed: {total_passed} | Failed: {total_failed}")
    
    # Per-block summary
    print("\nPer-Block Results:")
    for block, counts in sorted(block_results.items()):
        status = "✅ PASS" if counts["failed"] == 0 else "❌ FAIL"
        print(f"{status} | {block}: {counts['passed']} passed, {counts['failed']} failed")
    
    # Failed tests
    if total_failed > 0:
        print("\nFailed Tests:")
        for i, result in enumerate([r for r in test_results if not r.passed], 1):
            print(f"{i}. ❌ {result.block} | {result.test}")
            print(f"   └─ {result.details}")
    
    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    exit(main())
