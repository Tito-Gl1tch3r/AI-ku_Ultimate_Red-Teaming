#!/usr/bin/env bash
# Local development: Docker infra (Postgres + Redis) + npm dev server + worker (hot reload).

set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker not found. Install Docker or run Postgres/Redis yourself."
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose v2 required (docker compose)."
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Cannot connect to Docker. Start the daemon or add your user to the docker group."
  exit 1
fi

bash scripts/ensure-env.sh

echo -e "${CYAN}Checking and installing Node.js dependencies...${NC}"
npm install

echo -e "${CYAN}Starting Postgres and Redis...${NC}"
docker compose up -d postgres redis

bash scripts/wait-for-infra.sh

if ! npm run db:migrate >/dev/null 2>&1; then
  echo -e "${YELLOW}Running database setup (migrate + seed)...${NC}"
  npm run setup
else
  echo -e "${GREEN}Database migrations OK.${NC}"
fi

echo -e "${CYAN}Generating Prisma Client...${NC}"
npx prisma generate

BP=""
if [ -f .env ]; then
  BP=$(grep -E '^NEXT_PUBLIC_BASE_PATH=' .env | cut -d '=' -f 2- | tr -d '"' | tr -d "'" | tr -d ' ' || true)
fi

echo ""
echo -e "${GREEN}Infrastructure ready.${NC} Starting dev server and worker (Ctrl+C to stop)..."
echo -e "  App: ${YELLOW}http://localhost:3000${BP}${NC}"
echo ""

exec npm run dev:all
