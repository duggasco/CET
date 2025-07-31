#!/usr/bin/env python3
"""Test the chart header updates in the UI using Playwright"""

from playwright.sync_api import sync_playwright
import time

def test_chart_header_updates():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        
        # Navigate to the app
        page.goto('http://localhost:9095')
        page.wait_for_load_state('networkidle')
        
        # Get initial max/min/avg values
        initial_90day_stats = page.locator('#recentChartStats').text_content()
        initial_3year_stats = page.locator('#longTermChartStats').text_content()
        
        print("Initial 90-day stats:", initial_90day_stats)
        print("Initial 3-year stats:", initial_3year_stats)
        
        # Select first two clients
        client_rows = page.locator('#clientTable tbody tr')
        if client_rows.count() >= 2:
            client_rows.nth(0).click()
            page.wait_for_timeout(500)
            client_rows.nth(1).click()
            page.wait_for_timeout(1000)
            
            # Get stats after client selection
            client_90day_stats = page.locator('#recentChartStats').text_content()
            client_3year_stats = page.locator('#longTermChartStats').text_content()
            
            print("\nAfter selecting 2 clients:")
            print("90-day stats:", client_90day_stats)
            print("3-year stats:", client_3year_stats)
            
            # Now click on a date in the 90-day chart
            # Get the chart element and click near the middle
            chart_element = page.locator('#recentChart')
            box = chart_element.bounding_box()
            if box:
                # Click in the middle of the chart
                page.mouse.click(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
                page.wait_for_timeout(2000)
                
                # Get stats after date click
                date_90day_stats = page.locator('#recentChartStats').text_content()
                date_3year_stats = page.locator('#longTermChartStats').text_content()
                
                print("\nAfter clicking date on chart (with clients selected):")
                print("90-day stats:", date_90day_stats)
                print("3-year stats:", date_3year_stats)
                
                # Verify the values are still filtered (should match client selection stats)
                if date_90day_stats == client_90day_stats:
                    print("\n✓ SUCCESS: Chart stats correctly maintained after date click!")
                else:
                    print("\n✗ FAILED: Chart stats changed unexpectedly after date click")
        
        browser.close()

if __name__ == '__main__':
    test_chart_header_updates()