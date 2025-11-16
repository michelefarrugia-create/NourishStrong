#!/usr/bin/env python3
"""
Simple sequential backend test
"""

import requests
import json
import time

BASE_URL = "https://weight-wellness-4.preview.emergentagent.com/api"

def test_step_by_step():
    print("Testing step by step...")
    
    # Test 1: Health check
    print("1. Health check...")
    response = requests.get(f"{BASE_URL}/health", timeout=30)
    print(f"   Status: {response.status_code}, Response: {response.json()}")
    
    time.sleep(2)
    
    # Test 2: User registration
    print("2. User registration...")
    user_data = {
        "email": "simple.test@example.com",
        "password": "SimplePass123!",
        "name": "Simple Test User",
        "role": "user"
    }
    
    response = requests.post(f"{BASE_URL}/auth/register", json=user_data, timeout=30)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        token = response.json()["token"]
        print(f"   Token received: {token[:20]}...")
        
        time.sleep(2)
        
        # Test 3: Get user info
        print("3. Get user info...")
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/auth/me", headers=headers, timeout=30)
        print(f"   Status: {response.status_code}, User: {response.json().get('email', 'N/A')}")
        
        time.sleep(2)
        
        # Test 4: Create meal
        print("4. Create meal...")
        meal_data = {
            "image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
            "notes": "Simple test meal"
        }
        
        response = requests.post(f"{BASE_URL}/meals", json=meal_data, headers=headers, timeout=60)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            meal_response = response.json()
            print(f"   Meal created: {meal_response.get('food_name', 'N/A')}")
        else:
            print(f"   Error: {response.text}")
    else:
        print(f"   Registration failed: {response.text}")

if __name__ == "__main__":
    test_step_by_step()