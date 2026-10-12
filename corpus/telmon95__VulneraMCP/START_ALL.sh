#!/bin/bash

# Start All Services Script
# Starts MCP Server, Dashboard, and verifies ZAP

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🚀 Starting All Bug Bounty MCP Services...${NC}"
echo ""

cd "$(dirname "$0")"

# Build first
echo -e "${BLUE}📦 Building TypeScript...${NC}"
npm run build
echo ""

# Stop existing services
echo -e "${BLUE}🛑 Stopping existing services...${NC}"
pkill -f "dashboard-server.js" 2>/dev/null || true
pkill -f "node dist/index.js" 2>/dev/null || true
sleep 2
echo ""

# Start MCP Server
echo -e "${BLUE}🔧 Starting MCP Server (Backend)...${NC}"
POSTGRES_PORT=5433 POSTGRES_USER=postgres nohup node dist/index.js > mcp-server.log 2>&1 &
MCP_PID=$!
sleep 3
if ps -p $MCP_PID > /dev/null 2>&1; then
    echo -e "${GREEN}   ✅ MCP Server started (PID: $MCP_PID)${NC}"
else
    echo -e "${YELLOW}   ⚠️  MCP Server may have issues. Check mcp-server.log${NC}"
fi
echo ""

# Start Dashboard
echo -e "${BLUE}📊 Starting Dashboard Server (Frontend)...${NC}"
POSTGRES_PORT=5433 POSTGRES_USER=postgres POSTGRES_DB=bugbounty nohup node dashboard-server.js > dashboard-server.log 2>&1 &
DASHBOARD_PID=$!
sleep 4
if ps -p $DASHBOARD_PID > /dev/null 2>&1; then
    echo -e "${GREEN}   ✅ Dashboard started (PID: $DASHBOARD_PID)${NC}"
else
    echo -e "${YELLOW}   ⚠️  Dashboard may have issues. Check dashboard-server.log${NC}"
fi
echo ""

# Check ZAP
echo -e "${BLUE}🕷️  Checking ZAP Proxy...${NC}"
if docker ps | grep -q zap; then
    echo -e "${GREEN}   ✅ ZAP Proxy running on http://localhost:8081${NC}"
else
    echo -e "${YELLOW}   ⚠️  ZAP Proxy not running${NC}"
    echo -e "${BLUE}   Start with: docker run -d --name zap-proxy -p 8081:8080 zaproxy/zap-stable zap.sh -daemon -host 0.0.0.0 -port 8080 -config api.disablekey=true${NC}"
fi
echo ""

# Verify services
echo -e "${BLUE}🔍 Verifying services...${NC}"
sleep 3

if curl -s --max-time 3 http://localhost:3000/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}   ✅ Dashboard responding${NC}"
else
    echo -e "${YELLOW}   ⏳ Dashboard still starting...${NC}"
fi

echo ""
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ All Services Started!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}🌐 Dashboard:${NC} http://localhost:3000"
echo -e "${BLUE}🔌 MCP Server:${NC} Running (check mcp-server.log)"
echo -e "${BLUE}🕷️  ZAP Proxy:${NC} http://localhost:8081"
echo ""
echo -e "${BLUE}📝 View logs:${NC}"
echo "   tail -f mcp-server.log"
echo "   tail -f dashboard-server.log"
echo ""



