#!/usr/bin/env node

/**
 * Post-Tool-Use: Version Check Hook
 *
 * After reading package.json, requirements.txt, go.mod, or similar:
 * - Reminds to check the exact version against NVD/OSV
 * - Reminds to verify this is the latest version
 */

import { readFileSync } from "fs";

// Read the tool input/output from stdin
let input = "";
try {
  input = readFileSync("/dev/stdin", "utf-8");
} catch {
  process.exit(0);
}

// Check if we're reading a dependency/version file
const versionFiles = [
  "package.json",
  "package-lock.json",
  "requirements.txt",
  "setup.py",
  "setup.cfg",
  "pyproject.toml",
  "go.mod",
  "go.sum",
  "Gemfile",
  "Gemfile.lock",
  "composer.json",
  "Cargo.toml",
  "pom.xml",
];

const isVersionFile = versionFiles.some((f) => input.includes(f));

if (!isVersionFile) {
  process.exit(0);
}

const reminders = [];

reminders.push("VERSION CHECK REMINDER:");
reminders.push("  - Note the EXACT version number from this file");
reminders.push("  - Check NVD/OSV for existing CVEs on this exact version:");
reminders.push(
  '    curl -s "https://api.osv.dev/v1/query" -d \'{"package":{"name":"<pkg>","ecosystem":"<eco>"}}\''
);
reminders.push(
  "  - Verify this is the LATEST release (not an old, already-patched version):"
);
reminders.push("    npm view <package> version");
reminders.push("    pip3 index versions <package>");
reminders.push(
  "  - If the version is outdated, check the changelog for security fixes"
);
reminders.push(
  "  - A patched version = DUPLICATE, not a new finding. Check before proceeding."
);

console.log(reminders.join("\n"));

process.exit(0);
