#!/usr/bin/env python3
import requests
import json

base_url = "http://localhost:9095/api"

def test_filters():
    print("Testing Server-Side Text Filters")
    print("=" * 50)
    
    # Test 1: No filters
    print("\nTest 1: No filters")
    response = requests.get(f"{base_url}/overview")
    data = response.json()
    print(f"Total clients: {len(data.get('client_balances', []))}")
    print(f"Total funds: {len(data.get('fund_balances', []))}")
    print(f"Total accounts: {len(data.get('account_details', []))}")
    
    # Test 2: Filter by client name "Global"
    print("\nTest 2: Filter by client name 'Global'")
    response = requests.get(f"{base_url}/overview", params={'client_name': 'Global'})
    data = response.json()
    print(f"Filtered clients: {len(data.get('client_balances', []))}")
    print(f"Filtered accounts: {len(data.get('account_details', []))}")
    for client in data.get('client_balances', [])[:3]:
        print(f"  - {client['client_name']}")
    
    # Test 3: Filter by fund ticker "MM"
    print("\nTest 3: Filter by fund ticker 'MM'")
    response = requests.get(f"{base_url}/overview", params={'fund_ticker': 'MM'})
    data = response.json()
    print(f"Filtered funds: {len(data.get('fund_balances', []))}")
    for fund in data.get('fund_balances', []):
        print(f"  - {fund['fund_name']} ({fund['fund_ticker']})")
    
    # Test 4: Filter by account number "001"
    print("\nTest 4: Filter by account number '001'")
    response = requests.get(f"{base_url}/overview", params={'account_number': '001'})
    data = response.json()
    print(f"Filtered accounts: {len(data.get('account_details', []))}")
    for account in data.get('account_details', [])[:5]:
        print(f"  - {account['account_id']} ({account['client_name']})")
    
    # Test 5: Combined filters
    print("\nTest 5: Combined filters - Client 'Capital' AND Fund 'INST'")
    response = requests.get(f"{base_url}/overview", params={
        'client_name': 'Capital',
        'fund_ticker': 'INST'
    })
    data = response.json()
    print(f"Filtered clients: {len(data.get('client_balances', []))}")
    print(f"Filtered funds: {len(data.get('fund_balances', []))}")
    print(f"Filtered accounts: {len(data.get('account_details', []))}")
    
    # Test 6: Test on specific client endpoint
    print("\nTest 6: Client endpoint with fund filter")
    # First get a client ID
    response = requests.get(f"{base_url}/overview")
    data = response.json()
    if data.get('client_balances'):
        client_id = data['client_balances'][0]['client_id']
        response = requests.get(f"{base_url}/client/{client_id}", params={'fund_ticker': 'INST'})
        data = response.json()
        print(f"Client funds filtered: {len(data.get('fund_balances', []))}")
        print(f"Client accounts filtered: {len(data.get('account_details', []))}")

if __name__ == "__main__":
    test_filters()