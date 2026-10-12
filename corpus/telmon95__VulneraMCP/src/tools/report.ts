import { Server } from '../mcp/server';
import { formatToolResult, ToolResult } from '../types';
import { getFindings, getTestResults } from '../integrations/postgres';
import * as fs from 'fs-extra';
import * as path from 'path';

function safeJson(value: any): any {
  if (value == null) return null;
  if (typeof value === 'string') {
    try {
      return JSON.parse(value);
    } catch {
      return value;
    }
  }
  return value;
}

function toMarkdownList(items: string[]): string {
  if (items.length === 0) return 'None';
  return items.map((item) => `- ${item}`).join('\n');
}

function toFindingsTable(findings: any[]): string {
  if (findings.length === 0) return 'None';
  const header = '| Type | Severity | Description |\n| --- | --- | --- |';
  const rows = findings.map((f) => `| ${f.type} | ${f.severity} | ${f.description} |`);
  return [header, ...rows].join('\n');
}

export function registerReportTools(server: Server) {
  server.tool(
    'report.generate_markdown',
    {
      description: 'Generate a markdown report from findings and scanner runs',
      inputSchema: {
        type: 'object',
        properties: {
          target: { type: 'string' },
          limit: { type: 'number', default: 100 },
        },
      },
    },
    async ({ target, limit = 100 }: any): Promise<ToolResult> => {
      try {
        const findings = await getFindings(target, limit);
        const tests = await getTestResults(target, undefined, undefined, limit);

        const scannerRuns = tests.filter((t) => t.test_type === 'scanner_run_flow');
        const scannerSummaries: string[] = scannerRuns.map((t) => {
          const data = safeJson(t.result_data);
          const summary = data?.artifacts?.summary || {};
          const steps = data?.steps?.length ?? 0;
          const swagger = data?.artifacts?.swagger?.length ?? 0;
          const graphql = data?.artifacts?.graphql?.length ?? 0;
          const leaks = data?.artifacts?.leaks?.length ?? 0;
          const hosts = summary.hostsDiscovered ?? 0;
          const durationMs = summary.durationMs ?? 0;
          const mode = data?.mode || 'unknown';
          const hypotheses = data?.hypotheses?.length ?? 0;
          const earlyAborts = summary.earlyAborts ?? 0;
          return `Scanner run at ${t.timestamp}: mode=${mode}, steps=${steps}, hosts=${hosts}, swagger=${swagger}, graphql=${graphql}, leaks=${leaks}, hypotheses=${hypotheses}, earlyAborts=${earlyAborts}, duration=${durationMs}ms`;
        });

        const autoRunDetails: string[] = [];
        for (const run of scannerRuns) {
          const data = safeJson(run.result_data);
          const api = data?.artifacts?.autoRun?.api || [];
          const auth = data?.artifacts?.autoRun?.auth || [];
          const cloud = data?.artifacts?.autoRun?.cloud || [];
          if (api.length + auth.length + cloud.length === 0) continue;
          autoRunDetails.push(`Auto-run summary at ${run.timestamp}: api=${api.length}, auth=${auth.length}, cloud=${cloud.length}`);
        }

        const markdown = `# Bug Bounty Report
## Executive Summary
This report summarizes automated reconnaissance, discovery, and safe validation checks executed against the target. Findings are prioritized by severity and include evidence summaries for reproducibility.

## Target
${target || 'All'}

## Attack Surface Overview
${toMarkdownList(scannerSummaries)}

## Hypotheses Generated
${scannerRuns.length === 0 ? 'None' : scannerRuns.map((t) => {
  const data = safeJson(t.result_data);
  const hypotheses = data?.hypotheses || [];
  return hypotheses.length === 0 ? 'None' : hypotheses.map((h: any) => `- ${h.type}: ${h.reason}`).join('\n');
}).join('\n')}

## Findings
${toFindingsTable(findings)}

## Findings Detail
${findings.length === 0 ? 'None' : findings.map((f) => `### ${f.type}\nSeverity: ${f.severity}\nDescription: ${f.description}\nEvidence: ${f.response || f.payload || 'N/A'}`).join('\n\n')}

## Recommended Fixes
${findings.length === 0 ? 'None' : findings.map((f) => `- ${f.type}: Review access controls, harden configuration, and validate input handling.`).join('\n')}

## Scanner Runs
${toMarkdownList(scannerSummaries)}

## Auto-Run Summaries
${toMarkdownList(autoRunDetails)}

## Checks Executed
${tests.length === 0 ? 'None' : tests.map((t) => `- ${t.test_type} (${t.timestamp})`).join('\n')}

## Test Results
${tests.length === 0 ? 'None' : tests.map((t) => `- ${t.test_type}: ${t.success ? 'OK' : 'FAIL'} (${t.timestamp})`).join('\n')}
`;

        const reportsDir = path.join(process.cwd(), 'reports');
        await fs.ensureDir(reportsDir);
        const filepath = path.join(reportsDir, `report_${Date.now()}.md`);
        await fs.writeFile(filepath, markdown, 'utf-8');

        return formatToolResult(true, { path: filepath, markdown });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );
}
