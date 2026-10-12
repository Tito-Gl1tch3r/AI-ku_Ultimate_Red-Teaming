#!/usr/bin/env bash
# Tengu Docker Entrypoint
set -euo pipefail

# ── Colors ─────────────────────────────────────────────────────────────────────
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# ── Banner ──────────────────────────────────────────────────────────────────────
echo -e "${BLUE}"
echo "  ████████╗███████╗███╗   ██╗ ██████╗ ██╗   ██╗"
echo "     ██╔══╝██╔════╝████╗  ██║██╔════╝ ██║   ██║"
echo "     ██║   █████╗  ██╔██╗ ██║██║  ███╗██║   ██║"
echo "     ██║   ██╔══╝  ██║╚██╗██║██║   ██║██║   ██║"
echo "     ██║   ███████╗██║ ╚████║╚██████╔╝╚██████╔╝"
echo "     ╚═╝   ╚══════╝╚═╝  ╚═══╝ ╚═════╝  ╚═════╝"
echo "  Pentesting MCP Server — Docker"
echo -e "${NC}"

# ── Ensure required directories exist ──────────────────────────────────────────
mkdir -p /app/logs /app/output/.tengu

# ── Override allowed_hosts via environment variable ────────────────────────────
# TENGU_ALLOWED_HOSTS="192.168.1.0/24,10.0.0.0/8" overrides tengu.toml values.
# The config.py load_config() reads this env var automatically.
if [[ -n "${TENGU_ALLOWED_HOSTS:-}" ]]; then
    echo -e "${YELLOW}[config]${NC} TENGU_ALLOWED_HOSTS override: ${TENGU_ALLOWED_HOSTS}"
fi

# ── Update Nuclei templates (best-effort, skip if offline) ─────────────────────
if command -v nuclei &>/dev/null; then
    echo -e "${BLUE}[nuclei]${NC} Updating templates..."
    nuclei -update-templates -silent 2>/dev/null && \
        echo -e "${GREEN}[nuclei]${NC} Templates updated" || \
        echo -e "${YELLOW}[nuclei]${NC} Template update skipped (offline?)"
fi

# ── Quick tool health check ─────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}[tools]${NC} Checking critical tools..."
TOOLS_OK=true
for tool in nmap nuclei ffuf sqlmap; do
    if command -v "$tool" &>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $tool"
    else
        echo -e "  ${RED}✗${NC} $tool (not found — some tools may be unavailable)"
        TOOLS_OK=false
    fi
done

if [[ "$TOOLS_OK" == "true" ]]; then
    echo -e "${GREEN}[tools]${NC} All critical tools present"
else
    echo -e "${YELLOW}[tools]${NC} Some tools missing — build with TENGU_TIER=core or full"
fi

echo ""
echo -e "${GREEN}[tengu]${NC} Starting MCP server on port ${TENGU_PORT:-8000}..."
echo ""

# ── Launch Tengu ────────────────────────────────────────────────────────────────
exec uv run tengu "$@"
