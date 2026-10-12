#!/usr/bin/env node

/**
 * Pre-Tool-Use: Finding Self-Check Hook
 *
 * When writing to findings.md or verdict.md:
 * - Injects the self-criticism checklist as a reminder
 * - Reminds about common false positive patterns
 */

import { readFileSync } from "fs";

// Read the tool input from stdin
let input = "";
try {
  input = readFileSync("/dev/stdin", "utf-8");
} catch {
  process.exit(0);
}

// Check if we're writing to a findings or verdict file
const isFindings = input.includes("findings.md");
const isVerdict = input.includes("verdict.md");
const isPoc = input.includes("poc_");

if (!isFindings && !isVerdict && !isPoc) {
  process.exit(0);
}

const reminders = [];

if (isFindings) {
  reminders.push("SELF-CHECK REMINDER (findings.md):");
  reminders.push("  1. Did you trace the FULL data flow from source to sink?");
  reminders.push("  2. Did you verify the source is attacker-controlled (not internal)?");
  reminders.push("  3. Did you check for validation/sanitization between source and sink?");
  reminders.push("  4. Did you read the README for 'untrusted input' warnings?");
  reminders.push("  5. Is this a real security bug, or intended behavior?");
}

if (isVerdict) {
  reminders.push("SELF-CHECK REMINDER (verdict.md):");
  reminders.push("  1. Did the PoC succeed 3/3 times?");
  reminders.push("  2. Is this the LATEST version of the package?");
  reminders.push("  3. Does exploitation require permissions that already grant equivalent access?");
  reminders.push("  4. Are there runtime/framework protections you haven't checked?");
  reminders.push("  5. Am I hallucinating? LLMs are biased toward seeing bugs.");
  reminders.push("  6. Did I actually READ the validation code, or assume it works?");
  reminders.push("  7. For DoS: OOM crash or just a caught RangeError?");
}

if (isPoc) {
  reminders.push("POC REMINDER:");
  reminders.push("  - Did the Director approve this PoC plan?");
  reminders.push("  - Does the PoC run locally only (no remote targets)?");
  reminders.push("  - Does it use the exact version from the target's lockfile?");
  reminders.push("  - Does it produce concrete evidence (not 'it might crash')?");
}

if (reminders.length > 0) {
  console.log(reminders.join("\n"));
}

process.exit(0);
