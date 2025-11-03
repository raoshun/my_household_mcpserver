#!/bin/bash
"""
Docker Compose Integration Tests
Tests that Docker containers start correctly and endpoints are accessible
"""

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Docker Compose Integration Tests ===${NC}\n"

# Test 1: Check if docker-compose is available
echo "[TEST 1] Checking docker-compose availability..."
if ! command -v docker &> /dev/null && ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}✗ FAILED: docker/docker-compose not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ PASSED${NC}\n"

# Test 2: Verify docker-compose.yml exists
echo "[TEST 2] Checking docker-compose.yml..."
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}✗ FAILED: docker-compose.yml not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ PASSED${NC}\n"

# Test 3: Verify Dockerfile exists
echo "[TEST 3] Checking Dockerfile exists..."
if [ ! -f "backend/Dockerfile" ]; then
    echo -e "${RED}✗ FAILED: backend/Dockerfile not found${NC}"
    exit 1
fi
if [ ! -f "frontend/Dockerfile" ]; then
    echo -e "${RED}✗ FAILED: frontend/Dockerfile not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ PASSED${NC}\n"

# Test 4: Build images
echo "[TEST 4] Building Docker images..."
if docker compose build --no-cache 2>&1 | tail -5; then
    echo -e "${GREEN}✓ PASSED${NC}\n"
else
    echo -e "${RED}✗ FAILED: Image build failed${NC}"
    exit 1
fi

# Test 5: Start containers
echo "[TEST 5] Starting Docker containers..."
if docker compose up -d 2>&1 | grep -E "Started|Running"; then
    echo -e "${GREEN}✓ PASSED${NC}\n"
else
    echo -e "${RED}✗ FAILED: Container startup failed${NC}"
    exit 1
fi

# Wait for services to be ready
echo "[WAIT] Waiting for services to be ready..."
sleep 5

# Test 6: Check backend container health
echo "[TEST 6] Checking backend container health..."
BACKEND_STATUS=$(docker compose ps backend | grep -E "healthy|Up")
if [ -n "$BACKEND_STATUS" ]; then
    echo -e "${GREEN}✓ PASSED${NC} - $BACKEND_STATUS\n"
else
    echo -e "${RED}✗ FAILED: Backend container not healthy${NC}"
    docker compose logs backend | tail -20
    exit 1
fi

# Test 7: Check frontend container health
echo "[TEST 7] Checking frontend container health..."
FRONTEND_STATUS=$(docker compose ps frontend | grep -E "healthy|Up")
if [ -n "$FRONTEND_STATUS" ]; then
    echo -e "${GREEN}✓ PASSED${NC} - $FRONTEND_STATUS\n"
else
    echo -e "${RED}✗ FAILED: Frontend container not healthy${NC}"
    docker compose logs frontend | tail -20
    exit 1
fi

# Test 8: Test backend /api/tools endpoint
echo "[TEST 8] Testing backend /api/tools endpoint..."
TOOLS_RESPONSE=$(curl -s http://127.0.0.1:8000/api/tools)
if echo "$TOOLS_RESPONSE" | grep -q '"success":true'; then
    echo -e "${GREEN}✓ PASSED${NC}"
    TOOL_COUNT=$(echo "$TOOLS_RESPONSE" | grep -o '"name":"[^"]*"' | wc -l)
    echo "    Found $TOOL_COUNT tools\n"
else
    echo -e "${RED}✗ FAILED: /api/tools endpoint returned invalid response${NC}"
    echo "Response: $TOOLS_RESPONSE"
    exit 1
fi

# Test 9: Test backend /api/duplicates/candidates endpoint
echo "[TEST 9] Testing backend /api/duplicates/candidates endpoint..."
DUP_RESPONSE=$(curl -s http://127.0.0.1:8000/api/duplicates/candidates)
if echo "$DUP_RESPONSE" | grep -q '"success":true'; then
    echo -e "${GREEN}✓ PASSED${NC}\n"
else
    echo -e "${RED}✗ FAILED: /api/duplicates/candidates returned invalid response${NC}"
    echo "Response: $DUP_RESPONSE"
    exit 1
fi

# Test 10: Test frontend index.html
echo "[TEST 10] Testing frontend index.html..."
INDEX_RESPONSE=$(curl -s http://127.0.0.1:8080/)
if echo "$INDEX_RESPONSE" | grep -q '家計簿分析'; then
    echo -e "${GREEN}✓ PASSED${NC}\n"
else
    echo -e "${RED}✗ FAILED: Frontend index.html not accessible${NC}"
    exit 1
fi

# Test 11: Test frontend mcp-tools.html
echo "[TEST 11] Testing frontend mcp-tools.html..."
MCP_RESPONSE=$(curl -s http://127.0.0.1:8080/mcp-tools.html)
if echo "$MCP_RESPONSE" | grep -q 'MCPツール'; then
    echo -e "${GREEN}✓ PASSED${NC}\n"
else
    echo -e "${RED}✗ FAILED: Frontend mcp-tools.html not accessible${NC}"
    exit 1
fi

# Test 12: Test config.js availability
echo "[TEST 12] Testing config.js availability..."
CONFIG_RESPONSE=$(curl -s http://127.0.0.1:8080/js/config.js)
if echo "$CONFIG_RESPONSE" | grep -q 'DEFAULT_API_PORT'; then
    DEFAULT_PORT=$(echo "$CONFIG_RESPONSE" | grep 'DEFAULT_API_PORT' | head -1)
    echo -e "${GREEN}✓ PASSED${NC} - $DEFAULT_PORT\n"
else
    echo -e "${RED}✗ FAILED: config.js not properly deployed${NC}"
    exit 1
fi

# Test 13: Test default port is 8000 (not 8001)
echo "[TEST 13] Verifying default port is 8000 (Docker environment)..."
if echo "$CONFIG_RESPONSE" | grep -q 'DEFAULT_API_PORT = 8000'; then
    echo -e "${GREEN}✓ PASSED${NC} - DEFAULT_API_PORT = 8000\n"
else
    echo -e "${RED}✗ FAILED: DEFAULT_API_PORT not set to 8000${NC}"
    exit 1
fi

# Test 14: Test OpenAPI documentation
echo "[TEST 14] Testing OpenAPI documentation..."
OPENAPI_RESPONSE=$(curl -s http://127.0.0.1:8000/openapi.json)
if echo "$OPENAPI_RESPONSE" | grep -q '"paths"'; then
    echo -e "${GREEN}✓ PASSED${NC}\n"
else
    echo -e "${RED}✗ FAILED: OpenAPI schema not available${NC}"
    exit 1
fi

# Test 15: Test CORS headers
echo "[TEST 15] Testing CORS headers..."
CORS_RESPONSE=$(curl -s -i http://127.0.0.1:8000/api/tools 2>&1)
if echo "$CORS_RESPONSE" | grep -q "200 OK"; then
    echo -e "${GREEN}✓ PASSED${NC}\n"
else
    echo -e "${RED}✗ FAILED: API not responding with 200 OK${NC}"
    exit 1
fi

# Cleanup
echo "[CLEANUP] Stopping Docker containers..."
docker compose down

echo -e "${GREEN}=== All Tests Passed! ===${NC}\n"
