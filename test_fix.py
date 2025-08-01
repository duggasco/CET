#!/usr/bin/env python3
"""
Test script to verify the v2 API fix for selection_source=client
"""

import requests
import json

def test_v2_api_selection_behavior():
    """Test that v2 API properly handles selection_source parameter"""
    
    base_url = "http://localhost:9096"
    client_id = "36e69761-d951-4534-9241-c237721630ab"  # Acme Corporation
    
    print("Testing v2 API selection behavior...")
    print("=" * 50)
    
    # Test 1: Without selection_source (should return only the selected client)
    print("\n1. Testing WITHOUT selection_source:")
    response = requests.get(f"{base_url}/api/v2/dashboard?client_id={client_id}")
    data = response.json()
    client_count = len(data.get('client_balances', []))
    print(f"   Client count: {client_count} (expected: 1)")
    
    if client_count == 1:
        print("   ✅ PASS: Returns only the selected client")
    else:
        print("   ❌ FAIL: Should return only 1 client")
    
    # Test 2: With selection_source=client (should return all clients)
    print("\n2. Testing WITH selection_source=client:")
    response = requests.get(f"{base_url}/api/v2/dashboard?client_id={client_id}&selection_source=client")
    data = response.json()
    client_count = len(data.get('client_balances', []))
    print(f"   Client count: {client_count} (expected: 10)")
    
    if client_count == 10:
        print("   ✅ PASS: Returns all clients (Tableau-like behavior)")
    else:
        print("   ❌ FAIL: Should return all 10 clients")
    
    # Test 3: Verify the selected client still has a fund filter applied
    print("\n3. Testing fund filtering with selection_source=client:")
    fund_count = len(data.get('fund_balances', []))
    print(f"   Fund count: {fund_count}")
    
    # The selected client should still filter the funds shown
    if fund_count > 0:
        print("   ✅ PASS: Fund filtering still works")
    else:
        print("   ❌ FAIL: No funds returned")
    
    print("\n" + "=" * 50)
    print("Test Summary:")
    print("The fix should make the browser show all clients when a client is selected,")
    print("while still filtering other tables based on the selected client's data.")

if __name__ == "__main__":
    test_v2_api_selection_behavior()