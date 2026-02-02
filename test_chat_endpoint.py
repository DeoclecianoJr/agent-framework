#!/usr/bin/env python3
"""Quick test script for chat endpoint"""
import requests
import json

# Test configuration
BASE_URL = "http://localhost:8000"
API_KEY = "ccc307ba25c5bf77d04af3850b7741c11388fd3ecf01c5171d6e85cede546abe"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

def test_chat_sessions():
    """Test GET /chat/sessions endpoint"""
    print("Testing GET /chat/sessions...")
    try:
        response = requests.get(f"{BASE_URL}/chat/sessions", headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_health():
    """Test health endpoint first"""
    print("Testing GET /health...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("=== API Endpoint Tests ===")
    
    if test_health():
        print("✅ Health check passed")
        if test_chat_sessions():
            print("✅ Chat sessions endpoint working!")
        else:
            print("❌ Chat sessions endpoint failed")
    else:
        print("❌ Health check failed - API not running")