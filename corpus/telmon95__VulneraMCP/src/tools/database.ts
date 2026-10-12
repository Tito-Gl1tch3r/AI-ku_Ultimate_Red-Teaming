import { Server } from '../mcp/server';
import { formatToolResult, ToolResult, Finding } from '../types';
import {
  saveFinding,
  getFindings,
  saveTestResult,
  getTestResults,
  getTestStatistics,
  createTables,
} from '../integrations/postgres';

export function registerDatabaseTools(server: Server) {
  // Save finding
  server.tool(
    'db.save_finding',
    {
      description: 'Save a bug finding to the database',
      inputSchema: {
        type: 'object',
        properties: {
          target: { type: 'string', description: 'Target URL or domain' },
          type: { type: 'string', description: 'Vulnerability type' },
          severity: {
            type: 'string',
            enum: ['low', 'medium', 'high', 'critical'],
            description: 'Severity level',
          },
          description: { type: 'string', description: 'Finding description' },
          payload: { type: 'string', description: 'Payload used' },
          response: { type: 'string', description: 'Response data' },
          score: { type: 'number', description: 'Severity score (0-10)' },
        },
        required: ['target', 'type', 'severity', 'description'],
      },
    },
    async (params: any): Promise<ToolResult> => {
      try {
        const finding: Finding = {
          target: params.target,
          type: params.type,
          severity: params.severity,
          description: params.description,
          payload: params.payload,
          response: params.response,
          timestamp: new Date(),
          score: params.score || 0,
        };

        const id = await saveFinding(finding);
        return formatToolResult(true, { id, finding });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Get findings
  server.tool(
    'db.get_findings',
    {
      description: 'Retrieve bug findings from the database',
      inputSchema: {
        type: 'object',
        properties: {
          target: { type: 'string', description: 'Filter by target' },
          limit: { type: 'number', description: 'Maximum number of results', default: 100 },
        },
      },
    },
    async ({ target, limit = 100 }: any): Promise<ToolResult> => {
      try {
        const findings = await getFindings(target, limit);
        return formatToolResult(true, {
          findings,
          count: findings.length,
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Get test results
  server.tool(
    'db.get_test_results',
    {
      description: 'Retrieve test results with success/failure and scores',
      inputSchema: {
        type: 'object',
        properties: {
          target: { type: 'string', description: 'Filter by target' },
          testType: { type: 'string', description: 'Filter by test type' },
          success: { type: 'boolean', description: 'Filter by success status' },
          limit: { type: 'number', description: 'Maximum number of results', default: 100 },
        },
      },
    },
    async ({ target, testType, success, limit = 100 }: any): Promise<ToolResult> => {
      try {
        const results = await getTestResults(target, testType, success, limit);
        return formatToolResult(true, {
          testResults: results,
          count: results.length,
          successCount: results.filter((r: any) => r.success).length,
          failureCount: results.filter((r: any) => !r.success).length,
          avgScore: results.reduce((sum: number, r: any) => sum + (r.score || 0), 0) / results.length || 0,
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Get test statistics
  server.tool(
    'db.get_statistics',
    {
      description: 'Get statistics about test results',
      inputSchema: {
        type: 'object',
        properties: {},
      },
    },
    async (): Promise<ToolResult> => {
      try {
        const stats = await getTestStatistics();
        return formatToolResult(true, {
          statistics: stats,
          summary: {
            totalTests: stats.reduce((sum: number, s: any) => sum + parseInt(s.count || 0), 0),
            totalTypes: stats.length,
          },
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Initialize database
  server.tool(
    'db.init',
    {
      description: 'Initialize database tables (run once on first setup)',
      inputSchema: {
        type: 'object',
        properties: {},
      },
    },
    async (): Promise<ToolResult> => {
      try {
        await createTables();
        return formatToolResult(true, { message: 'Database tables created successfully' });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );
}

