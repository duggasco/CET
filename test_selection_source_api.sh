#!/bin/bash

echo "=== Testing Multi-Selection Bug Fix - selection_source parameter ==="
echo ""

# Test 1: Single client selection with selection_source
echo "--- Test 1: Single client selection with selection_source=client ---"
echo "Request: /api/v2/dashboard?client_ids=550e8400-e29b-41d4-a716-446655440001&selection_source=client"
curl -s "http://localhost:9097/api/v2/dashboard?client_ids=550e8400-e29b-41d4-a716-446655440001&selection_source=client" | python3 -m json.tool | head -20
echo ""

# Test 2: Multiple client selection (no selection_source)
echo "--- Test 2: Multiple client selection (no selection_source) ---"
echo "Request: /api/v2/dashboard?client_ids=550e8400-e29b-41d4-a716-446655440001,550e8400-e29b-41d4-a716-446655440002"
curl -s "http://localhost:9097/api/v2/dashboard?client_ids=550e8400-e29b-41d4-a716-446655440001,550e8400-e29b-41d4-a716-446655440002" | python3 -m json.tool | head -20
echo ""

# Test 3: Check if backend properly handles selection_source
echo "--- Test 3: Verify selection_source parameter is accepted ---"
response=$(curl -s -w "\n%{http_code}" "http://localhost:9097/api/v2/dashboard?fund_names=Money%20Market%20Fund&selection_source=fund")
http_code=$(echo "$response" | tail -n1)
echo "HTTP Status Code: $http_code"

if [ "$http_code" = "200" ]; then
    echo "✅ Backend accepts selection_source parameter"
else
    echo "❌ Backend rejected selection_source parameter"
fi

# Test 4: Check old /api/data endpoint
echo ""
echo "--- Test 4: Old /api/data endpoint with selection_source ---"
echo "Request: /api/data?client_ids=550e8400-e29b-41d4-a716-446655440001&selection_source=client"
curl -s "http://localhost:9095/api/data?client_ids=550e8400-e29b-41d4-a716-446655440001&selection_source=client" | python3 -m json.tool | grep -E "(client_balances|fund_balances)" | head -10
echo ""

echo "=== Summary ==="
echo "The selection_source parameter should be sent when:"
echo "1. Only ONE table has selections (clients OR funds OR accounts)"
echo "2. It should NOT be sent when multiple tables have selections"
echo "3. The backend should use this to exclude filters for the source table"
echo ""
echo "This ensures tables show ALL items with selections highlighted (Tableau-like behavior)"