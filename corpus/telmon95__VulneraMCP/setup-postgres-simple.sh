#!/bin/bash

# Simple PostgreSQL setup script
# This works with local PostgreSQL (not Docker)

echo "🔧 Setting up PostgreSQL for Bug Bounty MCP Dashboard"
echo ""

# Check if PostgreSQL is running locally
if ! pg_isready -h localhost > /dev/null 2>&1; then
    echo "⚠️  PostgreSQL doesn't seem to be running on localhost"
    echo "   Starting PostgreSQL..."
    brew services start postgresql@14 2>/dev/null || brew services start postgresql 2>/dev/null
    sleep 3
fi

# Option 1: Use trust authentication (no password)
echo "📝 Option 1: Setting up with trust authentication (no password required)"
echo "   This allows connection without password for local connections"
echo ""

# Check if we can connect without password
if psql -h localhost -U $(whoami) -d postgres -c "SELECT 1;" > /dev/null 2>&1; then
    echo "✅ Can connect without password"
    echo ""
    echo "Creating database..."
    createdb bugbounty 2>/dev/null || echo "Database might already exist"
    
    echo "Initializing tables..."
    POSTGRES_HOST=localhost POSTGRES_USER=$(whoami) POSTGRES_DB=bugbounty POSTGRES_PASSWORD="" node init-db.js
    
    echo ""
    echo "✅ Setup complete! Starting dashboard..."
    pkill -f dashboard-server.js 2>/dev/null
    sleep 1
    POSTGRES_HOST=localhost POSTGRES_USER=$(whoami) POSTGRES_DB=bugbounty POSTGRES_PASSWORD="" nohup node dashboard-server.js > dashboard-server.log 2>&1 &
    
    echo "✅ Dashboard started!"
    echo "🌐 Open: http://localhost:3000"
    exit 0
fi

# Option 2: Use postgres user with password
echo "📝 Option 2: Need to set password for postgres user"
echo ""
echo "To fix this, run one of these commands:"
echo ""
echo "A) Set password for postgres user:"
echo "   psql -U postgres -c \"ALTER USER postgres PASSWORD 'bugbounty123';\""
echo ""
echo "B) Or create a new user:"
echo "   psql -U postgres -c \"CREATE USER bugbounty WITH PASSWORD 'bugbounty123';\""
echo "   psql -U postgres -c \"CREATE DATABASE bugbounty OWNER bugbounty;\""
echo ""
echo "Then run:"
echo "   POSTGRES_PASSWORD=bugbounty123 ./run-dashboard.sh"
echo ""



