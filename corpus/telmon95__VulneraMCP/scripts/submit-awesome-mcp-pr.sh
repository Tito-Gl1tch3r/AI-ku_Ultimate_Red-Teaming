#!/usr/bin/env bash
set -euo pipefail

REPO="punkpeye/awesome-mcp-servers"
ENTRY_FILE="$(cd "$(dirname "$0")" && pwd)/awesome-mcp-pr-entry.txt"
ANCHOR='- [securityfortech/secops-mcp]'
WORKDIR="${TMPDIR:-/tmp}/awesome-mcp-servers-pr-$$"

if ! command -v gh >/dev/null 2>&1; then
  if [[ -x /opt/homebrew/bin/gh ]]; then
    GH=/opt/homebrew/bin/gh
  elif [[ -x /usr/local/bin/gh ]]; then
    GH=/usr/local/bin/gh
  else
    echo "Install GitHub CLI: https://cli.github.com/"
    exit 1
  fi
else
  GH=gh
fi

if ! "$GH" auth status >/dev/null 2>&1; then
  echo "Run: gh auth login"
  exit 1
fi

if [[ ! -f "$ENTRY_FILE" ]]; then
  echo "Missing entry file: $ENTRY_FILE"
  exit 1
fi

ENTRY_LINE="$(tr -d '\r' < "$ENTRY_FILE")"

rm -rf "$WORKDIR"
mkdir -p "$WORKDIR"
cd "$WORKDIR"

"$GH" repo fork "$REPO" --clone --default-branch-only
cd awesome-mcp-servers

if rg -F "telmon95/VulneraMCP" README.md >/dev/null 2>&1; then
  echo "VulneraMCP is already listed in README.md"
  exit 0
fi

python3 - "$ANCHOR" "$ENTRY_LINE" <<'PY'
import sys
from pathlib import Path

anchor = sys.argv[1]
entry = sys.argv[2]
readme = Path("README.md")
text = readme.read_text(encoding="utf-8")

if entry in text:
    raise SystemExit(0)

if anchor not in text:
    raise SystemExit(f"Anchor not found in README.md: {anchor}")

updated = text.replace(anchor, f"{anchor}\n{entry}", 1)
readme.write_text(updated, encoding="utf-8")
PY

git checkout -b add-vulneramcp
git add README.md
git commit -m "Add VulneraMCP bug bounty security server"

git push -u origin add-vulneramcp

"$GH" pr create \
  --repo "$REPO" \
  --head "$("$GH" api user --jq .login):add-vulneramcp" \
  --title "Add VulneraMCP - AI bug bounty MCP server" \
  --body "$(cat <<'EOF'
## Summary
- Adds [VulneraMCP](https://github.com/telmon95/VulneraMCP) to the Security section
- Includes Glama listing and score badge as required

## Server
- **Repo:** https://github.com/telmon95/VulneraMCP
- **Glama:** https://glama.ai/mcp/servers/telmon95/VulneraMCP
- **Demo:** https://youtu.be/wlUvBVNyh74

## Category
Security — bug bounty hunting, recon, vulnerability testing, ZAP integration, graph analysis
EOF
)"

echo "PR created successfully."
