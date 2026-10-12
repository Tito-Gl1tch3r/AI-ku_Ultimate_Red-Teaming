#!/bin/bash
# Quick dashboard test script

echo "🧪 Testing Dashboard Server..."
echo ""

# Test health endpoint
echo "1️⃣  Testing health endpoint..."
HEALTH=$(curl -s --max-time 3 http://localhost:3000/api/health)
if [ $? -eq 0 ]; then
    echo "   ✅ Health endpoint responding"
    echo "   Response: $HEALTH"
else
    echo "   ❌ Health endpoint not responding"
fi

echo ""
echo "2️⃣  Testing dashboard page..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 http://localhost:3000/)
if [ "$STATUS" = "200" ]; then
    echo "   ✅ Dashboard page accessible (HTTP $STATUS)"
else
    echo "   ❌ Dashboard page returned HTTP $STATUS"
fi

echo ""
echo "3️⃣  Checking process..."
if pgrep -f "dashboard-server.js" > /dev/null; then
    echo "   ✅ Dashboard server process is running"
    echo "   PID: $(pgrep -f dashboard-server.js)"
else
    echo "   ❌ Dashboard server process not found"
fi

echo ""
echo "🌐 Open in browser: http://localhost:3000"
echo ""



