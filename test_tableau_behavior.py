#!/usr/bin/env python3
"""
Test that verifies Tableau-like behavior is working correctly.
When selection_source is provided, the source table should show ALL items.
"""

import requests
import json
import sys


def test_selection_source_behavior():
    """Test that selection_source parameter enables Tableau-like behavior"""
    
    base_url = "http://localhost:9097"  # v2-only container
    
    print("=== Testing Tableau-like Behavior with selection_source ===\n")
    
    # First, get all clients without any filters
    print("1. Getting all clients (no filters)...")
    response = requests.get(f"{base_url}/api/v2/dashboard")
    if response.status_code != 200:
        print(f"❌ Failed to get overview data: {response.status_code}")
        return False
    
    all_data = response.json()
    all_clients = all_data.get('client_balances', [])
    total_clients = len(all_clients)
    print(f"   Total clients in database: {total_clients}")
    
    if total_clients == 0:
        print("❌ No clients found in database")
        return False
    
    # Get first client ID for testing
    first_client_id = all_clients[0]['client_id']
    first_client_name = all_clients[0]['client_name']
    print(f"   First client: {first_client_name} (ID: {first_client_id})")
    
    # Test 2: Single client selection WITHOUT selection_source
    print("\n2. Single client selection WITHOUT selection_source...")
    response = requests.get(f"{base_url}/api/v2/dashboard?client_ids={first_client_id}")
    if response.status_code != 200:
        print(f"❌ Request failed: {response.status_code}")
        return False
    
    data_without_source = response.json()
    clients_without_source = len(data_without_source.get('client_balances', []))
    print(f"   Clients returned: {clients_without_source}")
    
    # Test 3: Single client selection WITH selection_source=client
    print("\n3. Single client selection WITH selection_source=client...")
    response = requests.get(f"{base_url}/api/v2/dashboard?client_ids={first_client_id}&selection_source=client")
    if response.status_code != 200:
        print(f"❌ Request failed: {response.status_code}")
        return False
    
    data_with_source = response.json()
    clients_with_source = len(data_with_source.get('client_balances', []))
    print(f"   Clients returned: {clients_with_source}")
    
    # Analyze results
    print("\n=== Analysis ===")
    
    if clients_without_source == 1:
        print("✅ Without selection_source: Shows only selected client (expected)")
    else:
        print(f"❌ Without selection_source: Expected 1 client, got {clients_without_source}")
    
    if clients_with_source == total_clients:
        print(f"✅ With selection_source=client: Shows ALL {total_clients} clients (Tableau-like behavior)")
    else:
        print(f"❌ With selection_source=client: Expected {total_clients} clients, got {clients_with_source}")
    
    # Test funds table behavior
    print("\n4. Testing fund table behavior...")
    all_funds = all_data.get('fund_balances', [])
    if all_funds:
        first_fund = all_funds[0]['fund_name']
        total_funds = len(all_funds)
        
        # Without selection_source
        response = requests.get(f"{base_url}/api/v2/dashboard?fund_names={requests.utils.quote(first_fund)}")
        funds_without = len(response.json().get('fund_balances', []))
        
        # With selection_source
        response = requests.get(f"{base_url}/api/v2/dashboard?fund_names={requests.utils.quote(first_fund)}&selection_source=fund")
        funds_with = len(response.json().get('fund_balances', []))
        
        print(f"   Total funds: {total_funds}")
        print(f"   Without selection_source: {funds_without} funds")
        print(f"   With selection_source=fund: {funds_with} funds")
        
        if funds_with == total_funds:
            print("✅ Fund table shows ALL funds with selection_source=fund")
        else:
            print(f"❌ Fund table: Expected {total_funds} funds, got {funds_with}")
    
    # Overall result
    print("\n=== Final Result ===")
    tableau_behavior_working = (clients_with_source == total_clients)
    
    if tableau_behavior_working:
        print("✅ TABLEAU-LIKE BEHAVIOR IS WORKING!")
        print("   Tables show ALL items when selection_source matches the table.")
        print("   This allows selected items to be highlighted while keeping all items visible.")
        return True
    else:
        print("❌ TABLEAU-LIKE BEHAVIOR NOT WORKING")
        print("   The selection_source parameter is not properly excluding filters.")
        return False


if __name__ == "__main__":
    success = test_selection_source_behavior()
    sys.exit(0 if success else 1)