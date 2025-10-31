#!/usr/bin/env python3
"""
Comprehensive Backend Testing for Weight Loss Journey App
Tests authentication, AI food analysis, privacy controls, and coach endpoints
"""

import requests
import json
import base64
import time
from datetime import datetime
import sys

# Configuration
BASE_URL = "https://nourish-track.preview.emergentagent.com/api"
TIMEOUT = 60

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

def create_sample_food_image():
    """Create a simple base64 encoded image for testing"""
    # This is a minimal 1x1 pixel PNG image in base64
    # In real testing, you'd use an actual food image
    return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="

class BackendTester:
    def __init__(self):
        self.user_token = None
        self.coach_token = None
        self.user_id = None
        self.coach_id = None
        self.meal_id = None
        self.timestamp = str(int(time.time()))
        self.user_email = f"sarah.johnson.{self.timestamp}@example.com"
        self.coach_email = f"dr.martinez.{self.timestamp}@healthcoach.com"
        self.test_results = {
            "passed": 0,
            "failed": 0,
            "total": 0
        }

    def make_request(self, method, endpoint, data=None, headers=None, auth_token=None):
        """Make HTTP request with proper error handling"""
        url = f"{BASE_URL}{endpoint}"
        
        if headers is None:
            headers = {"Content-Type": "application/json"}
        
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=TIMEOUT)
            elif method == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=TIMEOUT)
            elif method == "PUT":
                response = requests.put(url, json=data, headers=headers, timeout=TIMEOUT)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=TIMEOUT)
            
            return response
        except requests.exceptions.Timeout:
            print(f"Request timed out after {TIMEOUT} seconds")
            return None
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None

    def test_health_check(self):
        """Test basic health endpoint"""
        print(f"\n{Colors.BLUE}=== Testing Health Check ==={Colors.ENDC}")
        
        response = self.make_request("GET", "/health")
        if response and response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy":
                log_test("Health Check", "PASS", "Backend is healthy")
                self.test_results["passed"] += 1
            else:
                log_test("Health Check", "FAIL", f"Unexpected response: {data}")
                self.test_results["failed"] += 1
        else:
            log_test("Health Check", "FAIL", f"Status: {response.status_code if response else 'No response'}")
            self.test_results["failed"] += 1
        
        self.test_results["total"] += 1

    def test_user_registration(self):
        """Test user registration with both user and coach roles"""
        print(f"\n{Colors.BLUE}=== Testing User Registration ==={Colors.ENDC}")
        
        # Test regular user registration
        user_data = {
            "email": self.user_email,
            "password": "SecurePass123!",
            "name": "Sarah Johnson",
            "role": "user"
        }
        
        response = self.make_request("POST", "/auth/register", user_data)
        if response and response.status_code == 200:
            data = response.json()
            if "token" in data and "user" in data:
                self.user_token = data["token"]
                self.user_id = data["user"]["user_id"]
                log_test("User Registration", "PASS", f"User registered: {data['user']['name']}")
                self.test_results["passed"] += 1
            else:
                log_test("User Registration", "FAIL", f"Missing token or user data: {data}")
                self.test_results["failed"] += 1
        else:
            log_test("User Registration", "FAIL", f"Status: {response.status_code if response else 'No response'}")
            self.test_results["failed"] += 1
        
        self.test_results["total"] += 1
        
        # Add delay between requests
        time.sleep(1)
        
        # Test coach registration
        coach_data = {
            "email": self.coach_email,
            "password": "CoachPass456!",
            "name": "Dr. Maria Martinez",
            "role": "coach"
        }
        
        response = self.make_request("POST", "/auth/register", coach_data)
        if response and response.status_code == 200:
            data = response.json()
            if "token" in data and "user" in data and data["user"]["role"] == "coach":
                self.coach_token = data["token"]
                self.coach_id = data["user"]["user_id"]
                log_test("Coach Registration", "PASS", f"Coach registered: {data['user']['name']}")
                self.test_results["passed"] += 1
            else:
                log_test("Coach Registration", "FAIL", f"Missing token or incorrect role: {data}")
                self.test_results["failed"] += 1
        else:
            log_test("Coach Registration", "FAIL", f"Status: {response.status_code if response else 'No response'}")
            self.test_results["failed"] += 1
        
        self.test_results["total"] += 1

    def test_user_login(self):
        """Test user login functionality"""
        print(f"\n{Colors.BLUE}=== Testing User Login ==={Colors.ENDC}")
        
        # Test user login - use the same email from registration
        login_data = {
            "email": self.user_email,
            "password": "SecurePass123!"
        }
        
        response = self.make_request("POST", "/auth/login", login_data)
        if response and response.status_code == 200:
            data = response.json()
            if "token" in data and "user" in data:
                log_test("User Login", "PASS", f"User logged in: {data['user']['name']}")
                self.test_results["passed"] += 1
            else:
                log_test("User Login", "FAIL", f"Missing token or user data: {data}")
                self.test_results["failed"] += 1
        else:
            log_test("User Login", "FAIL", f"Status: {response.status_code if response else 'No response'}")
            self.test_results["failed"] += 1
        
        self.test_results["total"] += 1

    def test_jwt_validation(self):
        """Test JWT token validation"""
        print(f"\n{Colors.BLUE}=== Testing JWT Token Validation ==={Colors.ENDC}")
        
        # Test with valid token
        response = self.make_request("GET", "/auth/me", auth_token=self.user_token)
        if response and response.status_code == 200:
            data = response.json()
            if "user_id" in data and "email" in data:
                log_test("Valid JWT Token", "PASS", f"Token validated for: {data['email']}")
                self.test_results["passed"] += 1
            else:
                log_test("Valid JWT Token", "FAIL", f"Incomplete user data: {data}")
                self.test_results["failed"] += 1
        else:
            log_test("Valid JWT Token", "FAIL", f"Status: {response.status_code if response else 'No response'}")
            self.test_results["failed"] += 1
        
        self.test_results["total"] += 1
        
        # Add delay before next test
        time.sleep(2)
        
        # Test with invalid token - use shorter timeout for this test
        try:
            response = requests.get(f"{BASE_URL}/auth/me", 
                                  headers={"Authorization": "Bearer invalid_token"}, 
                                  timeout=10)
            if response.status_code == 401:
                log_test("Invalid JWT Token", "PASS", "Correctly rejected invalid token")
                self.test_results["passed"] += 1
            else:
                log_test("Invalid JWT Token", "FAIL", f"Should have returned 401, got: {response.status_code}")
                self.test_results["failed"] += 1
        except Exception as e:
            log_test("Invalid JWT Token", "FAIL", f"Request failed: {str(e)}")
            self.test_results["failed"] += 1
        
        self.test_results["total"] += 1

    def test_unauthorized_access(self):
        """Test unauthorized access without token"""
        print(f"\n{Colors.BLUE}=== Testing Unauthorized Access ==={Colors.ENDC}")
        
        # Add delay before test
        time.sleep(2)
        
        # Test accessing protected endpoint without token - use direct request
        try:
            response = requests.get(f"{BASE_URL}/meals", timeout=10)
            if response.status_code == 403:
                log_test("Unauthorized Access", "PASS", "Correctly blocked access without token")
                self.test_results["passed"] += 1
            else:
                log_test("Unauthorized Access", "FAIL", f"Should have returned 403, got: {response.status_code}")
                self.test_results["failed"] += 1
        except Exception as e:
            log_test("Unauthorized Access", "FAIL", f"Request failed: {str(e)}")
            self.test_results["failed"] += 1
        
        self.test_results["total"] += 1

    def test_ai_food_analysis(self):
        """Test AI food image analysis - MOST CRITICAL TEST"""
        print(f"\n{Colors.BLUE}=== Testing AI Food Image Analysis (CRITICAL) ==={Colors.ENDC}")
        
        # Create meal with image
        meal_data = {
            "image_base64": create_sample_food_image(),
            "notes": "Grilled chicken breast with quinoa and steamed broccoli"
        }
        
        response = self.make_request("POST", "/meals", meal_data, auth_token=self.user_token)
        if response and response.status_code == 200:
            data = response.json()
            
            # Check if meal was created
            if "meal_id" in data:
                self.meal_id = data["meal_id"]
                log_test("Meal Creation", "PASS", f"Meal created with ID: {self.meal_id}")
                self.test_results["passed"] += 1
                
                # Check if AI analysis worked (user should get supportive message)
                if "message" in data and "food_name" in data:
                    log_test("AI Analysis Response", "PASS", f"AI analyzed food: {data.get('food_name', 'Unknown')}")
                    self.test_results["passed"] += 1
                    
                    # Verify nutrition data is NOT in user response
                    if "nutrition" not in data:
                        log_test("Privacy Control (User)", "PASS", "Nutrition data correctly hidden from user")
                        self.test_results["passed"] += 1
                    else:
                        log_test("Privacy Control (User)", "FAIL", "Nutrition data exposed to user")
                        self.test_results["failed"] += 1
                else:
                    log_test("AI Analysis Response", "FAIL", f"Missing AI analysis data: {data}")
                    self.test_results["failed"] += 1
            else:
                log_test("Meal Creation", "FAIL", f"No meal_id in response: {data}")
                self.test_results["failed"] += 1
        else:
            log_test("Meal Creation", "FAIL", f"Status: {response.status_code if response else 'No response'}")
            if response:
                print(f"    Response: {response.text}")
            self.test_results["failed"] += 1
        
        self.test_results["total"] += 3

    def test_coach_ai_analysis(self):
        """Test that coaches can see full nutrition data"""
        print(f"\n{Colors.BLUE}=== Testing Coach AI Analysis Access ==={Colors.ENDC}")
        
        # Create meal as coach
        meal_data = {
            "image_base64": create_sample_food_image(),
            "notes": "Testing coach access to nutrition data"
        }
        
        response = self.make_request("POST", "/meals", meal_data, auth_token=self.coach_token)
        if response and response.status_code == 200:
            data = response.json()
            
            # Check if coach gets nutrition data
            if "nutrition" in data:
                nutrition = data["nutrition"]
                if all(key in nutrition for key in ["calories", "protein", "carbs", "fats", "food_name"]):
                    log_test("Coach Nutrition Access", "PASS", f"Coach can see nutrition data: {nutrition['food_name']}")
                    self.test_results["passed"] += 1
                else:
                    log_test("Coach Nutrition Access", "FAIL", f"Incomplete nutrition data: {nutrition}")
                    self.test_results["failed"] += 1
            else:
                log_test("Coach Nutrition Access", "FAIL", "Coach cannot see nutrition data")
                self.test_results["failed"] += 1
        else:
            log_test("Coach Nutrition Access", "FAIL", f"Status: {response.status_code if response else 'No response'}")
            self.test_results["failed"] += 1
        
        self.test_results["total"] += 1

    def test_meal_management(self):
        """Test meal CRUD operations"""
        print(f"\n{Colors.BLUE}=== Testing Meal Management ==={Colors.ENDC}")
        
        # Test getting meals
        response = self.make_request("GET", "/meals", auth_token=self.user_token)
        if response and response.status_code == 200:
            data = response.json()
            if "meals" in data and isinstance(data["meals"], list):
                log_test("Get Meals", "PASS", f"Retrieved {len(data['meals'])} meals")
                self.test_results["passed"] += 1
                
                # Verify nutrition data is hidden from user
                for meal in data["meals"]:
                    if "nutrition" in meal:
                        log_test("Meal Privacy", "FAIL", "Nutrition data exposed in meal list")
                        self.test_results["failed"] += 1
                        break
                else:
                    log_test("Meal Privacy", "PASS", "Nutrition data correctly hidden in meal list")
                    self.test_results["passed"] += 1
            else:
                log_test("Get Meals", "FAIL", f"Invalid response format: {data}")
                self.test_results["failed"] += 1
        else:
            log_test("Get Meals", "FAIL", f"Status: {response.status_code if response else 'No response'}")
            self.test_results["failed"] += 1
        
        self.test_results["total"] += 2
        
        # Test meal deletion if we have a meal_id
        if self.meal_id:
            response = self.make_request("DELETE", f"/meals/{self.meal_id}", auth_token=self.user_token)
            if response and response.status_code == 200:
                log_test("Delete Meal", "PASS", "Meal deleted successfully")
                self.test_results["passed"] += 1
            else:
                log_test("Delete Meal", "FAIL", f"Status: {response.status_code if response else 'No response'}")
                self.test_results["failed"] += 1
            
            self.test_results["total"] += 1

    def test_coach_endpoints(self):
        """Test coach-only endpoints"""
        print(f"\n{Colors.BLUE}=== Testing Coach Endpoints ==={Colors.ENDC}")
        
        # First create a meal as user for coach to see
        meal_data = {
            "image_base64": create_sample_food_image(),
            "notes": "Meal for coach testing"
        }
        
        response = self.make_request("POST", "/meals", meal_data, auth_token=self.user_token)
        if response and response.status_code == 200:
            test_meal_id = response.json().get("meal_id")
        
        time.sleep(1)  # Allow meal to be processed
        
        # Test coach can access users list
        response = self.make_request("GET", "/coach/users", auth_token=self.coach_token)
        if response and response.status_code == 200:
            data = response.json()
            if "users" in data and isinstance(data["users"], list):
                log_test("Coach Get Users", "PASS", f"Coach can access {len(data['users'])} users")
                self.test_results["passed"] += 1
            else:
                log_test("Coach Get Users", "FAIL", f"Invalid response format: {data}")
                self.test_results["failed"] += 1
        else:
            log_test("Coach Get Users", "FAIL", f"Status: {response.status_code if response else 'No response'}")
            self.test_results["failed"] += 1
        
        self.test_results["total"] += 1
        
        # Test regular user CANNOT access coach endpoints
        time.sleep(1)
        response = self.make_request("GET", "/coach/users", auth_token=self.user_token)
        if response and response.status_code == 403:
            log_test("User Blocked from Coach Endpoint", "PASS", "Regular user correctly blocked")
            self.test_results["passed"] += 1
        else:
            log_test("User Blocked from Coach Endpoint", "FAIL", f"Should have returned 403, got: {response.status_code if response else 'No response'}")
            self.test_results["failed"] += 1
        
        self.test_results["total"] += 1
        
        # Test coach can access user meals with nutrition data
        if self.user_id:
            time.sleep(1)
            response = self.make_request("GET", f"/coach/users/{self.user_id}/meals", auth_token=self.coach_token)
            if response and response.status_code == 200:
                data = response.json()
                if "meals" in data and "user" in data:
                    log_test("Coach Get User Meals", "PASS", f"Coach can access user meals: {len(data['meals'])} meals")
                    self.test_results["passed"] += 1
                    
                    # Check if nutrition data is visible to coach
                    for meal in data["meals"]:
                        if "nutrition" in meal:
                            log_test("Coach Nutrition Visibility", "PASS", "Coach can see nutrition data in user meals")
                            self.test_results["passed"] += 1
                            break
                    else:
                        if len(data["meals"]) > 0:
                            log_test("Coach Nutrition Visibility", "FAIL", "Coach cannot see nutrition data")
                            self.test_results["failed"] += 1
                        else:
                            log_test("Coach Nutrition Visibility", "PASS", "No meals to check (expected)")
                            self.test_results["passed"] += 1
                else:
                    log_test("Coach Get User Meals", "FAIL", f"Invalid response format: {data}")
                    self.test_results["failed"] += 1
            else:
                log_test("Coach Get User Meals", "FAIL", f"Status: {response.status_code if response else 'No response'}")
                self.test_results["failed"] += 1
            
            self.test_results["total"] += 2
            
            # Test coach stats endpoint
            time.sleep(1)
            response = self.make_request("GET", f"/coach/users/{self.user_id}/stats", auth_token=self.coach_token)
            if response and response.status_code == 200:
                data = response.json()
                expected_keys = ["total_meals", "total_calories", "total_protein", "total_carbs", "total_fats"]
                if all(key in data for key in expected_keys):
                    log_test("Coach User Stats", "PASS", f"Coach can access user stats: {data['total_meals']} meals")
                    self.test_results["passed"] += 1
                else:
                    log_test("Coach User Stats", "FAIL", f"Missing stats data: {data}")
                    self.test_results["failed"] += 1
            else:
                log_test("Coach User Stats", "FAIL", f"Status: {response.status_code if response else 'No response'}")
                self.test_results["failed"] += 1
            
            self.test_results["total"] += 1

    def run_all_tests(self):
        """Run all backend tests"""
        print(f"{Colors.BOLD}Starting Comprehensive Backend Testing{Colors.ENDC}")
        print(f"Testing against: {BASE_URL}")
        print("=" * 60)
        
        # Run tests in order
        self.test_health_check()
        self.test_user_registration()
        self.test_user_login()
        self.test_jwt_validation()
        self.test_unauthorized_access()
        self.test_ai_food_analysis()
        self.test_coach_ai_analysis()
        self.test_meal_management()
        self.test_coach_endpoints()
        
        # Print summary
        print(f"\n{Colors.BOLD}=== TEST SUMMARY ==={Colors.ENDC}")
        print(f"Total Tests: {self.test_results['total']}")
        print(f"{Colors.GREEN}Passed: {self.test_results['passed']}{Colors.ENDC}")
        print(f"{Colors.RED}Failed: {self.test_results['failed']}{Colors.ENDC}")
        
        success_rate = (self.test_results['passed'] / self.test_results['total']) * 100 if self.test_results['total'] > 0 else 0
        print(f"Success Rate: {success_rate:.1f}%")
        
        if self.test_results['failed'] > 0:
            print(f"\n{Colors.RED}CRITICAL ISSUES FOUND - See failed tests above{Colors.ENDC}")
            return False
        else:
            print(f"\n{Colors.GREEN}ALL TESTS PASSED - Backend is working correctly{Colors.ENDC}")
            return True

if __name__ == "__main__":
    tester = BackendTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)