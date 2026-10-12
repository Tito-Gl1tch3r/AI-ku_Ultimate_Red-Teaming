#!/bin/bash
# Get npm package statistics (downloads, version, maintainers)
# Usage: ./npm-stats.sh <package-name>

set -euo pipefail

PACKAGE="${1:?Usage: npm-stats.sh <package-name>}"

echo "[*] Fetching npm stats for: $PACKAGE"

# Package metadata
META=$(curl -s "https://registry.npmjs.org/$PACKAGE")
LATEST=$(echo "$META" | python3 -c "import sys,json; print(json.load(sys.stdin).get('dist-tags',{}).get('latest','N/A'))" 2>/dev/null)
echo "[*] Latest version: $LATEST"

# Weekly downloads
DOWNLOADS=$(curl -s "https://api.npmjs.org/downloads/point/last-week/$PACKAGE")
COUNT=$(echo "$DOWNLOADS" | python3 -c "import sys,json; print(json.load(sys.stdin).get('downloads', 0))" 2>/dev/null)
echo "[*] Weekly downloads: $COUNT"

# GitHub repo
REPO=$(echo "$META" | python3 -c "
import sys, json
data = json.load(sys.stdin)
repo = data.get('repository', {})
if isinstance(repo, dict):
    url = repo.get('url', 'N/A')
else:
    url = str(repo)
print(url.replace('git+', '').replace('git://', 'https://').replace('.git', ''))
" 2>/dev/null)
echo "[*] Repository: $REPO"

# Maintainers
echo "[*] Maintainers:"
echo "$META" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for m in data.get('maintainers', []):
    print(f'  - {m.get(\"name\", \"N/A\")}')
" 2>/dev/null
