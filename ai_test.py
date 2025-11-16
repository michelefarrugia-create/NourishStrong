#!/usr/bin/env python3
"""
Quick test for AI food analysis functionality
"""

import requests
import json
import base64

BASE_URL = "https://weight-wellness-4.preview.emergentagent.com/api"

def create_sample_food_image():
    """Create a simple base64 encoded image for testing"""
    return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="

def test_ai_analysis():
    # Register a user first
    user_data = {
        "email": "test.ai@example.com",
        "password": "TestPass123!",
        "name": "AI Test User",
        "role": "user"
    }
    
    response = requests.post(f"{BASE_URL}/auth/register", json=user_data, timeout=30)
    if response.status_code != 200:
        print(f"Registration failed: {response.status_code}")
        return
    
    token = response.json()["token"]
    
    # Test meal creation with AI analysis
    meal_data = {
        "image_base64": create_sample_food_image(),
        "notes": "Testing AI food analysis"
    }
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{BASE_URL}/meals", json=meal_data, headers=headers, timeout=60)
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

if __name__ == "__main__":
    test_ai_analysis()