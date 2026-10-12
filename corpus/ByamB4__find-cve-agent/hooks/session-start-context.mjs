#!/usr/bin/env node

/**
 * Session Start Context Hook
 *
 * On session start/resume/clear/compact:
 * - Reads REGISTRY.md if it exists and injects current research state
 * - Reads any active target brief for context continuity
 * - Provides a summary of what's in progress
 */

import { readFileSync, existsSync, readdirSync, statSync } from "fs";
import { join, resolve } from "path";

const projectRoot = process.env.PROJECT_DIR || process.cwd();
const registryPath = join(projectRoot, "REGISTRY.md");
const targetsDir = join(projectRoot, "targets");

const lines = [];

// Read REGISTRY.md summary
if (existsSync(registryPath)) {
  try {
    const content = readFileSync(registryPath, "utf-8");
    const inProgressMatches = content.match(/^\|[^|]+\|[^|]+\|[^|]+\|[^|]+\|$/gm);
    const submittedMatches = content.match(
      /## SUBMITTED[\s\S]*?(?=##|$)/
    );

    let inProgressCount = 0;
    let submittedCount = 0;

    if (inProgressMatches) {
      // Subtract header row
      inProgressCount = Math.max(0, inProgressMatches.length - 5);
    }

    // Count submitted entries
    if (submittedMatches) {
      const submittedLines = submittedMatches[0]
        .split("\n")
        .filter((l) => l.startsWith("|") && !l.includes("---") && !l.includes("Repo"));
      submittedCount = submittedLines.length;
    }

    // Count sections
    const sections = {
      in_progress: (content.match(/## IN PROGRESS([\s\S]*?)(?=##|$)/)?.[1] || "")
        .split("\n")
        .filter((l) => l.startsWith("|") && !l.includes("---") && !l.includes("Repo")).length,
      submitted: (content.match(/## SUBMITTED([\s\S]*?)(?=##|$)/)?.[1] || "")
        .split("\n")
        .filter((l) => l.startsWith("|") && !l.includes("---") && !l.includes("Repo")).length,
      false_positives: (content.match(/## FALSE POSITIVES([\s\S]*?)(?=##|$)/)?.[1] || "")
        .split("\n")
        .filter((l) => l.startsWith("|") && !l.includes("---") && !l.includes("Repo")).length,
      skip: (content.match(/## SKIP([\s\S]*?)(?=##|$)/)?.[1] || "")
        .split("\n")
        .filter((l) => l.startsWith("|") && !l.includes("---") && !l.includes("Repo")).length,
    };

    lines.push("REGISTRY STATUS:");
    lines.push(`  In Progress: ${sections.in_progress}`);
    lines.push(`  Submitted: ${sections.submitted}`);
    lines.push(`  False Positives: ${sections.false_positives}`);
    lines.push(`  Skipped: ${sections.skip}`);
  } catch {
    // Registry exists but couldn't be parsed - not critical
  }
} else {
  lines.push(
    "No REGISTRY.md found. Run /registry or /hunt to initialize."
  );
}

// Check for active targets with briefs
if (existsSync(targetsDir)) {
  try {
    const targets = readdirSync(targetsDir).filter((d) => {
      const fullPath = join(targetsDir, d);
      return statSync(fullPath).isDirectory();
    });

    if (targets.length > 0) {
      lines.push("");
      lines.push("ACTIVE TARGETS:");

      for (const target of targets) {
        const briefPath = join(targetsDir, target, "brief.md");
        const findingsPath = join(targetsDir, target, "findings.md");
        const verdictPath = join(targetsDir, target, "verdict.md");
        const pocFiles = existsSync(join(targetsDir, target))
          ? readdirSync(join(targetsDir, target)).filter((f) =>
              f.startsWith("poc_")
            )
          : [];

        let status = "recon";
        if (existsSync(verdictPath)) {
          const verdict = readFileSync(verdictPath, "utf-8");
          if (verdict.includes("CONFIRMED")) status = "CONFIRMED";
          else if (verdict.includes("FALSE_POSITIVE"))
            status = "false_positive";
          else status = "validating";
        } else if (pocFiles.length > 0) {
          status = "poc_ready";
        } else if (existsSync(findingsPath)) {
          status = "findings_ready";
        } else if (existsSync(briefPath)) {
          status = "brief_ready";
        }

        lines.push(`  ${target}: ${status}`);
      }
    }
  } catch {
    // Targets dir exists but couldn't be read - not critical
  }
}

if (lines.length > 0) {
  console.log(lines.join("\n"));
}
