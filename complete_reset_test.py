#!/usr/bin/env python3
"""
Complete Reset Password Flow Test - Tests the full flow with real tokens
"""

import requests
import json
import time
from datetime import datetime, timedelta
import sys
import uuid

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

def test_complete_reset_flow():
    """Test complete password reset flow with real database tokens"""
    print(f"\n{Colors.BLUE}=== Testing Complete Reset Password Flow ==={Colors.ENDC}")
    
    results = {"passed": 0, "failed": 0, "total": 0}
    
    # Step 1: Register a test user
    test_email = f"reset.test.{int(time.time())}@nourishstrong.com"
    original_password = "OriginalPass123!"
    
    try:
        response = requests.post(f"{BASE_URL}/auth/register", 
                               json={
                                   "email": test_email,
                                   "password": original_password,
                                   "name": "Reset Test User",
                                   "role": "user"
                               }, timeout=TIMEOUT)
        
        if response.status_code == 200:
            log_test("User Registration for Reset Test", "PASS", f"Test user created: {test_email}")
            results["passed"] += 1
        else:
            log_test("User Registration for Reset Test", "FAIL", f"Failed to create test user: {response.status_code}")
            results["failed"] += 1
            return results
    except Exception as e:
        log_test("User Registration for Reset Test", "FAIL", f"Request failed: {str(e)}")
        results["failed"] += 1
        return results
    
    results["total"] += 1
    
    # Step 2: Request password reset
    try:
        response = requests.post(f"{BASE_URL}/auth/forgot-password", 
                               json={"email": test_email}, timeout=TIMEOUT)
        
        if response.status_code == 200:
            log_test("Password Reset Request", "PASS", "Reset request sent successfully")
            results["passed"] += 1
        else:
            log_test("Password Reset Request", "FAIL", f"Reset request failed: {response.status_code}")
            results["failed"] += 1
            return results
    except Exception as e:
        log_test("Password Reset Request", "FAIL", f"Request failed: {str(e)}")
        results["failed"] += 1
        return results
    
    results["total"] += 1
    
    # Step 3: Create a real reset token in the database
    try:
        from pymongo import MongoClient
        
        MONGO_URL = "mongodb://localhost:27017"
        client = MongoClient(MONGO_URL)
        db = client['weight_loss_app']
        users_collection = db['users']
        password_reset_tokens_collection = db['password_reset_tokens']
        
        # Find our test user
        user = users_collection.find_one({"email": test_email})
        if not user:
            log_test("Database Token Creation", "FAIL", "Test user not found in database")
            results["failed"] += 1
            return results
        
        # Create a test reset token
        reset_token = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(hours=1)
        
        password_reset_tokens_collection.insert_one({
            "token": reset_token,
            "user_id": user["user_id"],
            "email": test_email,
            "expires_at": expires_at.isoformat(),
            "used": False,
            "created_at": datetime.utcnow().isoformat()
        })
        
        log_test("Database Token Creation", "PASS", f"Reset token created: {reset_token[:8]}...")
        results["passed"] += 1
        
    except Exception as e:
        log_test("Database Token Creation", "FAIL", f"Database operation failed: {str(e)}")
        results["failed"] += 1
        return results
    
    results["total"] += 1
    
    # Step 4: Reset password with valid token
    new_password = "NewStrongPass456!"
    try:
        response = requests.post(f"{BASE_URL}/auth/reset-password", 
                               json={
                                   "token": reset_token,
                                   "new_password": new_password
                               }, timeout=TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            if "successfully" in data.get("message", "").lower():
                log_test("Password Reset with Valid Token", "PASS", "Password reset successful")
                results["passed"] += 1
            else:
                log_test("Password Reset with Valid Token", "FAIL", f"Unexpected message: {data}")
                results["failed"] += 1
        else:
            log_test("Password Reset with Valid Token", "FAIL", f"Reset failed: {response.status_code}, {response.text}")
            results["failed"] += 1
    except Exception as e:
        log_test("Password Reset with Valid Token", "FAIL", f"Request failed: {str(e)}")
        results["failed"] += 1
    
    results["total"] += 1
    
    # Step 5: Try to use the same token again (should fail - one-time use)
    try:
        response = requests.post(f"{BASE_URL}/auth/reset-password", 
                               json={
                                   "token": reset_token,
                                   "new_password": "AnotherPass789!"
                               }, timeout=TIMEOUT)
        
        if response.status_code == 400:
            error_msg = response.json().get("detail", "")
            if "used" in error_msg.lower() or "already" in error_msg.lower():
                log_test("Token One-Time Use Validation", "PASS", "Used token correctly rejected")
                results["passed"] += 1
            else:
                log_test("Token One-Time Use Validation", "FAIL", f"Wrong error for used token: {error_msg}")
                results["failed"] += 1
        else:
            log_test("Token One-Time Use Validation", "FAIL", f"Used token should be rejected, got: {response.status_code}")
            results["failed"] += 1
    except Exception as e:
        log_test("Token One-Time Use Validation", "FAIL", f"Request failed: {str(e)}")
        results["failed"] += 1
    
    results["total"] += 1
    
    # Step 6: Verify old password no longer works
    try:
        response = requests.post(f"{BASE_URL}/auth/login", 
                               json={
                                   "email": test_email,
                                   "password": original_password
                               }, timeout=TIMEOUT)
        
        if response.status_code == 401:
            log_test("Old Password Invalidated", "PASS", "Old password correctly rejected")
            results["passed"] += 1
        else:
            log_test("Old Password Invalidated", "FAIL", f"Old password still works: {response.status_code}")
            results["failed"] += 1
    except Exception as e:
        log_test("Old Password Invalidated", "FAIL", f"Request failed: {str(e)}")
        results["failed"] += 1
    
    results["total"] += 1
    
    # Step 7: Verify new password works
    try:
        response = requests.post(f"{BASE_URL}/auth/login", 
                               json={
                                   "email": test_email,
                                   "password": new_password
                               }, timeout=TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            if "token" in data and "user" in data:
                log_test("New Password Works", "PASS", "Can login with new password")
                results["passed"] += 1
            else:
                log_test("New Password Works", "FAIL", f"Login response missing data: {data}")
                results["failed"] += 1
        else:
            log_test("New Password Works", "FAIL", f"Login with new password failed: {response.status_code}")
            results["failed"] += 1
    except Exception as e:
        log_test("New Password Works", "FAIL", f"Request failed: {str(e)}")
        results["failed"] += 1
    
    results["total"] += 1
    
    # Step 8: Test expired token (create an expired token)
    try:
        expired_token = str(uuid.uuid4())
        expired_time = datetime.utcnow() - timedelta(hours=2)  # 2 hours ago
        
        password_reset_tokens_collection.insert_one({
            "token": expired_token,
            "user_id": user["user_id"],
            "email": test_email,
            "expires_at": expired_time.isoformat(),
            "used": False,
            "created_at": expired_time.isoformat()
        })
        
        response = requests.post(f"{BASE_URL}/auth/reset-password", 
                               json={
                                   "token": expired_token,
                                   "new_password": "ExpiredTest123!"
                               }, timeout=TIMEOUT)
        
        if response.status_code == 400:
            error_msg = response.json().get("detail", "")
            if "expired" in error_msg.lower():
                log_test("Expired Token Rejection", "PASS", "Expired token correctly rejected")
                results["passed"] += 1
            else:
                log_test("Expired Token Rejection", "FAIL", f"Wrong error for expired token: {error_msg}")
                results["failed"] += 1
        else:
            log_test("Expired Token Rejection", "FAIL", f"Expired token should be rejected, got: {response.status_code}")
            results["failed"] += 1
    except Exception as e:
        log_test("Expired Token Rejection", "FAIL", f"Test failed: {str(e)}")
        results["failed"] += 1
    
    results["total"] += 1
    
    return results

def main():
    """Run complete reset password flow test"""
    print(f"{Colors.BOLD}Complete Reset Password Flow Testing{Colors.ENDC}")
    print(f"Testing against: {BASE_URL}")
    print("=" * 60)
    
    results = test_complete_reset_flow()
    
    # Print summary
    print(f"\n{Colors.BOLD}=== COMPLETE RESET FLOW TEST SUMMARY ==={Colors.ENDC}")
    print(f"Total Tests: {results['total']}")
    print(f"{Colors.GREEN}Passed: {results['passed']}{Colors.ENDC}")
    print(f"{Colors.RED}Failed: {results['failed']}{Colors.ENDC}")
    
    success_rate = (results['passed'] / results['total']) * 100 if results['total'] > 0 else 0
    print(f"Success Rate: {success_rate:.1f}%")
    
    if results['failed'] > 0:
        print(f"\n{Colors.RED}Some reset flow tests failed{Colors.ENDC}")
        return False
    else:
        print(f"\n{Colors.GREEN}Complete reset password flow working perfectly!{Colors.ENDC}")
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)