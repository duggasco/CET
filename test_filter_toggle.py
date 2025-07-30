#!/usr/bin/env python3
"""
Automated test script for the collapsible filter toolbar
"""

import requests
import json
import time

BASE_URL = "http://localhost:9095"

def test_api_filters():
    """Test that API filters work correctly"""
    print("Testing API filters...")
    
    # Test fund ticker filter
    response = requests.get(f"{BASE_URL}/api/overview?fund_ticker=GMMF")
    data = response.json()
    fund_names = [f['fund_name'] for f in data.get('fund_balances', [])]
    assert all('Government' in name for name in fund_names), "Fund ticker filter not working"
    print("✓ Fund ticker filter working")
    
    # Test client name filter
    response = requests.get(f"{BASE_URL}/api/overview?client_name=Tech")
    data = response.json()
    client_names = [c['client_name'] for c in data.get('client_balances', [])]
    assert all('Tech' in name for name in client_names), "Client name filter not working"
    print("✓ Client name filter working")
    
    # Test account number filter
    response = requests.get(f"{BASE_URL}/api/overview?account_number=GRO-005")
    data = response.json()
    account_ids = [a['account_id'] for a in data.get('account_details', [])]
    assert all('GRO-005' in aid for aid in account_ids), "Account number filter not working"
    print("✓ Account number filter working")
    
    # Test multiple filters
    response = requests.get(f"{BASE_URL}/api/overview?fund_ticker=GMMF&client_name=Tech")
    data = response.json()
    assert len(data.get('client_balances', [])) > 0, "Multiple filters not working"
    print("✓ Multiple filters working")
    
    return True

def test_page_loads():
    """Test that the main page loads correctly"""
    print("\nTesting page load...")
    response = requests.get(BASE_URL)
    assert response.status_code == 200, "Page not loading"
    assert "toggle-filters" in response.text, "Toggle button not found"
    assert "filter-section" in response.text, "Filter section not found"
    assert "Ctrl+F" in response.text, "Keyboard shortcut hint not found"
    print("✓ Page loads with all filter elements")
    return True

def main():
    print("Client Exploration Tool - Filter Toggle Automated Tests")
    print("=" * 50)
    
    try:
        # Test page loads
        test_page_loads()
        
        # Test API filters
        test_api_filters()
        
        print("\n" + "=" * 50)
        print("All automated tests passed! ✅")
        print("\nManual testing required for:")
        print("- Toggle button animation")
        print("- localStorage persistence")
        print("- Ctrl+F keyboard shortcut")
        print("- Mobile responsiveness")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())