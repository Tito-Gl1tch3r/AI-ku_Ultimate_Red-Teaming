#!/usr/bin/env node

/**
 * Pre-Tool-Use: Clone Deduplication Hook
 *
 * Before a Bash tool call that contains "git clone":
 * - Checks if the target repo is already in REGISTRY.md
 * - Warns if the target has already been investigated
 * - Checks if the directory already exists locally
 */

import { readFileSync, existsSync } from "fs";
import { join } from "path";

const projectRoot = process.env.PROJECT_DIR || process.cwd();
const registryPath = join(projectRoot, "REGISTRY.md");

// Read the tool input from stdin
let input = "";
try {
  input = readFileSync("/dev/stdin", "utf-8");
} catch {
  process.exit(0);
}

// Only act on git clone commands
if (!input.includes("git clone")) {
  process.exit(0);
}

// Extract the repo URL or name from the clone command
const cloneMatch = input.match(/git clone\s+(?:--[^\s]+\s+)*(?:["']?)([^\s"']+)/);
if (!cloneMatch) {
  process.exit(0);
}

const repoUrl = cloneMatch[1];

// Extract repo name from URL
const repoName = repoUrl
  .replace(/\.git$/, "")
  .split("/")
  .pop();

if (!repoName) {
  process.exit(0);
}

const warnings = [];

// Check REGISTRY.md for duplicates
if (existsSync(registryPath)) {
  try {
    const registry = readFileSync(registryPath, "utf-8");
    const lowerRegistry = registry.toLowerCase();
    const lowerName = repoName.toLowerCase();

    if (lowerRegistry.includes(lowerName)) {
      // Determine which section it's in
      const sections = [
        { name: "IN PROGRESS", pattern: /## IN PROGRESS([\s\S]*?)(?=##|$)/ },
        { name: "SUBMITTED", pattern: /## SUBMITTED([\s\S]*?)(?=##|$)/ },
        { name: "FALSE POSITIVES", pattern: /## FALSE POSITIVES([\s\S]*?)(?=##|$)/ },
        { name: "SKIP", pattern: /## SKIP([\s\S]*?)(?=##|$)/ },
        { name: "DUPLICATE", pattern: /## DUPLICATE([\s\S]*?)(?=##|$)/ },
      ];

      for (const section of sections) {
        const match = registry.match(section.pattern);
        if (match && match[1].toLowerCase().includes(lowerName)) {
          warnings.push(
            `REGISTRY WARNING: "${repoName}" found in ${section.name} section of REGISTRY.md. Check before proceeding.`
          );
          break;
        }
      }
    }
  } catch {
    // Registry couldn't be read - not critical
  }
}

// Check if target directory already exists
const targetsDir = join(projectRoot, "targets", repoName);
if (existsSync(targetsDir)) {
  warnings.push(
    `DIRECTORY EXISTS: targets/${repoName}/ already exists locally. The repo may already be cloned.`
  );
}

if (warnings.length > 0) {
  console.log(warnings.join("\n"));
}

process.exit(0);
