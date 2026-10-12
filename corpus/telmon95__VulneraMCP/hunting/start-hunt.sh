#!/bin/bash

# Social Deal Bug Hunting - Complete Workflow
# Respects rate limits (2 req/sec) and saves all findings to database

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

cd "$(dirname "$0")"
cd ..

echo -e "${BLUE}🎯 Starting Social Deal Bug Hunt${NC}"
echo -e "${BLUE}Rate Limit: 2 requests/second${NC}"
echo ""

# Ensure services are running
echo -e "${BLUE}📋 Checking services...${NC}"
if ! curl -s --max-time 2 http://localhost:3000/api/health > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Dashboard not running. Starting...${NC}"
    POSTGRES_PORT=5433 POSTGRES_USER=postgres POSTGRES_DB=bugbounty \
        nohup node dashboard-server.js > dashboard-server.log 2>&1 &
    sleep 3
fi

if ! ps aux | grep "node dist/index.js" | grep -v grep > /dev/null; then
    echo -e "${YELLOW}⚠️  MCP Server not running. Starting...${NC}"
    POSTGRES_PORT=5433 POSTGRES_USER=postgres nohup node dist/index.js > mcp-server.log 2>&1 &
    sleep 3
fi

echo -e "${GREEN}✅ Services ready${NC}"
echo ""

# Run reconnaissance
echo -e "${BLUE}🔍 Step 1: Initial Reconnaissance${NC}"
cd hunting
POSTGRES_PORT=5433 POSTGRES_USER=postgres node socialdeal-recon.js

echo ""
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Initial Reconnaissance Complete${NC}"
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}📊 Next Steps:${NC}"
echo "  1. View findings in dashboard: http://localhost:3000"
echo "  2. Use MCP tools for deeper testing:"
echo "     - recon.subfinder on socialdeal.nl"
echo "     - security.test_xss on discovered endpoints"
echo "     - zap.start_spider on www.socialdeal.nl"
echo ""
echo -e "${BLUE}💾 All findings saved to PostgreSQL database${NC}"
echo ""


