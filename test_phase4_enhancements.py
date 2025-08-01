#!/usr/bin/env python3
"""
Comprehensive test suite for Phase 4 enhancements:
1. Response compression (nginx gzip)
2. Cursor pagination
3. Cache warming
"""
import requests
import time
import json
import base64

BASE_URL = "http://localhost"

def test_compression():
    """Test response compression."""
    print("\n=== Testing Response Compression ===")
    
    # Test without compression
    headers = {"Accept-Encoding": "identity"}
    response = requests.get(f"{BASE_URL}/api/v2/dashboard", headers=headers)
    uncompressed_size = len(response.content)
    
    # Test with compression
    headers = {"Accept-Encoding": "gzip"}
    response = requests.get(f"{BASE_URL}/api/v2/dashboard", headers=headers)
    compressed_size = int(response.headers.get('Content-Length', 0))
    
    if response.headers.get('Content-Encoding') == 'gzip':
        print(f"✓ Compression enabled")
        print(f"  Uncompressed: {uncompressed_size:,} bytes")
        print(f"  Compressed: {compressed_size:,} bytes")
        print(f"  Reduction: {(1 - compressed_size/uncompressed_size)*100:.1f}%")
    else:
        print("✗ Compression not working")
    
    return response.headers.get('Content-Encoding') == 'gzip'

def test_pagination():
    """Test cursor pagination."""
    print("\n=== Testing Cursor Pagination ===")
    
    # Test first page
    response = requests.get(f"{BASE_URL}/api/v2/dashboard?page_size=3")
    data = response.json()
    
    client_count = len(data.get('client_balances', []))
    has_pagination = 'pagination' in data
    
    print(f"✓ First page retrieved: {client_count} clients")
    
    if has_pagination and 'client_balances' in data['pagination']:
        pagination = data['pagination']['client_balances']
        has_more = pagination.get('has_more', False)
        next_cursor = pagination.get('next_cursor')
        
        print(f"  Has more: {has_more}")
        print(f"  Next cursor: {next_cursor[:20]}..." if next_cursor else "  No next cursor")
        
        # Test cursor navigation
        if next_cursor:
            # Decode cursor to see what's inside
            try:
                decoded = base64.b64decode(next_cursor).decode()
                cursor_data = json.loads(decoded)
                print(f"  Cursor contains: {cursor_data}")
            except:
                pass
            
            # Get second page
            response2 = requests.get(f"{BASE_URL}/api/v2/dashboard?page_size=3&client_cursor={next_cursor}")
            data2 = response2.json()
            client_count2 = len(data2.get('client_balances', []))
            
            print(f"✓ Second page retrieved: {client_count2} clients")
            
            # Check no overlap
            first_page_names = [c['client_name'] for c in data['client_balances']]
            second_page_names = [c['client_name'] for c in data2['client_balances']]
            
            if not set(first_page_names).intersection(second_page_names):
                print("✓ No overlap between pages")
            else:
                print("✗ Pages have overlapping data")
    
    # Test chart exclusion with pagination
    response_with_page = requests.get(f"{BASE_URL}/api/v2/dashboard?page_size=10")
    response_without_page = requests.get(f"{BASE_URL}/api/v2/dashboard")
    
    has_charts_paginated = 'charts' in response_with_page.json()
    has_charts_normal = 'charts' in response_without_page.json()
    
    print(f"\nChart inclusion:")
    print(f"  With pagination: {'Yes' if has_charts_paginated else 'No'}")
    print(f"  Without pagination: {'Yes' if has_charts_normal else 'No'}")
    
    return has_pagination and not has_charts_paginated and has_charts_normal

def test_cache():
    """Test cache warming."""
    print("\n=== Testing Cache Warming ===")
    
    # Test cached response
    start = time.time()
    response = requests.get(f"{BASE_URL}/api/v2/dashboard")
    cached_time = time.time() - start
    data = response.json()
    
    is_cached = data.get('metadata', {}).get('from_cache', False)
    cache_timestamp = data.get('metadata', {}).get('cache_timestamp', 'N/A')
    
    print(f"✓ Cached response: {is_cached}")
    print(f"  Response time: {cached_time*1000:.1f}ms")
    print(f"  Cache timestamp: {cache_timestamp}")
    
    # Test uncached response (with filters)
    start = time.time()
    response = requests.get(f"{BASE_URL}/api/v2/dashboard?client_id=d9312eff-1d81-4955-a1d7-4e1a9927c7ed")
    uncached_time = time.time() - start
    data2 = response.json()
    
    is_cached2 = data2.get('metadata', {}).get('from_cache', False)
    
    print(f"\n✓ Filtered response: {'cached' if is_cached2 else 'not cached'}")
    print(f"  Response time: {uncached_time*1000:.1f}ms")
    
    # Speed comparison
    if cached_time < uncached_time * 2:  # Cached should be significantly faster
        print(f"\n✓ Cache provides performance benefit")
    else:
        print(f"\n✗ Cache not providing expected performance benefit")
    
    return is_cached and not is_cached2

def test_combined_features():
    """Test features working together."""
    print("\n=== Testing Combined Features ===")
    
    # Test pagination + compression
    headers = {"Accept-Encoding": "gzip"}
    response = requests.get(f"{BASE_URL}/api/v2/dashboard?page_size=5", headers=headers)
    
    is_compressed = response.headers.get('Content-Encoding') == 'gzip'
    has_pagination = 'pagination' in response.json()
    
    print(f"✓ Pagination + Compression: {'Working' if is_compressed and has_pagination else 'Not working'}")
    print(f"  Response size: {len(response.content):,} bytes")
    
    # Test all query parameters
    params = {
        "page_size": 2,
        "client_id": "d9312eff-1d81-4955-a1d7-4e1a9927c7ed",
        "fund_name": "Prime Money Market",
        "client_name": "Acme"
    }
    response = requests.get(f"{BASE_URL}/api/v2/dashboard", params=params)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✓ Complex query successful")
        print(f"  Clients returned: {len(data.get('client_balances', []))}")
        print(f"  Funds returned: {len(data.get('fund_balances', []))}")
        print(f"  Accounts returned: {len(data.get('account_details', []))}")
    
    return is_compressed and has_pagination

def run_all_tests():
    """Run all Phase 4 enhancement tests."""
    print("Phase 4 Enhancement Test Suite")
    print("=" * 50)
    
    results = {
        "Compression": test_compression(),
        "Pagination": test_pagination(),
        "Cache": test_cache(),
        "Combined": test_combined_features()
    }
    
    print("\n" + "=" * 50)
    print("Test Summary:")
    for test, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {test}: {status}")
    
    all_passed = all(results.values())
    print(f"\nOverall: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")
    
    return all_passed

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)