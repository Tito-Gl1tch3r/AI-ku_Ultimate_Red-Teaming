#!/usr/bin/env bash
# Full stack in Docker: Postgres, Redis, migrate/seed, Next.js app, scan worker.

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo -e "${RED}Docker not found.${NC}"
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo -e "${RED}Docker Compose v2 not found.${NC}"
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo -e "${RED}Cannot connect to Docker daemon.${NC}"
  exit 1
fi

bash scripts/ensure-env.sh

if grep -q 'REPLACE_ME_BASE64_32_BYTES' .env 2>/dev/null; then
  echo -e "${YELLOW}APP_ENCRYPTION_KEY is still a placeholder in .env.${NC}"
  if command -v openssl >/dev/null 2>&1; then
    KEY="$(openssl rand -base64 32)"
    sed -i "s|APP_ENCRYPTION_KEY=\"REPLACE_ME_BASE64_32_BYTES\"|APP_ENCRYPTION_KEY=\"${KEY}\"|" .env
    echo -e "${GREEN}Generated APP_ENCRYPTION_KEY in .env${NC}"
  else
    echo "Set APP_ENCRYPTION_KEY in .env before using encrypted API keys."
  fi
fi

echo -e "${CYAN}Building and starting full SCOPTIX stack...${NC}"
docker compose --profile full up -d --build

echo ""
echo -e "${GREEN}Stack started.${NC}"
sleep 2

if [ -f ./docker-status.sh ]; then
  ./docker-status.sh
else
  docker compose --profile full ps
fi
