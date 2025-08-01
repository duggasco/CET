"""Integration tests for /api/v2/dashboard endpoint."""
import requests
import json
from datetime import datetime, timedelta


BASE_URL = "http://localhost:9095"
V2_ENDPOINT = f"{BASE_URL}/api/v2/dashboard"


def test_basic_request():
    """Test basic request without filters."""
    response = requests.get(V2_ENDPOINT)
    assert response.status_code == 200
    
    data = response.json()
    assert "metadata" in data
    assert "client_balances" in data
    assert "fund_balances" in data
    assert "account_details" in data
    assert "charts" in data
    assert "kpi_metrics" in data
    
    # Check that we have data
    assert len(data["client_balances"]) > 0
    assert len(data["fund_balances"]) > 0
    assert data["kpi_metrics"]["total_aum"] > 0
    
    print("✓ Basic request test passed")


def test_client_filter():
    """Test filtering by client_id."""
    # First get a client ID
    response = requests.get(V2_ENDPOINT)
    data = response.json()
    client_id = data["client_balances"][0]["client_id"]
    client_name = data["client_balances"][0]["client_name"]
    
    # Now filter by this client
    response = requests.get(V2_ENDPOINT, params={"client_id": client_id})
    assert response.status_code == 200
    
    data = response.json()
    assert len(data["client_balances"]) == 1
    assert data["client_balances"][0]["client_id"] == client_id
    assert data["metadata"]["filters_applied"]["client_ids"] == [client_id]
    
    print(f"✓ Client filter test passed (filtered to {client_name})")


def test_text_filters():
    """Test text filters."""
    response = requests.get(V2_ENDPOINT, params={
        "client_name": "Capital",
        "fund_ticker": "Pri"
    })
    assert response.status_code == 200
    
    data = response.json()
    # Check that filters were applied
    assert data["metadata"]["filters_applied"]["text_filters"]["client_name"] == "Capital"
    assert data["metadata"]["filters_applied"]["text_filters"]["fund_ticker"] == "Pri"
    
    # Check that results match filters
    for client in data["client_balances"]:
        assert "Capital" in client["client_name"]
    
    for fund in data["fund_balances"]:
        assert fund["fund_ticker"].startswith("Pri")
    
    print("✓ Text filters test passed")


def test_multiple_filters():
    """Test combining multiple filter types."""
    # Get some test data first
    response = requests.get(V2_ENDPOINT)
    data = response.json()
    client_id = data["client_balances"][0]["client_id"]
    fund_name = data["fund_balances"][0]["fund_name"]
    
    # Apply multiple filters
    response = requests.get(V2_ENDPOINT, params={
        "client_id": client_id,
        "fund_name": fund_name
    })
    assert response.status_code == 200
    
    data = response.json()
    # Should have intersection of client and fund
    assert data["kpi_metrics"]["total_aum"] > 0
    assert len(data["account_details"]) > 0
    
    print("✓ Multiple filters test passed")


def test_date_filter():
    """Test filtering by date."""
    # Test with a date 30 days ago
    past_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    response = requests.get(V2_ENDPOINT, params={"date": past_date})
    assert response.status_code == 200
    
    data = response.json()
    assert data["metadata"]["as_of_date"] == past_date
    
    print(f"✓ Date filter test passed (as of {past_date})")


def test_invalid_date_format():
    """Test RFC 7807 error response for invalid date."""
    response = requests.get(V2_ENDPOINT, params={"date": "invalid-date"})
    assert response.status_code == 400
    
    error = response.json()
    assert error["type"] == "/errors/invalid-parameter"
    assert error["title"] == "Invalid Date Format"
    assert "invalid-date" in error["detail"]
    assert error["status"] == 400
    assert error["instance"] == "/api/v2/dashboard"
    
    print("✓ Invalid date error handling test passed")


def test_invalid_uuid_format():
    """Test RFC 7807 error response for invalid UUID."""
    response = requests.get(V2_ENDPOINT, params={"client_id": "not-a-uuid"})
    assert response.status_code == 400
    
    error = response.json()
    assert error["type"] == "/errors/invalid-parameter"
    assert error["title"] == "Invalid Client ID Format"
    assert "not-a-uuid" in error["detail"]
    assert error["status"] == 400
    assert error["instance"] == "/api/v2/dashboard"
    
    print("✓ Invalid UUID error handling test passed")


def test_qtd_ytd_consistency():
    """Test that QTD/YTD values are consistent across tables."""
    # Get data with a specific client and fund
    response = requests.get(V2_ENDPOINT)
    data = response.json()
    client_id = data["client_balances"][0]["client_id"]
    fund_name = data["fund_balances"][0]["fund_name"]
    
    # Filter by both
    response = requests.get(V2_ENDPOINT, params={
        "client_id": client_id,
        "fund_name": fund_name
    })
    data = response.json()
    
    # All tables should show the same QTD/YTD for the intersection
    client_qtd = data["client_balances"][0]["qtd_change"]
    client_ytd = data["client_balances"][0]["ytd_change"]
    fund_qtd = data["fund_balances"][0]["qtd_change"]
    fund_ytd = data["fund_balances"][0]["ytd_change"]
    
    # They should be equal (or both None)
    assert client_qtd == fund_qtd, f"QTD mismatch: client={client_qtd}, fund={fund_qtd}"
    assert client_ytd == fund_ytd, f"YTD mismatch: client={client_ytd}, fund={fund_ytd}"
    
    print("✓ QTD/YTD consistency test passed")


def test_chart_data():
    """Test that chart data is included and valid."""
    response = requests.get(V2_ENDPOINT)
    data = response.json()
    
    # Check 90-day chart
    assert len(data["charts"]["recent_history"]) > 0
    assert len(data["charts"]["recent_history"]) <= 91  # 90 days + today
    
    # Check 3-year chart
    assert len(data["charts"]["long_term_history"]) > 0
    assert len(data["charts"]["long_term_history"]) <= 1096  # ~3 years
    
    # Check data structure
    for point in data["charts"]["recent_history"]:
        assert "date" in point
        assert "balance" in point
        assert isinstance(point["balance"], (int, float))
    
    print("✓ Chart data test passed")


def run_all_tests():
    """Run all integration tests."""
    print("Running v2 API integration tests...\n")
    
    tests = [
        test_basic_request,
        test_client_filter,
        test_text_filters,
        test_multiple_filters,
        test_date_filter,
        test_invalid_date_format,
        test_invalid_uuid_format,
        test_qtd_ytd_consistency,
        test_chart_data
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} error: {e}")
            failed += 1
    
    print(f"\n{passed} tests passed, {failed} tests failed")
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)