#!/usr/bin/env python3
"""Test script to verify chart header max/min/avg updates correctly when clicking dates"""

import requests
import json
from datetime import datetime, timedelta

# Base URL
BASE_URL = 'http://localhost:9095'

def test_date_endpoint_with_filters():
    """Test the date endpoint with selection filters"""
    
    # First get overview data to find some clients and funds
    overview_resp = requests.get(f'{BASE_URL}/api/overview')
    overview_data = overview_resp.json()
    
    # Get first 2 clients and 2 funds for testing
    client_ids = [client['client_id'] for client in overview_data['client_balances'][:2]]
    fund_names = [fund['fund_name'] for fund in overview_data['fund_balances'][:2]]
    
    # Get a date from 30 days ago
    test_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    print(f"Testing date endpoint for {test_date}")
    print(f"Selected clients: {client_ids[:2]}")
    print(f"Selected funds: {fund_names[:2]}")
    
    # Test 1: Date endpoint without filters
    resp1 = requests.get(f'{BASE_URL}/api/date/{test_date}')
    data1 = resp1.json()
    
    if 'recent_history' in data1 and data1['recent_history']:
        balances1 = [item['total_balance'] for item in data1['recent_history']]
        max1 = max(balances1)
        min1 = min(balances1)
        avg1 = sum(balances1) / len(balances1)
        print(f"\nWithout filters:")
        print(f"  Max: ${max1:,.2f}")
        print(f"  Min: ${min1:,.2f}")
        print(f"  Avg: ${avg1:,.2f}")
    
    # Test 2: Date endpoint with client filters
    params = {
        'client_id': client_ids
    }
    resp2 = requests.get(f'{BASE_URL}/api/date/{test_date}', params=params)
    data2 = resp2.json()
    
    if 'recent_history' in data2 and data2['recent_history']:
        balances2 = [item['total_balance'] for item in data2['recent_history']]
        max2 = max(balances2)
        min2 = min(balances2)
        avg2 = sum(balances2) / len(balances2)
        print(f"\nWith client filters:")
        print(f"  Max: ${max2:,.2f}")
        print(f"  Min: ${min2:,.2f}")
        print(f"  Avg: ${avg2:,.2f}")
        print(f"  Should be lower than unfiltered values: {max2 < max1}")
    
    # Test 3: Date endpoint with fund filters
    params = {
        'fund_name': fund_names
    }
    resp3 = requests.get(f'{BASE_URL}/api/date/{test_date}', params=params)
    data3 = resp3.json()
    
    if 'recent_history' in data3 and data3['recent_history']:
        balances3 = [item['total_balance'] for item in data3['recent_history']]
        max3 = max(balances3)
        min3 = min(balances3)
        avg3 = sum(balances3) / len(balances3)
        print(f"\nWith fund filters:")
        print(f"  Max: ${max3:,.2f}")
        print(f"  Min: ${min3:,.2f}")
        print(f"  Avg: ${avg3:,.2f}")
        print(f"  Should be lower than unfiltered values: {max3 < max1}")
    
    # Test 4: Combined filters
    params = {
        'client_id': client_ids,
        'fund_name': fund_names[:1]  # Just one fund
    }
    resp4 = requests.get(f'{BASE_URL}/api/date/{test_date}', params=params)
    data4 = resp4.json()
    
    if 'recent_history' in data4 and data4['recent_history']:
        balances4 = [item['total_balance'] for item in data4['recent_history']]
        if balances4:
            max4 = max(balances4)
            min4 = min(balances4)
            avg4 = sum(balances4) / len(balances4)
            print(f"\nWith combined filters (clients + 1 fund):")
            print(f"  Max: ${max4:,.2f}")
            print(f"  Min: ${min4:,.2f}")
            print(f"  Avg: ${avg4:,.2f}")
            print(f"  Should be lowest values: {max4 <= max2 and max4 <= max3}")

if __name__ == '__main__':
    test_date_endpoint_with_filters()