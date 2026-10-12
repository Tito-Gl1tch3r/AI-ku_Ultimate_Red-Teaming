#!/usr/bin/env bash
set -euo pipefail

# Setup local test environment for recon script testing
# This creates multiple web servers to simulate a real target

echo "🐳 Setting up local test environment..."
echo

# Clean up any existing containers
echo "Cleaning up old containers..."
docker rm -f test-main test-api test-admin test-blog 2>/dev/null || true
echo

# Create a custom network
echo "Creating Docker network..."
docker network create test-network 2>/dev/null || true
echo

# Start multiple web servers on different ports
echo "Starting test web servers..."

# Main site
docker run -d --name test-main \
  --network test-network \
  -p 8080:80 \
  nginx:alpine
echo "  ✓ Main site: http://localhost:8080"

# API endpoint
docker run -d --name test-api \
  --network test-network \
  -p 8081:80 \
  nginx:alpine
echo "  ✓ API site: http://localhost:8081"

# Admin panel
docker run -d --name test-admin \
  --network test-network \
  -p 8082:80 \
  nginx:alpine
echo "  ✓ Admin site: http://localhost:8082"

# Blog
docker run -d --name test-blog \
  --network test-network \
  -p 8083:80 \
  nginx:alpine
echo "  ✓ Blog site: http://localhost:8083"

echo
echo "Adding entries to /etc/hosts..."
echo "You'll need to enter your password:"
sudo bash -c 'cat >> /etc/hosts << EOF

# Recon test environment (added by setup-local-test.sh)
127.0.0.1 test.local
127.0.0.1 www.test.local
127.0.0.1 api.test.local
127.0.0.1 admin.test.local
127.0.0.1 blog.test.local
127.0.0.1 dev.test.local
127.0.0.1 staging.test.local
EOF'

echo
echo "✅ Setup complete!"
echo
echo "Test the sites:"
echo "  curl http://localhost:8080"
echo "  curl http://test.local:8080"
echo
echo "Now you can test your recon script:"
echo "  ./recon-one.sh -d test.local -t 12 -j 4"
echo
echo "⚠️  Note: subfinder won't find these subdomains (they're not real DNS)"
echo "   but httpx, nuclei, and other tools will work on the URLs"
echo
echo "To clean up later, run:"
echo "  docker rm -f test-main test-api test-admin test-blog"
echo "  docker network rm test-network"
echo "  sudo sed -i '/# Recon test environment/,+7d' /etc/hosts"
