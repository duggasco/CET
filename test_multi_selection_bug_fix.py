#!/usr/bin/env python3
"""
Test script to verify the multi-selection table display bug fix.
Tests that tables show ALL items with selections highlighted, not just selected items.
"""

import asyncio
import json
from playwright.async_api import async_playwright


async def test_multi_selection_display():
    """Test that tables maintain all items when multiple selections are made"""
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        # Enable console logging
        page.on('console', lambda msg: print(f'Browser console: {msg.text}'))
        
        results = {
            'single_selection': {},
            'multi_selection': {},
            'v2_api_calls': []
        }
        
        # Monitor network requests to track v2 API calls
        async def handle_request(request):
            if '/api/v2/dashboard' in request.url:
                results['v2_api_calls'].append({
                    'url': request.url,
                    'params': request.url.split('?')[1] if '?' in request.url else ''
                })
        
        page.on('request', handle_request)
        
        try:
            # Test with v2 tables enabled
            print("\n=== Testing with V2 Tables Enabled ===")
            await page.goto('http://localhost:9097')  # v2-only container
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(2000)
            
            # Get initial client count
            initial_client_rows = await page.locator('#clientTable tbody tr').count()
            print(f"Initial client rows: {initial_client_rows}")
            results['initial_client_count'] = initial_client_rows
            
            # Test 1: Single client selection
            print("\n--- Test 1: Single Client Selection ---")
            # Click first client
            await page.click('#clientTable tbody tr:first-child')
            await page.wait_for_timeout(1000)
            
            # Check if all clients are still visible
            single_client_rows = await page.locator('#clientTable tbody tr').count()
            print(f"Client rows after single selection: {single_client_rows}")
            results['single_selection']['client_count'] = single_client_rows
            
            # Check if selection is highlighted
            selected_count = await page.locator('#clientTable tbody tr.selected').count()
            print(f"Selected rows: {selected_count}")
            results['single_selection']['selected_count'] = selected_count
            
            # Check v2 API call for selection_source
            if results['v2_api_calls']:
                last_call = results['v2_api_calls'][-1]
                print(f"V2 API call: {last_call['params']}")
                results['single_selection']['api_params'] = last_call['params']
            
            # Test 2: Multiple client selection
            print("\n--- Test 2: Multiple Client Selection ---")
            # Click second client (multi-select)
            await page.click('#clientTable tbody tr:nth-child(2)')
            await page.wait_for_timeout(1000)
            
            # Check if all clients are still visible
            multi_client_rows = await page.locator('#clientTable tbody tr').count()
            print(f"Client rows after multi selection: {multi_client_rows}")
            results['multi_selection']['client_count'] = multi_client_rows
            
            # Check selected count
            multi_selected_count = await page.locator('#clientTable tbody tr.selected').count()
            print(f"Selected rows: {multi_selected_count}")
            results['multi_selection']['selected_count'] = multi_selected_count
            
            # Check v2 API call
            if len(results['v2_api_calls']) > 1:
                last_call = results['v2_api_calls'][-1]
                print(f"V2 API call: {last_call['params']}")
                results['multi_selection']['api_params'] = last_call['params']
            
            # Test 3: Clear selections
            print("\n--- Test 3: Clear Selections ---")
            # Click outside tables to clear
            await page.click('body', position={'x': 50, 'y': 50})
            await page.wait_for_timeout(1000)
            
            # Test 4: Fund table selection
            print("\n--- Test 4: Fund Table Selection ---")
            initial_fund_rows = await page.locator('#fundTable tbody tr').count()
            print(f"Initial fund rows: {initial_fund_rows}")
            results['initial_fund_count'] = initial_fund_rows
            
            # Select first two funds
            await page.click('#fundTable tbody tr:first-child')
            await page.wait_for_timeout(500)
            await page.click('#fundTable tbody tr:nth-child(2)')
            await page.wait_for_timeout(1000)
            
            fund_rows_after = await page.locator('#fundTable tbody tr').count()
            print(f"Fund rows after multi selection: {fund_rows_after}")
            results['multi_selection']['fund_count'] = fund_rows_after
            
            # Check v2 API call
            if results['v2_api_calls']:
                last_call = results['v2_api_calls'][-1]
                print(f"V2 API call: {last_call['params']}")
                results['multi_selection']['fund_api_params'] = last_call['params']
            
            # Analyze results
            print("\n=== Analysis ===")
            
            # Check if bug is fixed
            bug_fixed = True
            issues = []
            
            # Single selection should show all items
            if results['single_selection']['client_count'] != results['initial_client_count']:
                bug_fixed = False
                issues.append(f"Single selection: Expected {results['initial_client_count']} clients, got {results['single_selection']['client_count']}")
            
            # Multi selection should show all items
            if results['multi_selection']['client_count'] != results['initial_client_count']:
                bug_fixed = False
                issues.append(f"Multi selection: Expected {results['initial_client_count']} clients, got {results['multi_selection']['client_count']}")
            
            # Fund multi selection should show all items
            if results['multi_selection']['fund_count'] != results['initial_fund_count']:
                bug_fixed = False
                issues.append(f"Fund multi selection: Expected {results['initial_fund_count']} funds, got {results['multi_selection']['fund_count']}")
            
            # Check for selection_source parameter
            has_selection_source = any('selection_source=' in call['params'] for call in results['v2_api_calls'])
            if not has_selection_source:
                print("Warning: No selection_source parameter found in v2 API calls")
            
            if bug_fixed:
                print("\n✅ BUG FIXED: Tables maintain all items during multi-selection!")
                print("All tests passed - Tableau-like behavior is working correctly.")
            else:
                print("\n❌ BUG STILL EXISTS:")
                for issue in issues:
                    print(f"  - {issue}")
            
            # Print detailed results
            print("\n=== Detailed Results ===")
            print(json.dumps(results, indent=2))
            
            return bug_fixed
            
        finally:
            await browser.close()


if __name__ == "__main__":
    # Run the test
    bug_fixed = asyncio.run(test_multi_selection_display())
    exit(0 if bug_fixed else 1)