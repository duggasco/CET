"""
Playwright tests for v1 chart behavior
These tests establish baseline behavior before v2 migration
"""
import pytest
from playwright.sync_api import Page, expect
import time
import re

@pytest.fixture
def dashboard_url():
    """URL for the dashboard"""
    return "http://localhost:9095"

def test_charts_initial_load(page: Page, dashboard_url: str):
    """Test that both charts load on initial page load"""
    # Navigate to dashboard
    page.goto(dashboard_url)
    
    # Wait for charts to be visible
    recent_chart = page.locator("#recentChart")
    longterm_chart = page.locator("#longTermChart")
    
    # Verify both charts are visible
    expect(recent_chart).to_be_visible()
    expect(longterm_chart).to_be_visible()
    
    # Verify chart canvases are present
    recent_canvas = page.locator("#recentChart canvas")
    longterm_canvas = page.locator("#longTermChart canvas")
    
    expect(recent_canvas).to_be_visible()
    expect(longterm_canvas).to_be_visible()
    
    # Wait for data to load (charts should have content)
    page.wait_for_timeout(2000)  # Give charts time to render
    
    # Verify chart titles are present
    chart_titles = page.locator(".chart-container h3")
    expect(chart_titles).to_have_count(2)
    expect(chart_titles.nth(0)).to_contain_text("90-Day Balance History")
    expect(chart_titles.nth(1)).to_contain_text("3-Year Balance History")

def test_charts_client_selection(page: Page, dashboard_url: str):
    """Test that charts update when selecting a client"""
    page.goto(dashboard_url)
    
    # Wait for initial load
    page.wait_for_selector("#clientTable tbody tr")
    
    # Get initial chart state (capture screenshot for comparison)
    recent_chart = page.locator("#recentChart")
    initial_screenshot = recent_chart.screenshot()
    
    # Click on first client
    first_client = page.locator("#clientTable tbody tr").first
    first_client.click()
    
    # Wait for charts to update
    page.wait_for_timeout(1000)
    
    # Verify chart has updated (screenshot should be different)
    updated_screenshot = recent_chart.screenshot()
    assert initial_screenshot != updated_screenshot, "Chart should update after client selection"
    
    # Verify selection is visible
    expect(first_client).to_have_class(re.compile(r"selected"))

def test_charts_fund_selection(page: Page, dashboard_url: str):
    """Test that charts update when selecting a fund"""
    page.goto(dashboard_url)
    
    # Wait for initial load
    page.wait_for_selector("#fundTable tbody tr")
    
    # Click on first fund
    first_fund = page.locator("#fundTable tbody tr").first
    first_fund.click()
    
    # Wait for charts to update
    page.wait_for_timeout(1000)
    
    # Verify both charts are still visible
    expect(page.locator("#recentChart")).to_be_visible()
    expect(page.locator("#longTermChart")).to_be_visible()

def test_charts_multi_selection(page: Page, dashboard_url: str):
    """Test charts with multiple selections (client + fund)"""
    page.goto(dashboard_url)
    
    # Wait for tables to load
    page.wait_for_selector("#clientTable tbody tr")
    page.wait_for_selector("#fundTable tbody tr")
    
    # Select first client
    first_client = page.locator("#clientTable tbody tr").first
    first_client.click()
    
    # Select first fund
    first_fund = page.locator("#fundTable tbody tr").first
    first_fund.click()
    
    # Wait for charts to update
    page.wait_for_timeout(1000)
    
    # Verify both selections are active
    expect(first_client).to_have_class(re.compile(r"selected"))
    expect(first_fund).to_have_class(re.compile(r"selected"))
    
    # Verify charts are still visible
    expect(page.locator("#recentChart")).to_be_visible()
    expect(page.locator("#longTermChart")).to_be_visible()

def test_chart_date_interaction(page: Page, dashboard_url: str):
    """Test clicking on chart data points to filter by date"""
    page.goto(dashboard_url)
    
    # Wait for charts to load
    page.wait_for_selector("#recentChart canvas")
    page.wait_for_timeout(2000)  # Let charts render
    
    # Click on the recent chart (middle area)
    chart_canvas = page.locator("#recentChart canvas")
    chart_box = chart_canvas.bounding_box()
    
    if chart_box:
        # Click in the middle of the chart
        page.mouse.click(
            chart_box['x'] + chart_box['width'] / 2,
            chart_box['y'] + chart_box['height'] / 2
        )
        
        # Wait for potential data update
        page.wait_for_timeout(1000)
        
        # Verify filter indicator shows date selection
        filter_indicator = page.locator("#filterIndicator")
        expect(filter_indicator).to_be_visible()
        # Should contain date pattern (e.g., "2025-07-15")
        expect(filter_indicator).to_contain_text(re.compile(r"\d{4}-\d{2}-\d{2}"))

def test_chart_axes_labels(page: Page, dashboard_url: str):
    """Test that chart axes have proper labels and formatting"""
    page.goto(dashboard_url)
    
    # Wait for charts to render
    page.wait_for_timeout(2000)
    
    # Check for currency formatting in tooltips/legends
    # This is harder to test without interacting with the chart
    # For now, just verify charts rendered without errors
    
    # Check console for any chart-related errors
    console_logs = []
    page.on("console", lambda msg: console_logs.append(msg))
    
    # Re-navigate to capture any console errors
    page.reload()
    page.wait_for_timeout(2000)
    
    # Filter for error messages
    errors = [log for log in console_logs if log.type == "error"]
    chart_errors = [err for err in errors if "chart" in err.text.lower()]
    
    assert len(chart_errors) == 0, f"Chart errors found: {[err.text for err in chart_errors]}"

def test_chart_responsiveness(page: Page, dashboard_url: str):
    """Test that charts respond to window resize"""
    page.goto(dashboard_url)
    
    # Set initial viewport
    page.set_viewport_size({"width": 1200, "height": 800})
    page.wait_for_timeout(1000)
    
    # Get initial chart size
    recent_chart = page.locator("#recentChart")
    initial_box = recent_chart.bounding_box()
    
    # Resize viewport
    page.set_viewport_size({"width": 800, "height": 600})
    page.wait_for_timeout(1000)
    
    # Get new chart size
    resized_box = recent_chart.bounding_box()
    
    # Verify chart resized
    assert initial_box and resized_box, "Chart bounding boxes should exist"
    assert resized_box['width'] < initial_box['width'], "Chart should resize with viewport"

def test_chart_loading_states(page: Page, dashboard_url: str):
    """Test that charts show appropriate loading states"""
    # Intercept API calls to delay response
    def handle_route(route):
        # Delay chart data endpoints
        if "history" in route.request.url:
            time.sleep(1)  # Add 1 second delay
        route.continue_()
    
    page.route("**/api/**", handle_route)
    
    page.goto(dashboard_url)
    
    # Charts should be visible even while loading
    expect(page.locator("#recentChart")).to_be_visible()
    expect(page.locator("#longTermChart")).to_be_visible()
    
    # Wait for data to load
    page.wait_for_timeout(3000)
    
    # Verify charts rendered after loading
    expect(page.locator("#recentChart canvas")).to_be_visible()
    expect(page.locator("#longTermChart canvas")).to_be_visible()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])