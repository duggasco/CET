#!/bin/bash

echo "=== Testing Docker Setup for CET Phase 3 ==="
echo

# Function to test endpoint
test_endpoint() {
    local name=$1
    local url=$2
    local expected_flag=$3
    
    echo "Testing $name at $url..."
    
    # Check if server is running
    if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "200"; then
        echo "✅ Server is running"
        
        # Check feature flag
        response=$(curl -s "$url")
        if echo "$response" | grep -q "window.featureFlags = {"; then
            echo "✅ Feature flags are injected"
            
            # Check specific flag value
            if echo "$response" | grep -q "\"useV2DashboardApi\":$expected_flag"; then
                echo "✅ useV2DashboardApi is set to $expected_flag"
            else
                echo "❌ useV2DashboardApi is not set to $expected_flag"
            fi
        else
            echo "❌ Feature flags not found in response"
        fi
    else
        echo "❌ Server is not responding"
    fi
    echo
}

# Build Docker image first
echo "Building Docker image..."
docker build -t cet-app . || { echo "❌ Docker build failed"; exit 1; }
echo "✅ Docker image built successfully"
echo

# Check if containers are already running
if docker compose ps | grep -q "Up"; then
    echo "Stopping existing containers..."
    docker compose down
fi

# Start containers
echo "Starting Docker containers..."
docker compose up -d || { echo "❌ Docker compose failed"; exit 1; }

# Wait for services to start
echo "Waiting for services to start..."
sleep 10

# Test each instance
echo "=== Testing Individual Instances ==="
test_endpoint "Main App (Feature Flags)" "http://localhost:9095" "false"
test_endpoint "V1-only Instance" "http://localhost:9096" "false"
test_endpoint "V2-only Instance" "http://localhost:9097" "true"

# Test nginx routing
echo "=== Testing Nginx Routing ==="
test_endpoint "Nginx Main Route" "http://localhost:80" "false"
test_endpoint "Nginx V1 Route" "http://localhost/v1/" "false"
test_endpoint "Nginx V2 Route" "http://localhost/v2/" "true"

# Test A/B routing
echo "=== Testing A/B Routing ==="
echo "Making 10 requests to /ab/ endpoint to test distribution..."
v1_count=0
v2_count=0

for i in {1..10}; do
    response_header=$(curl -s -I "http://localhost/ab/")
    if echo "$response_header" | grep -q "X-AB-Test-Group: v1_backend"; then
        ((v1_count++))
    elif echo "$response_header" | grep -q "X-AB-Test-Group: v2_backend"; then
        ((v2_count++))
    fi
done

echo "V1 backend: $v1_count requests (expected ~9)"
echo "V2 backend: $v2_count requests (expected ~1)"
echo

# Test API endpoints
echo "=== Testing API Endpoints ==="
echo "Testing v1 API endpoint..."
if curl -s "http://localhost:9095/api/overview" | grep -q "client_balances"; then
    echo "✅ V1 API is working"
else
    echo "❌ V1 API is not responding correctly"
fi

echo "Testing v2 API endpoint..."
if curl -s "http://localhost:9095/api/v2/dashboard" | grep -q "result"; then
    echo "✅ V2 API is working"
else
    echo "❌ V2 API is not responding correctly"
fi

echo
echo "=== Docker Logs (last 10 lines) ==="
docker compose logs --tail=10 app

echo
echo "=== Test Complete ==="
echo "To stop containers: docker compose down"
echo "To view logs: docker compose logs -f [service-name]"
echo "To access containers: docker exec -it cet-app bash"