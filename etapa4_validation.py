#!/usr/bin/env python3
"""
ETAPA 4 Backend Validation: Focused tests for financial lifecycle
"""
import requests
import json
from datetime import datetime

BASE_URL = "https://flex-qa-stage6.preview.emergentagent.com/api"
DEMO_EMAIL = "demo@futureflex.dev"
DEMO_PASSWORD = "Demo@2026"

test_results = []


def log_test(scenario: str, passed: bool, details: str):
    test_results.append((scenario, passed, details))
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"\n{status} | Scenario {scenario}")
    print(f"Details: {details}")


def api_call(method, endpoint, token=None, json_data=None, params=None):
    """Helper for API calls"""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if method == "POST" and "pay" in endpoint:
        headers["Idempotency-Key"] = f"test-{datetime.now().timestamp()}"
    
    url = f"{BASE_URL}{endpoint}"
    try:
        if method == "GET":
            r = requests.get(url, headers=headers, params=params, timeout=10)
        elif method == "POST":
            r = requests.post(url, headers=headers, json=json_data, timeout=10)
        elif method == "PATCH":
            r = requests.patch(url, headers=headers, json=json_data, timeout=10)
        else:
            return None, None
        
        data = r.json() if r.status_code in [200, 400, 404, 409, 422] else None
        return r.status_code, data
    except Exception as e:
        print(f"API error: {e}")
        return 0, None


def run_validation():
    print("=" * 80)
    print("ETAPA 4 Backend Validation")
    print("=" * 80)
    
    # Login
    print("\n[SETUP] Logging in...")
    status, data = api_call("POST", "/auth/login", json_data={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    if status != 200:
        print("❌ Login failed")
        return
    token = data["access_token"]
    print("✅ Logged in")
    
    # Get accounts
    status, accounts = api_call("GET", "/accounts", token=token)
    if not accounts:
        print("❌ No accounts found")
        return
    account_id = accounts[0]["id"]
    print(f"✅ Using account: {account_id}")
    
    # Get current date info
    today = datetime.now()
    current_comp = today.strftime("%Y-%m")
    future_comp = f"{today.year}-{today.month + 1:02d}" if today.month < 12 else f"{today.year + 1}-01"
    overdue_day = 1  # Day that has passed (today is 13)
    
    print(f"\n[INFO] Today: {today.strftime('%Y-%m-%d')}, Current: {current_comp}, Future: {future_comp}")
    
    # ========================================================================
    # Test 1: Future occurrence => status future/due
    # ========================================================================
    print("\n" + "=" * 80)
    print("Test 1: Future occurrence => status future/due")
    
    status, c1 = api_call("POST", "/commitments", token=token, json_data={
        "type": "fixed_expense",
        "description": "Test Future Status",
        "total_amount": 100,
        "payment_method": "account",
        "day_of_month": 15
    })
    
    if c1:
        status, detail = api_call("GET", f"/commitments/{c1['id']}", token=token)
        if detail:
            future_occ = next((o for o in detail["occurrences"] if o["competence"] == future_comp), None)
            if future_occ and future_occ["status"] in ["future", "due"]:
                log_test("1", True, f"Future occurrence has status '{future_occ['status']}'")
            else:
                log_test("1", False, f"Status: {future_occ['status'] if future_occ else 'N/A'}")
        else:
            log_test("1", False, "Failed to get commitment detail")
    else:
        log_test("1", False, "Failed to create commitment")
    
    # ========================================================================
    # Test 2: Overdue occurrence => status overdue
    # ========================================================================
    print("\n" + "=" * 80)
    print("Test 2: Overdue occurrence => status overdue")
    
    status, c2 = api_call("POST", "/commitments", token=token, json_data={
        "type": "fixed_expense",
        "description": "Test Overdue Status",
        "total_amount": 200,
        "payment_method": "account",
        "day_of_month": overdue_day
    })
    
    if c2:
        status, detail = api_call("GET", f"/commitments/{c2['id']}", token=token)
        if detail:
            current_occ = next((o for o in detail["occurrences"] if o["competence"] == current_comp), None)
            if current_occ and current_occ["status"] == "overdue":
                log_test("2", True, f"Current month occurrence (day {overdue_day}) has status 'overdue'")
            else:
                log_test("2", False, f"Status: {current_occ['status'] if current_occ else 'N/A'}, competence: {current_occ['competence'] if current_occ else 'N/A'}")
        else:
            log_test("2", False, "Failed to get commitment detail")
    else:
        log_test("2", False, "Failed to create commitment")
    
    # ========================================================================
    # Test 3: Paid occurrence => status paid
    # ========================================================================
    print("\n" + "=" * 80)
    print("Test 3: Paid occurrence => status paid")
    
    status, c3 = api_call("POST", "/commitments", token=token, json_data={
        "type": "fixed_expense",
        "description": "Test Paid Status",
        "total_amount": 300,
        "payment_method": "account",
        "day_of_month": 20
    })
    
    if c3:
        status, detail = api_call("GET", f"/commitments/{c3['id']}", token=token)
        if detail:
            occ = detail["occurrences"][0]
            # Pay it
            status, pay_resp = api_call("POST", f"/occurrences/{occ['id']}/pay", token=token, 
                                       json_data={"account_id": account_id})
            if status == 200:
                # Re-fetch
                status, detail2 = api_call("GET", f"/commitments/{c3['id']}", token=token)
                if detail2:
                    paid_occ = next((o for o in detail2["occurrences"] if o["id"] == occ["id"]), None)
                    if paid_occ and paid_occ["status"] == "paid":
                        log_test("3", True, "Paid occurrence has status 'paid'")
                    else:
                        log_test("3", False, f"Status: {paid_occ['status'] if paid_occ else 'N/A'}")
                else:
                    log_test("3", False, "Failed to re-fetch")
            else:
                log_test("3", False, f"Payment failed: {status}")
        else:
            log_test("3", False, "Failed to get commitment detail")
    else:
        log_test("3", False, "Failed to create commitment")
    
    # ========================================================================
    # Test 4: Overdue can be paid => becomes paid + Transaction created
    # ========================================================================
    print("\n" + "=" * 80)
    print("Test 4: Overdue can be paid => becomes paid + Transaction created")
    
    if c2:
        status, detail = api_call("GET", f"/commitments/{c2['id']}", token=token)
        if detail:
            overdue_occ = next((o for o in detail["occurrences"] if o["status"] == "overdue"), None)
            if overdue_occ:
                tx_count_before = len(overdue_occ.get("refs", {}).get("transaction_ids", []))
                
                # Pay it
                status, pay_resp = api_call("POST", f"/occurrences/{overdue_occ['id']}/pay", token=token,
                                           json_data={"account_id": account_id})
                if status == 200:
                    # Re-fetch
                    status, detail2 = api_call("GET", f"/commitments/{c2['id']}", token=token)
                    if detail2:
                        paid_occ = next((o for o in detail2["occurrences"] if o["id"] == overdue_occ["id"]), None)
                        tx_count_after = len(paid_occ.get("refs", {}).get("transaction_ids", []))
                        
                        if paid_occ["status"] == "paid" and tx_count_after == tx_count_before + 1:
                            log_test("4", True, f"Overdue paid: status='paid', Transaction created ({tx_count_before} -> {tx_count_after})")
                        else:
                            log_test("4", False, f"Status: {paid_occ['status']}, Tx: {tx_count_before} -> {tx_count_after}")
                    else:
                        log_test("4", False, "Failed to re-fetch")
                else:
                    log_test("4", False, f"Payment failed: {status}")
            else:
                log_test("4", False, "No overdue occurrence found")
        else:
            log_test("4", False, "Failed to get commitment detail")
    else:
        log_test("4", False, "No commitment available")
    
    # ========================================================================
    # Test 5: Payment uses chosen account and debits it
    # ========================================================================
    print("\n" + "=" * 80)
    print("Test 5: Payment uses chosen account and debits it")
    
    # Create second account
    status, acc2 = api_call("POST", "/accounts", token=token, json_data={
        "name": "Test Account 2",
        "type": "checking",
        "opening_balance": 5000
    })
    
    if acc2:
        acc2_id = acc2["id"]
        
        # Get balance before
        status, accounts = api_call("GET", "/accounts", token=token)
        acc2_before = next((a for a in accounts if a["id"] == acc2_id), None)
        balance_before = acc2_before["current_balance"] if acc2_before else 0
        
        # Create commitment and pay with acc2
        status, c5 = api_call("POST", "/commitments", token=token, json_data={
            "type": "fixed_expense",
            "description": "Test Account Choice",
            "total_amount": 400,
            "payment_method": "account",
            "day_of_month": 25
        })
        
        if c5:
            status, detail = api_call("GET", f"/commitments/{c5['id']}", token=token)
            if detail:
                occ = detail["occurrences"][0]
                amount = occ["amount"]
                
                # Pay with acc2
                status, pay_resp = api_call("POST", f"/occurrences/{occ['id']}/pay", token=token,
                                           json_data={"account_id": acc2_id})
                if status == 200:
                    # Get balance after
                    status, accounts = api_call("GET", "/accounts", token=token)
                    acc2_after = next((a for a in accounts if a["id"] == acc2_id), None)
                    balance_after = acc2_after["current_balance"] if acc2_after else 0
                    expected = balance_before - amount
                    
                    if abs(balance_after - expected) < 0.01:
                        log_test("5", True, f"Account2 debited: {balance_before} -> {balance_after} (expected {expected})")
                    else:
                        log_test("5", False, f"Balance: {balance_before} -> {balance_after} (expected {expected})")
                else:
                    log_test("5", False, f"Payment failed: {status}")
            else:
                log_test("5", False, "Failed to get commitment detail")
        else:
            log_test("5", False, "Failed to create commitment")
    else:
        log_test("5", False, "Failed to create second account")
    
    # ========================================================================
    # Test 6: Double payment returns 409
    # ========================================================================
    print("\n" + "=" * 80)
    print("Test 6: Double payment returns 409")
    
    status, c6 = api_call("POST", "/commitments", token=token, json_data={
        "type": "fixed_expense",
        "description": "Test Double Payment",
        "total_amount": 500,
        "payment_method": "account",
        "day_of_month": 28
    })
    
    if c6:
        status, detail = api_call("GET", f"/commitments/{c6['id']}", token=token)
        if detail:
            occ = detail["occurrences"][0]
            
            # Pay once
            status1, _ = api_call("POST", f"/occurrences/{occ['id']}/pay", token=token,
                                 json_data={"account_id": account_id})
            if status1 == 200:
                # Try again
                status2, _ = api_call("POST", f"/occurrences/{occ['id']}/pay", token=token,
                                     json_data={"account_id": account_id})
                if status2 == 409:
                    log_test("6", True, "Second payment correctly rejected with 409")
                else:
                    log_test("6", False, f"Expected 409, got {status2}")
            else:
                log_test("6", False, f"First payment failed: {status1}")
        else:
            log_test("6", False, "Failed to get commitment detail")
    else:
        log_test("6", False, "Failed to create commitment")
    
    # ========================================================================
    # Test 7: Second payment creates NO second Transaction
    # ========================================================================
    print("\n" + "=" * 80)
    print("Test 7: Second payment creates NO second Transaction")
    
    status, c7 = api_call("POST", "/commitments", token=token, json_data={
        "type": "fixed_expense",
        "description": "Test No Duplicate Tx",
        "total_amount": 600,
        "payment_method": "account",
        "day_of_month": 29
    })
    
    if c7:
        status, detail = api_call("GET", f"/commitments/{c7['id']}", token=token)
        if detail:
            occ = detail["occurrences"][0]
            
            # Pay once
            status1, _ = api_call("POST", f"/occurrences/{occ['id']}/pay", token=token,
                                 json_data={"account_id": account_id})
            if status1 == 200:
                # Check tx count
                status, detail2 = api_call("GET", f"/commitments/{c7['id']}", token=token)
                if detail2:
                    occ2 = next((o for o in detail2["occurrences"] if o["id"] == occ["id"]), None)
                    tx_count1 = len(occ2.get("refs", {}).get("transaction_ids", []))
                    
                    # Try again (should fail)
                    status2, _ = api_call("POST", f"/occurrences/{occ['id']}/pay", token=token,
                                         json_data={"account_id": account_id})
                    
                    # Check tx count again
                    status, detail3 = api_call("GET", f"/commitments/{c7['id']}", token=token)
                    if detail3:
                        occ3 = next((o for o in detail3["occurrences"] if o["id"] == occ["id"]), None)
                        tx_count2 = len(occ3.get("refs", {}).get("transaction_ids", []))
                        
                        if tx_count1 == 1 and tx_count2 == 1:
                            log_test("7", True, f"Transaction count stayed at 1")
                        else:
                            log_test("7", False, f"Tx count: {tx_count1} -> {tx_count2}")
                    else:
                        log_test("7", False, "Failed to re-fetch 2")
                else:
                    log_test("7", False, "Failed to re-fetch 1")
            else:
                log_test("7", False, f"First payment failed: {status1}")
        else:
            log_test("7", False, "Failed to get commitment detail")
    else:
        log_test("7", False, "Failed to create commitment")
    
    # ========================================================================
    # Test 8: Unpaid occurrence has 0 transactions
    # ========================================================================
    print("\n" + "=" * 80)
    print("Test 8: Unpaid occurrence has 0 transactions")
    
    status, c8 = api_call("POST", "/commitments", token=token, json_data={
        "type": "fixed_expense",
        "description": "Test Unpaid No Tx",
        "total_amount": 700,
        "payment_method": "account",
        "day_of_month": 5
    })
    
    if c8:
        status, detail = api_call("GET", f"/commitments/{c8['id']}", token=token)
        if detail:
            unpaid_occ = next((o for o in detail["occurrences"] 
                              if o["paid_amount"] == 0 and o["status"] in ["overdue", "due", "future"]), None)
            if unpaid_occ:
                tx_count = len(unpaid_occ.get("refs", {}).get("transaction_ids", []))
                if tx_count == 0:
                    log_test("8", True, f"Unpaid occurrence has 0 transactions, status='{unpaid_occ['status']}'")
                else:
                    log_test("8", False, f"Unpaid occurrence has {tx_count} transactions")
            else:
                log_test("8", False, "No unpaid occurrence found")
        else:
            log_test("8", False, "Failed to get commitment detail")
    else:
        log_test("8", False, "Failed to create commitment")
    
    # ========================================================================
    # Test 9: Paid overdue keeps original competence
    # ========================================================================
    print("\n" + "=" * 80)
    print("Test 9: Paid overdue keeps original competence")
    
    status, c9 = api_call("POST", "/commitments", token=token, json_data={
        "type": "fixed_expense",
        "description": "Test Competence Preserved",
        "total_amount": 800,
        "payment_method": "account",
        "day_of_month": 2
    })
    
    if c9:
        status, detail = api_call("GET", f"/commitments/{c9['id']}", token=token)
        if detail:
            overdue_occ = next((o for o in detail["occurrences"] if o["status"] == "overdue"), None)
            if overdue_occ:
                original_comp = overdue_occ["competence"]
                
                # Pay it
                status, _ = api_call("POST", f"/occurrences/{overdue_occ['id']}/pay", token=token,
                                    json_data={"account_id": account_id})
                if status == 200:
                    # Re-fetch
                    status, detail2 = api_call("GET", f"/commitments/{c9['id']}", token=token)
                    if detail2:
                        paid_occ = next((o for o in detail2["occurrences"] if o["id"] == overdue_occ["id"]), None)
                        if paid_occ["competence"] == original_comp:
                            log_test("9", True, f"Competence preserved: '{original_comp}'")
                        else:
                            log_test("9", False, f"Competence changed: {original_comp} -> {paid_occ['competence']}")
                    else:
                        log_test("9", False, "Failed to re-fetch")
                else:
                    log_test("9", False, f"Payment failed: {status}")
            else:
                log_test("9", False, "No overdue occurrence found")
        else:
            log_test("9", False, "Failed to get commitment detail")
    else:
        log_test("9", False, "Failed to create commitment")
    
    # ========================================================================
    # Test 10: Materialize does NOT duplicate
    # ========================================================================
    print("\n" + "=" * 80)
    print("Test 10: Materialize does NOT duplicate")
    
    if c9:
        status, detail = api_call("GET", f"/commitments/{c9['id']}", token=token)
        if detail:
            count_before = len([o for o in detail["occurrences"] if o["competence"] == current_comp])
            
            # Materialize
            status, _ = api_call("POST", "/commitments/materialize", token=token)
            if status == 200:
                # Re-fetch
                status, detail2 = api_call("GET", f"/commitments/{c9['id']}", token=token)
                if detail2:
                    count_after = len([o for o in detail2["occurrences"] if o["competence"] == current_comp])
                    if count_after == count_before:
                        log_test("10", True, f"Count stayed at {count_before}")
                    else:
                        log_test("10", False, f"Count changed: {count_before} -> {count_after}")
                else:
                    log_test("10", False, "Failed to re-fetch")
            else:
                log_test("10", False, f"Materialize failed: {status}")
        else:
            log_test("10", False, "Failed to get commitment detail")
    else:
        log_test("10", False, "No commitment available")
    
    # ========================================================================
    # Test 11: Distinct competences for recurring commitment
    # ========================================================================
    print("\n" + "=" * 80)
    print("Test 11: Distinct competences for recurring commitment")
    
    if c9:
        status, detail = api_call("GET", f"/commitments/{c9['id']}", token=token)
        if detail:
            current_occ = next((o for o in detail["occurrences"] if o["competence"] == current_comp), None)
            future_occ = next((o for o in detail["occurrences"] if o["competence"] == future_comp), None)
            
            if current_occ and future_occ:
                if current_occ["competence"] != future_occ["competence"]:
                    log_test("11", True, f"Distinct: {current_occ['competence']} and {future_occ['competence']}")
                else:
                    log_test("11", False, "Competences not distinct")
            else:
                log_test("11", False, f"Missing: current={bool(current_occ)}, future={bool(future_occ)}")
        else:
            log_test("11", False, "Failed to get commitment detail")
    else:
        log_test("11", False, "No commitment available")
    
    # ========================================================================
    # Test 12: Credit card purchase does NOT debit account
    # ========================================================================
    print("\n" + "=" * 80)
    print("Test 12: Credit card purchase does NOT debit account")
    
    # Create card
    status, card = api_call("POST", "/credit-cards", token=token, json_data={
        "name": "Test Card",
        "limit": 10000,
        "closing_day": 28,
        "due_day": 5
    })
    
    if card:
        # Get balance before
        status, accounts = api_call("GET", "/accounts", token=token)
        acc_before = next((a for a in accounts if a["id"] == account_id), None)
        balance_before = acc_before["current_balance"] if acc_before else 0
        
        # Create purchase
        status, c12 = api_call("POST", "/commitments", token=token, json_data={
            "type": "purchase_installment",
            "description": "Test Purchase",
            "total_amount": 1200,
            "installments_total": 12,
            "payment_method": "credit_card",
            "credit_card_id": card["id"]
        })
        
        if c12:
            # Get balance after
            status, accounts = api_call("GET", "/accounts", token=token)
            acc_after = next((a for a in accounts if a["id"] == account_id), None)
            balance_after = acc_after["current_balance"] if acc_after else 0
            
            if abs(balance_after - balance_before) < 0.01:
                # Try to pay occurrence directly
                status, detail = api_call("GET", f"/commitments/{c12['id']}", token=token)
                if detail and detail["occurrences"]:
                    occ = detail["occurrences"][0]
                    status, _ = api_call("POST", f"/occurrences/{occ['id']}/pay", token=token,
                                        json_data={"account_id": account_id})
                    if status == 400:
                        log_test("12", True, "Purchase did NOT debit account, direct payment rejected (400)")
                    else:
                        log_test("12", False, f"Direct payment should return 400, got {status}")
                else:
                    log_test("12", False, "Failed to get commitment detail")
            else:
                log_test("12", False, f"Balance changed: {balance_before} -> {balance_after}")
        else:
            log_test("12", False, "Failed to create purchase")
    else:
        log_test("12", False, "Failed to create card")
    
    # ========================================================================
    # Test 13: Paying invoice debits account
    # ========================================================================
    print("\n" + "=" * 80)
    print("Test 13: Paying invoice debits account")
    
    if card:
        # Materialize to create invoices
        api_call("POST", "/commitments/materialize", token=token)
        
        # Get invoices
        status, invoices = api_call("GET", "/invoices", token=token, params={"credit_card_id": card["id"]})
        if invoices:
            unpaid = next((inv for inv in invoices if inv["status"] != "paid"), None)
            if unpaid:
                # Get balance before
                status, accounts = api_call("GET", "/accounts", token=token)
                acc_before = next((a for a in accounts if a["id"] == account_id), None)
                balance_before = acc_before["current_balance"] if acc_before else 0
                
                invoice_amount = unpaid["total"]
                
                # Pay invoice
                status, _ = api_call("POST", f"/invoices/{unpaid['id']}/pay", token=token,
                                    json_data={"account_id": account_id})
                if status == 200:
                    # Get balance after
                    status, accounts = api_call("GET", "/accounts", token=token)
                    acc_after = next((a for a in accounts if a["id"] == account_id), None)
                    balance_after = acc_after["current_balance"] if acc_after else 0
                    expected = balance_before - invoice_amount
                    
                    if abs(balance_after - expected) < 0.01:
                        log_test("13", True, f"Invoice payment debited: {balance_before} -> {balance_after}")
                    else:
                        log_test("13", False, f"Balance: {balance_before} -> {balance_after} (expected {expected})")
                else:
                    log_test("13", False, f"Payment failed: {status}")
            else:
                log_test("13", False, "No unpaid invoice found")
        else:
            log_test("13", False, "Failed to get invoices")
    else:
        log_test("13", False, "No card available")
    
    # ========================================================================
    # Test 14: Month view NO double counting
    # ========================================================================
    print("\n" + "=" * 80)
    print("Test 14: Month view NO double counting")
    
    status, month = api_call("GET", f"/months/{current_comp}", token=token)
    if month:
        committed = month["committed"]
        paid = month["paid"]
        pending = month["pending"]
        
        expected = paid + pending
        if abs(committed - expected) < 1:
            log_test("14", True, f"committed={committed} ≈ paid+pending={expected}")
        else:
            log_test("14", False, f"committed={committed} ≠ paid+pending={expected}")
    else:
        log_test("14", False, "Failed to get month view")
    
    # ========================================================================
    # Test 15: Projection consistent
    # ========================================================================
    print("\n" + "=" * 80)
    print("Test 15: Projection consistent")
    
    status, proj = api_call("GET", "/projection", token=token, params={"months": 24})
    if proj:
        rows = proj["rows"]
        competences = [r["competence"] for r in rows]
        unique = set(competences)
        
        if len(competences) == len(unique):
            log_test("15", True, f"{len(rows)} unique competences")
        else:
            log_test("15", False, f"Duplicates found")
    else:
        log_test("15", False, "Failed to get projection")
    
    # ========================================================================
    # Test 16: Free money consistent
    # ========================================================================
    print("\n" + "=" * 80)
    print("Test 16: Free money consistent")
    
    status, free = api_call("GET", "/free-money", token=token)
    if free:
        free_now = free["free_now"]
        
        # Get total balance
        status, accounts = api_call("GET", "/accounts", token=token)
        total_balance = sum(a["current_balance"] for a in accounts)
        
        # Get pending
        status, month = api_call("GET", f"/months/{current_comp}", token=token)
        pending = month["pending"] if month else 0
        
        expected = total_balance - pending
        if abs(free_now - expected) < 100:
            log_test("16", True, f"free_now={free_now} ≈ balance-pending={expected}")
        else:
            log_test("16", False, f"free_now={free_now} ≠ expected={expected}")
    else:
        log_test("16", False, "Failed to get free money")
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, p, _ in test_results if p)
    total = len(test_results)
    
    print(f"\nETAPA 4: {passed}/{total} passed")
    for scenario, passed, details in test_results:
        status = "✅" if passed else "❌"
        print(f"{status} Scenario {scenario}: {details}")
    
    return test_results


if __name__ == "__main__":
    results = run_validation()
    failed = sum(1 for _, p, _ in results if not p)
    exit(0 if failed == 0 else 1)
