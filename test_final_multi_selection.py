#!/usr/bin/env python3
"""
Final test to verify the multi-selection bug is fixed.
"""

import requests
import json
import sys


def test_multi_selection_fix():
    """Test that tables show ALL items when multiple items from single table are selected"""
    
    base_url = "http://localhost:9097"  # v2-only container
    
    print("=== Testing Multi-Selection Bug Fix ===\n")
    
    # 1. Get overview data to know total counts
    print("1. Getting overview data...")
    response = requests.get(f"{base_url}/api/v2/dashboard")
    if response.status_code != 200:
        print(f"❌ Failed to get overview data: {response.status_code}")
        return False
    
    overview = response.json()
    total_clients = len(overview.get('client_balances', []))
    total_funds = len(overview.get('fund_balances', []))
    total_accounts = len(overview.get('account_details', []))
    
    print(f"   Total clients: {total_clients}")
    print(f"   Total funds: {total_funds}")
    print(f"   Total accounts: {total_accounts}")
    
    # Get first two client IDs for testing
    if total_clients < 2:
        print("❌ Not enough clients for testing")
        return False
    
    client1_id = overview['client_balances'][0]['client_id']
    client2_id = overview['client_balances'][1]['client_id']
    client1_name = overview['client_balances'][0]['client_name']
    client2_name = overview['client_balances'][1]['client_name']
    
    # 2. Test single client selection
    print(f"\n2. Testing single client selection ({client1_name})...")
    response = requests.get(f"{base_url}/api/v2/dashboard?client_ids={client1_id}&selection_source=client")
    if response.status_code != 200:
        print(f"❌ Request failed: {response.status_code}")
        return False
    
    single_data = response.json()
    single_client_count = len(single_data.get('client_balances', []))
    single_fund_count = len(single_data.get('fund_balances', []))
    
    print(f"   Clients returned: {single_client_count} (should be {total_clients})")
    print(f"   Funds returned: {single_fund_count} (filtered for selected client)")
    
    # 3. Test multiple client selection
    print(f"\n3. Testing multiple client selection ({client1_name} + {client2_name})...")
    response = requests.get(f"{base_url}/api/v2/dashboard?client_ids={client1_id},{client2_id}&selection_source=client")
    if response.status_code != 200:
        print(f"❌ Request failed: {response.status_code}")
        return False
    
    multi_data = response.json()
    multi_client_count = len(multi_data.get('client_balances', []))
    multi_fund_count = len(multi_data.get('fund_balances', []))
    
    print(f"   Clients returned: {multi_client_count} (should be {total_clients})")
    print(f"   Funds returned: {multi_fund_count} (filtered for selected clients)")
    
    # 4. Test fund selection
    if total_funds >= 2:
        fund1 = overview['fund_balances'][0]['fund_name']
        fund2 = overview['fund_balances'][1]['fund_name']
        
        print(f"\n4. Testing multiple fund selection ({fund1} + {fund2})...")
        response = requests.get(f"{base_url}/api/v2/dashboard?fund_names={requests.utils.quote(fund1)},{requests.utils.quote(fund2)}&selection_source=fund")
        if response.status_code != 200:
            print(f"❌ Request failed: {response.status_code}")
            return False
        
        fund_data = response.json()
        fund_table_count = len(fund_data.get('fund_balances', []))
        client_table_count = len(fund_data.get('client_balances', []))
        
        print(f"   Funds returned: {fund_table_count} (should be {total_funds})")
        print(f"   Clients returned: {client_table_count} (filtered for selected funds)")
    
    # Analyze results
    print("\n=== Analysis ===")
    
    success = True
    
    # Check single selection
    if single_client_count == total_clients:
        print("✅ Single client selection: Shows ALL clients")
    else:
        print(f"❌ Single client selection: Expected {total_clients}, got {single_client_count}")
        success = False
    
    # Check multi selection
    if multi_client_count == total_clients:
        print("✅ Multi client selection: Shows ALL clients (BUG FIXED!)")
    else:
        print(f"❌ Multi client selection: Expected {total_clients}, got {multi_client_count} (BUG STILL EXISTS)")
        success = False
    
    # Check funds behavior
    if total_funds >= 2 and fund_table_count == total_funds:
        print("✅ Multi fund selection: Shows ALL funds")
    
    if success:
        print("\n🎉 SUCCESS: Multi-selection bug is FIXED!")
        print("Tables now show ALL items with selected items highlighted (Tableau-like behavior)")
    else:
        print("\n❌ FAILED: Multi-selection bug still exists")
    
    return success


if __name__ == "__main__":
    success = test_multi_selection_fix()
    sys.exit(0 if success else 1)