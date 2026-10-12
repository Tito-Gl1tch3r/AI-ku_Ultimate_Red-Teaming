#!/usr/bin/env bash
set -euo pipefail

# find-cve-agent installer
# Copies plugin files into the current project's .claude/ directory

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${1:-.}"

echo "=== find-cve-agent installer ==="
echo ""

# Resolve target directory
TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"
CLAUDE_DIR="$TARGET_DIR/.claude"

echo "Installing to: $TARGET_DIR"
echo ""

# Check required tools
MISSING_TOOLS=()
for tool in git gh python3 node curl; do
    if ! command -v "$tool" &>/dev/null; then
        MISSING_TOOLS+=("$tool")
    fi
done

if [ ${#MISSING_TOOLS[@]} -gt 0 ]; then
    echo "WARNING: Missing required tools: ${MISSING_TOOLS[*]}"
    echo "The plugin will install but some features may not work."
    echo ""
fi

# Create directory structure
echo "Creating directory structure..."
mkdir -p "$CLAUDE_DIR/skills/find-cve"
mkdir -p "$CLAUDE_DIR/commands"
mkdir -p "$CLAUDE_DIR/agents"
mkdir -p "$TARGET_DIR/targets"

# Copy CLAUDE.md to project root (merge if exists)
if [ -f "$TARGET_DIR/CLAUDE.md" ]; then
    echo "CLAUDE.md already exists. Appending find-cve-agent instructions..."
    echo "" >> "$TARGET_DIR/CLAUDE.md"
    echo "---" >> "$TARGET_DIR/CLAUDE.md"
    echo "" >> "$TARGET_DIR/CLAUDE.md"
    echo "# find-cve-agent plugin loaded. See .claude/skills/find-cve/CLAUDE.md for full instructions." >> "$TARGET_DIR/CLAUDE.md"
    cp "$SCRIPT_DIR/CLAUDE.md" "$CLAUDE_DIR/skills/find-cve/CLAUDE.md"
else
    cp "$SCRIPT_DIR/CLAUDE.md" "$TARGET_DIR/CLAUDE.md"
    cp "$SCRIPT_DIR/CLAUDE.md" "$CLAUDE_DIR/skills/find-cve/CLAUDE.md"
fi

# Copy agents
echo "Copying agent definitions..."
for agent in "$SCRIPT_DIR"/agents/*.md; do
    [ -f "$agent" ] && cp "$agent" "$CLAUDE_DIR/agents/"
done

# Copy commands
echo "Copying command definitions..."
for cmd in "$SCRIPT_DIR"/commands/*.md; do
    [ -f "$cmd" ] && cp "$cmd" "$CLAUDE_DIR/commands/"
done

# Copy hooks
echo "Copying hooks..."
mkdir -p "$CLAUDE_DIR/hooks"
cp "$SCRIPT_DIR"/hooks/hooks.json "$CLAUDE_DIR/hooks/"
for hook in "$SCRIPT_DIR"/hooks/*.mjs; do
    [ -f "$hook" ] && cp "$hook" "$CLAUDE_DIR/hooks/"
done

# Create REGISTRY.md from template if it doesn't exist
if [ ! -f "$TARGET_DIR/REGISTRY.md" ]; then
    echo "Creating REGISTRY.md from template..."
    cp "$SCRIPT_DIR/templates/REGISTRY.md" "$TARGET_DIR/REGISTRY.md"
else
    echo "REGISTRY.md already exists. Skipping."
fi

# Copy plugin manifest
mkdir -p "$CLAUDE_DIR/.claude-plugin"
cp "$SCRIPT_DIR/.claude-plugin/plugin.json" "$CLAUDE_DIR/.claude-plugin/"

echo ""
echo "=== Installation complete ==="
echo ""
echo "Directory structure:"
echo "  $TARGET_DIR/"
echo "  +-- CLAUDE.md              (agent instructions)"
echo "  +-- REGISTRY.md            (research tracker)"
echo "  +-- targets/               (per-target working dirs)"
echo "  +-- .claude/"
echo "      +-- agents/            (5 agent definitions)"
echo "      +-- commands/          (7 slash commands)"
echo "      +-- hooks/             (4 automation hooks)"
echo "      +-- skills/find-cve/   (skill reference)"
echo ""
echo "Usage:"
echo "  /hunt <package>          Full hunting pipeline"
echo "  /recon <category>        Find targets in a category"
echo "  /check-nvd <package>     Check for existing CVEs"
echo "  /fp-check                Verify a finding (6-gate process)"
echo "  /report                  Generate disclosure report"
echo "  /registry                Query the research registry"
echo "  /cross-pollinate         Find same vuln in similar packages"
echo ""
echo "Start with: /recon \"csv parsers\" or /hunt <package-name>"
