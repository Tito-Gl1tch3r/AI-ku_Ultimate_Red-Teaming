#!/bin/bash
# Query OSV.dev API for known vulnerabilities
# Usage: ./check-osv.sh <ecosystem> <package-name> [version]
# Ecosystems: npm, PyPI, Go, crates.io, RubyGems, Packagist, Maven, NuGet

set -euo pipefail

ECOSYSTEM="${1:?Usage: check-osv.sh <ecosystem> <package-name> [version]}"
PACKAGE="${2:?Usage: check-osv.sh <ecosystem> <package-name> [version]}"
VERSION="${3:-}"

echo "[*] Searching OSV.dev for: $PACKAGE ($ECOSYSTEM)"

if [ -n "$VERSION" ]; then
    PAYLOAD="{\"package\":{\"name\":\"$PACKAGE\",\"ecosystem\":\"$ECOSYSTEM\"},\"version\":\"$VERSION\"}"
else
    PAYLOAD="{\"package\":{\"name\":\"$PACKAGE\",\"ecosystem\":\"$ECOSYSTEM\"}}"
fi

RESPONSE=$(curl -s -X POST "https://api.osv.dev/v1/query" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD")

VULNS=$(echo "$RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
vulns = data.get('vulns', [])
print(len(vulns))
" 2>/dev/null)

echo "[*] Known vulnerabilities: $VULNS"

if [ "$VULNS" -gt 0 ]; then
    echo ""
    echo "ID | Severity | Summary"
    echo "---|----------|--------"
    echo "$RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for v in data.get('vulns', []):
    vid = v.get('id', 'N/A')
    summary = v.get('summary', 'No summary')[:80]
    severity = 'N/A'
    for s in v.get('severity', []):
        severity = s.get('score', 'N/A')
    print(f'{vid} | {severity} | {summary}')
" 2>/dev/null
fi
