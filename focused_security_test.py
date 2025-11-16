#!/usr/bin/env python3
"""
Focused Security Testing for NourishStrong - Testing the 4 new security features
"""

import requests
import json
import time
from datetime import datetime
import sys

# Configuration
BASE_URL = "https://weight-wellness-4.preview.emergentagent.com/api"
TIMEOUT = 15

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def log_test(test_name, status, message=""):
    color = Colors.GREEN if status == "PASS" else Colors.RED if status == "FAIL" else Colors.YELLOW
    print(f"{color}[{status}]{Colors.ENDC} {test_name}")
    if message:
        print(f"    {message}")

def test_password_strength():
    """Test password strength validation"""
    print(f"\n{Colors.BLUE}=== Testing Password Strength Validation ==={Colors.ENDC}")
    
    results = {"passed": 0, "failed": 0, "total": 0}
    
    # Test 1: Weak password (too short)
    try:
        response = requests.post(f"{BASE_URL}/auth/register", 
                               json={
                                   "email": f"weak1.{int(time.time())}@test.com",
                                   "password": "123",
                                   "name": "Test User",
                                   "role": "user"
                               }, timeout=TIMEOUT)
        
        if response.status_code == 400:
            error_msg = response.json().get("detail", "")
            if "8 characters" in error_msg.lower():
                log_test("Weak Password Rejection (Short)", "PASS", f"Correctly rejected: {error_msg}")
                results["passed"] += 1
            else:
                log_test("Weak Password Rejection (Short)", "FAIL", f"Wrong error: {error_msg}")
                results["failed"] += 1
        else:
            log_test("Weak Password Rejection (Short)", "FAIL", f"Expected 400, got {response.status_code}")
            results["failed"] += 1
    except Exception as e:
        log_test("Weak Password Rejection (Short)", "FAIL", f"Request failed: {str(e)}")
        results["failed"] += 1
    
    results["total"] += 1
    
    # Test 2: Weak password (only lowercase)
    try:
        response = requests.post(f"{BASE_URL}/auth/register", 
                               json={
                                   "email": f"weak2.{int(time.time())}@test.com",
                                   "password": "onlylowercase",
                                   "name": "Test User 2",
                                   "role": "user"
                               }, timeout=TIMEOUT)
        
        if response.status_code == 400:
            error_msg = response.json().get("detail", "")
            if "3 of" in error_msg.lower() or "uppercase" in error_msg.lower():
                log_test("Weak Password Rejection (Simple)", "PASS", f"Correctly rejected: {error_msg}")
                results["passed"] += 1
            else:
                log_test("Weak Password Rejection (Simple)", "FAIL", f"Wrong error: {error_msg}")
                results["failed"] += 1
        else:
            log_test("Weak Password Rejection (Simple)", "FAIL", f"Expected 400, got {response.status_code}")
            results["failed"] += 1
    except Exception as e:
        log_test("Weak Password Rejection (Simple)", "FAIL", f"Request failed: {str(e)}")
        results["failed"] += 1
    
    results["total"] += 1
    
    # Test 3: Strong password (should succeed)
    test_email = f"strong.{int(time.time())}@test.com"
    try:
        response = requests.post(f"{BASE_URL}/auth/register", 
                               json={
                                   "email": test_email,
                                   "password": "StrongPass123!",
                                   "name": "Strong User",
                                   "role": "user"
                               }, timeout=TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            if "token" in data and "user" in data:
                log_test("Strong Password Acceptance", "PASS", "User registered with strong password")
                results["passed"] += 1
            else:
                log_test("Strong Password Acceptance", "FAIL", f"Missing data: {data}")
                results["failed"] += 1
        else:
            log_test("Strong Password Acceptance", "FAIL", f"Status: {response.status_code}, Response: {response.text}")
            results["failed"] += 1
    except Exception as e:
        log_test("Strong Password Acceptance", "FAIL", f"Request failed: {str(e)}")
        results["failed"] += 1
    
    results["total"] += 1
    
    return results, test_email

def test_password_validation_api():
    """Test password validation endpoint"""
    print(f"\n{Colors.BLUE}=== Testing Password Validation API ==={Colors.ENDC}")
    
    results = {"passed": 0, "failed": 0, "total": 0}
    
    # Test weak password
    try:
        response = requests.get(f"{BASE_URL}/auth/validate-password", 
                              params={"password": "weak"}, timeout=TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            if not data.get("valid", True) and data.get("strength") == "weak":
                log_test("Password Validation API (Weak)", "PASS", "Correctly identified weak password")
                results["passed"] += 1
            else:
                log_test("Password Validation API (Weak)", "FAIL", f"Wrong result: {data}")
                results["failed"] += 1
        else:
            log_test("Password Validation API (Weak)", "FAIL", f"Status: {response.status_code}")
            results["failed"] += 1
    except Exception as e:
        log_test("Password Validation API (Weak)", "FAIL", f"Request failed: {str(e)}")
        results["failed"] += 1
    
    results["total"] += 1
    
    # Test strong password
    try:
        response = requests.get(f"{BASE_URL}/auth/validate-password", 
                              params={"password": "StrongPass123!"}, timeout=TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("valid", False) and data.get("strength") in ["good", "strong"]:
                log_test("Password Validation API (Strong)", "PASS", f"Correctly identified: {data.get('strength')}")
                results["passed"] += 1
            else:
                log_test("Password Validation API (Strong)", "FAIL", f"Wrong result: {data}")
                results["failed"] += 1
        else:
            log_test("Password Validation API (Strong)", "FAIL", f"Status: {response.status_code}")
            results["failed"] += 1
    except Exception as e:
        log_test("Password Validation API (Strong)", "FAIL", f"Request failed: {str(e)}")
        results["failed"] += 1
    
    results["total"] += 1
    
    return results

def test_email_integration():
    """Test email integration (welcome email)"""
    print(f"\n{Colors.BLUE}=== Testing Email Integration ==={Colors.ENDC}")
    
    results = {"passed": 0, "failed": 0, "total": 0}
    
    # Register user and check if email doesn't block registration
    try:
        response = requests.post(f"{BASE_URL}/auth/register", 
                               json={
                                   "email": f"email.test.{int(time.time())}@test.com",
                                   "password": "EmailTest123!",
                                   "name": "Email Test User",
                                   "role": "user"
                               }, timeout=TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            if "token" in data and "user" in data:
                log_test("Registration with Email Integration", "PASS", "Registration succeeded despite email errors")
                results["passed"] += 1
            else:
                log_test("Registration with Email Integration", "FAIL", f"Registration failed: {data}")
                results["failed"] += 1
        else:
            log_test("Registration with Email Integration", "FAIL", f"Status: {response.status_code}")
            results["failed"] += 1
    except Exception as e:
        log_test("Registration with Email Integration", "FAIL", f"Request failed: {str(e)}")
        results["failed"] += 1
    
    results["total"] += 1
    
    return results

def test_forgot_password():
    """Test forgot password flow"""
    print(f"\n{Colors.BLUE}=== Testing Forgot Password Flow ==={Colors.ENDC}")
    
    results = {"passed": 0, "failed": 0, "total": 0}
    
    # Test with existing email
    try:
        response = requests.post(f"{BASE_URL}/auth/forgot-password", 
                               json={"email": "test@example.com"}, timeout=TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            expected_msg = "If an account with that email exists, a password reset link has been sent."
            if data.get("message") == expected_msg:
                log_test("Forgot Password Flow", "PASS", "Correct security message returned")
                results["passed"] += 1
            else:
                log_test("Forgot Password Flow", "FAIL", f"Wrong message: {data.get('message')}")
                results["failed"] += 1
        else:
            log_test("Forgot Password Flow", "FAIL", f"Status: {response.status_code}")
            results["failed"] += 1
    except Exception as e:
        log_test("Forgot Password Flow", "FAIL", f"Request failed: {str(e)}")
        results["failed"] += 1
    
    results["total"] += 1
    
    # Test with non-existent email (should return same message)
    try:
        response = requests.post(f"{BASE_URL}/auth/forgot-password", 
                               json={"email": "nonexistent@fake.com"}, timeout=TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            expected_msg = "If an account with that email exists, a password reset link has been sent."
            if data.get("message") == expected_msg:
                log_test("Forgot Password Security", "PASS", "Same message for non-existent email (good security)")
                results["passed"] += 1
            else:
                log_test("Forgot Password Security", "FAIL", f"Different message reveals email existence")
                results["failed"] += 1
        else:
            log_test("Forgot Password Security", "FAIL", f"Status: {response.status_code}")
            results["failed"] += 1
    except Exception as e:
        log_test("Forgot Password Security", "FAIL", f"Request failed: {str(e)}")
        results["failed"] += 1
    
    results["total"] += 1
    
    return results

def test_reset_password():
    """Test reset password flow"""
    print(f"\n{Colors.BLUE}=== Testing Reset Password Flow ==={Colors.ENDC}")
    
    results = {"passed": 0, "failed": 0, "total": 0}
    
    # Test with invalid token
    try:
        response = requests.post(f"{BASE_URL}/auth/reset-password", 
                               json={
                                   "token": "invalid-token-123",
                                   "new_password": "NewStrongPass123!"
                               }, timeout=TIMEOUT)
        
        if response.status_code == 400:
            error_msg = response.json().get("detail", "")
            if "invalid" in error_msg.lower() or "expired" in error_msg.lower():
                log_test("Reset Password (Invalid Token)", "PASS", f"Correctly rejected: {error_msg}")
                results["passed"] += 1
            else:
                log_test("Reset Password (Invalid Token)", "FAIL", f"Wrong error: {error_msg}")
                results["failed"] += 1
        else:
            log_test("Reset Password (Invalid Token)", "FAIL", f"Expected 400, got {response.status_code}")
            results["failed"] += 1
    except Exception as e:
        log_test("Reset Password (Invalid Token)", "FAIL", f"Request failed: {str(e)}")
        results["failed"] += 1
    
    results["total"] += 1
    
    # Test with weak password
    try:
        response = requests.post(f"{BASE_URL}/auth/reset-password", 
                               json={
                                   "token": "some-token-123",
                                   "new_password": "weak"
                               }, timeout=TIMEOUT)
        
        if response.status_code == 400:
            error_msg = response.json().get("detail", "")
            if "8 characters" in error_msg.lower() or "password" in error_msg.lower():
                log_test("Reset Password (Weak Password)", "PASS", f"Correctly rejected weak password")
                results["passed"] += 1
            else:
                log_test("Reset Password (Weak Password)", "FAIL", f"Wrong error: {error_msg}")
                results["failed"] += 1
        else:
            log_test("Reset Password (Weak Password)", "FAIL", f"Expected 400, got {response.status_code}")
            results["failed"] += 1
    except Exception as e:
        log_test("Reset Password (Weak Password)", "FAIL", f"Request failed: {str(e)}")
        results["failed"] += 1
    
    results["total"] += 1
    
    return results

def main():
    """Run all security tests"""
    print(f"{Colors.BOLD}NourishStrong Security Features Testing{Colors.ENDC}")
    print(f"Testing against: {BASE_URL}")
    print("=" * 60)
    
    total_results = {"passed": 0, "failed": 0, "total": 0}
    
    # Run all tests
    pwd_results, test_email = test_password_strength()
    api_results = test_password_validation_api()
    email_results = test_email_integration()
    forgot_results = test_forgot_password()
    reset_results = test_reset_password()
    
    # Combine results
    for result in [pwd_results, api_results, email_results, forgot_results, reset_results]:
        total_results["passed"] += result["passed"]
        total_results["failed"] += result["failed"]
        total_results["total"] += result["total"]
    
    # Print summary
    print(f"\n{Colors.BOLD}=== SECURITY TEST SUMMARY ==={Colors.ENDC}")
    print(f"Total Tests: {total_results['total']}")
    print(f"{Colors.GREEN}Passed: {total_results['passed']}{Colors.ENDC}")
    print(f"{Colors.RED}Failed: {total_results['failed']}{Colors.ENDC}")
    
    success_rate = (total_results['passed'] / total_results['total']) * 100 if total_results['total'] > 0 else 0
    print(f"Success Rate: {success_rate:.1f}%")
    
    # Test specific features
    print(f"\n{Colors.BOLD}=== FEATURE STATUS ==={Colors.ENDC}")
    print(f"✅ Password Strength Validation: {pwd_results['passed']}/{pwd_results['total']} tests passed")
    print(f"✅ Password Validation API: {api_results['passed']}/{api_results['total']} tests passed")
    print(f"✅ Email Integration: {email_results['passed']}/{email_results['total']} tests passed")
    print(f"✅ Forgot Password Flow: {forgot_results['passed']}/{forgot_results['total']} tests passed")
    print(f"✅ Reset Password Flow: {reset_results['passed']}/{reset_results['total']} tests passed")
    
    if total_results['failed'] > 0:
        print(f"\n{Colors.RED}Some tests failed - see details above{Colors.ENDC}")
        return False
    else:
        print(f"\n{Colors.GREEN}All security features working correctly!{Colors.ENDC}")
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)