#!/usr/bin/env bash
# Start only Postgres + Redis for local hot-reload development (npm run dev:all).

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
  echo -e "${RED}Docker not found.${NC} Install Docker first."
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo -e "${RED}Docker Compose v2 not found.${NC} Install docker-compose-plugin."
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo -e "${RED}Cannot connect to Docker daemon.${NC}"
  echo "Try: sudo systemctl start docker"
  echo "Or add your user to the docker group and log in again."
  exit 1
fi

bash scripts/ensure-env.sh

echo -e "${CYAN}Starting infrastructure (PostgreSQL + Redis)...${NC}"
docker compose up -d postgres redis

bash scripts/wait-for-infra.sh

echo ""
echo -e "${GREEN}Infrastructure is up.${NC}"
echo ""
echo -e "${BLUE}Next steps (hot reload):${NC}"
echo "  1. Ensure .env has DATABASE_URL and REDIS_URL pointing to localhost (see .env.example)"
echo "  2. npm install   (if not done)"
echo "  3. npm run setup (first time only — migrate + seed)"
echo "  4. npm run dev:all"
echo ""
echo -e "  Or run everything in one command: ${YELLOW}npm run dev:local${NC}"
echo ""
echo -e "  Postgres: localhost:${POSTGRES_PORT:-5432}  |  Redis: localhost:${REDIS_PORT:-6379}"
echo ""
