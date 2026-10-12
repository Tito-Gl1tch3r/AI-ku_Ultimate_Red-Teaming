import { Server } from '../mcp/server';
import { initZAP, getZAPClient, ZAPClient } from '../integrations/zap';
import { MCPProxyLayer } from '../integrations/zap-proxy';
import { saveTestResult } from '../integrations/postgres';
import { formatToolResult, ToolResult } from '../types';

let proxyLayer: MCPProxyLayer | null = null;

async function safeSaveTestResult(
  target: string,
  testType: string,
  success: boolean,
  resultData?: any,
  errorMessage?: string,
  score?: number,
  payload?: string,
  responseData?: string
) {
  try {
    await saveTestResult(target, testType, success, resultData, errorMessage, score, payload, responseData);
  } catch (error: any) {
    console.error(`[ZAP] Failed to save test result (${testType}):`, error?.message || error);
  }
}

function getProxyLayer(): MCPProxyLayer {
  if (!proxyLayer) {
    const zapClient = initZAP();
    proxyLayer = new MCPProxyLayer(zapClient);
  }
  return proxyLayer;
}

export function registerZAPTools(server: Server) {
  // Initialize ZAP client
  initZAP();

  // Health check
  server.tool(
    'zap.health_check',
    {
      description: 'Check if ZAP is running and accessible',
      inputSchema: {
        type: 'object',
        properties: {},
      },
    },
    async (): Promise<ToolResult> => {
      const client = getZAPClient();
      if (!client) {
        return formatToolResult(false, null, 'ZAP client not initialized');
      }
      const result = await client.healthCheck();
      return formatToolResult(result.success, result.data, result.error);
    }
  );

  // Start spider scan
  server.tool(
    'zap.start_spider',
    {
      description: 'Start a spider (crawler) scan on a target URL',
      inputSchema: {
        type: 'object',
        properties: {
          url: {
            type: 'string',
            description: 'Target URL to spider',
          },
          maxChildren: {
            type: 'number',
            description: 'Maximum number of children to crawl (optional)',
          },
          recurse: {
            type: 'boolean',
            description: 'Whether to recurse into subdirectories (optional)',
          },
          contextName: {
            type: 'string',
            description: 'Context name to use (optional)',
          },
        },
        required: ['url'],
      },
    },
    async ({ url, maxChildren, recurse, contextName }: any): Promise<ToolResult> => {
      const client = getZAPClient();
      if (!client) {
        return formatToolResult(false, null, 'ZAP client not initialized');
      }
      const result = await client.startSpider(url, maxChildren, recurse, contextName);
      if (result.success) {
        await safeSaveTestResult(url, 'zap_spider', true, result.data);
      }
      return formatToolResult(result.success, result.data, result.error);
    }
  );

  // Get spider status
  server.tool(
    'zap.get_spider_status',
    {
      description: 'Get the status of a spider scan',
      inputSchema: {
        type: 'object',
        properties: {
          scanId: {
            type: 'string',
            description: 'Spider scan ID',
          },
        },
        required: ['scanId'],
      },
    },
    async ({ scanId }: any): Promise<ToolResult> => {
      const client = getZAPClient();
      if (!client) {
        return formatToolResult(false, null, 'ZAP client not initialized');
      }
      const result = await client.getSpiderStatus(scanId);
      return formatToolResult(result.success, result.data, result.error);
    }
  );

  // Start active scan
  server.tool(
    'zap.start_active_scan',
    {
      description: 'Start an active vulnerability scan on a target URL',
      inputSchema: {
        type: 'object',
        properties: {
          url: {
            type: 'string',
            description: 'Target URL to scan',
          },
          recurse: {
            type: 'boolean',
            description: 'Whether to recurse into subdirectories (optional)',
          },
          inScopeOnly: {
            type: 'boolean',
            description: 'Only scan URLs in scope (optional)',
          },
          scanPolicyName: {
            type: 'string',
            description: 'Scan policy name to use (optional)',
          },
          method: {
            type: 'string',
            description: 'HTTP method (optional)',
          },
          postData: {
            type: 'string',
            description: 'POST data (optional)',
          },
        },
        required: ['url'],
      },
    },
    async ({ url, recurse, inScopeOnly, scanPolicyName, method, postData }: any): Promise<ToolResult> => {
      const client = getZAPClient();
      if (!client) {
        return formatToolResult(false, null, 'ZAP client not initialized');
      }
      const result = await client.startActiveScan(url, recurse, inScopeOnly, scanPolicyName, method, postData);
      if (result.success) {
        await safeSaveTestResult(url, 'zap_active_scan', true, result.data);
      }
      return formatToolResult(result.success, result.data, result.error);
    }
  );

  // Get active scan status
  server.tool(
    'zap.get_active_scan_status',
    {
      description: 'Get the status of an active scan',
      inputSchema: {
        type: 'object',
        properties: {
          scanId: {
            type: 'string',
            description: 'Active scan ID',
          },
        },
        required: ['scanId'],
      },
    },
    async ({ scanId }: any): Promise<ToolResult> => {
      const client = getZAPClient();
      if (!client) {
        return formatToolResult(false, null, 'ZAP client not initialized');
      }
      const result = await client.getActiveScanStatus(scanId);
      return formatToolResult(result.success, result.data, result.error);
    }
  );

  // Get alerts
  server.tool(
    'zap.get_alerts',
    {
      description: 'Get all security alerts from ZAP',
      inputSchema: {
        type: 'object',
        properties: {
          baseURL: {
            type: 'string',
            description: 'Filter alerts by base URL (optional)',
          },
          start: {
            type: 'number',
            description: 'Start index for pagination (optional)',
          },
          count: {
            type: 'number',
            description: 'Number of alerts to return (optional)',
          },
          riskId: {
            type: 'string',
            description: 'Filter by risk level: 0=Informational, 1=Low, 2=Medium, 3=High, 4=Critical (optional)',
          },
        },
      },
    },
    async ({ baseURL, start, count, riskId }: any): Promise<ToolResult> => {
      const client = getZAPClient();
      if (!client) {
        return formatToolResult(false, null, 'ZAP client not initialized');
      }
      const result = await client.getAlerts(baseURL, start, count, riskId);
      return formatToolResult(result.success, result.data, result.error);
    }
  );

  // Get alerts summary
  server.tool(
    'zap.get_alerts_summary',
    {
      description: 'Get summary of alerts by risk level',
      inputSchema: {
        type: 'object',
        properties: {
          baseURL: {
            type: 'string',
            description: 'Filter by base URL (optional)',
          },
        },
      },
    },
    async ({ baseURL }: any): Promise<ToolResult> => {
      const client = getZAPClient();
      if (!client) {
        return formatToolResult(false, null, 'ZAP client not initialized');
      }
      const result = await client.getAlertsSummary(baseURL);
      return formatToolResult(result.success, result.data, result.error);
    }
  );

  // Send custom request through ZAP
  server.tool(
    'zap.send_request',
    {
      description: 'Send a custom HTTP request through ZAP proxy',
      inputSchema: {
        type: 'object',
        properties: {
          url: {
            type: 'string',
            description: 'Target URL',
          },
          method: {
            type: 'string',
            description: 'HTTP method (GET, POST, PUT, DELETE, etc.)',
            default: 'GET',
          },
          headers: {
            type: 'object',
            description: 'HTTP headers (optional)',
          },
          body: {
            type: 'string',
            description: 'Request body (optional)',
          },
        },
        required: ['url'],
      },
    },
    async ({ url, method = 'GET', headers, body }: any): Promise<ToolResult> => {
      const client = getZAPClient();
      if (!client) {
        return formatToolResult(false, null, 'ZAP client not initialized');
      }
      const result = await client.sendRequest(url, method, headers, body);
      return formatToolResult(result.success, result.data, result.error);
    }
  );

  // Process request through MCP proxy layer
  server.tool(
    'zap.proxy_process',
    {
      description: 'Process a request through the MCP proxy layer (enhances with AI intelligence)',
      inputSchema: {
        type: 'object',
        properties: {
          method: {
            type: 'string',
            description: 'HTTP method',
          },
          url: {
            type: 'string',
            description: 'Target URL',
          },
          headers: {
            type: 'object',
            description: 'HTTP headers (optional)',
          },
          body: {
            type: 'string',
            description: 'Request body (optional)',
          },
        },
        required: ['method', 'url'],
      },
    },
    async ({ method, url, headers = {}, body }: any): Promise<ToolResult> => {
      try {
        const proxy = getProxyLayer();
        const result = await proxy.processRequest(method, url, headers, body);

        // Save findings to database
        for (const finding of result.findings) {
          if (finding.customFinding) {
            await safeSaveTestResult(
              finding.customFinding.url,
              finding.customFinding.type,
              finding.verified,
              finding.customFinding,
              undefined,
              (finding.aiScore || finding.correlationScore) * 10,
              finding.customFinding.evidence,
              JSON.stringify(finding)
            );
          } else if (finding.zapAlert) {
            await safeSaveTestResult(
              finding.zapAlert.url,
              finding.zapAlert.name,
              finding.verified,
              finding.zapAlert,
              undefined,
              finding.correlationScore * 10,
              finding.zapAlert.attack || '',
              JSON.stringify(finding.zapAlert)
            );
          }
        }

        return formatToolResult(true, {
          request: result.request,
          response: result.response,
          findings: result.findings.map(f => ({
            type: f.zapAlert?.name || f.customFinding?.type || 'unknown',
            severity: f.zapAlert?.risk || f.customFinding?.severity || 'low',
            confidence: f.zapAlert?.confidence || f.customFinding?.confidence || 0,
            url: f.zapAlert?.url || f.customFinding?.url || '',
            correlationScore: f.correlationScore,
            aiScore: f.aiScore,
            verified: f.verified,
          })),
          findingsCount: result.findings.length,
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message || 'Failed to process request');
      }
    }
  );

  // Get sites
  server.tool(
    'zap.get_sites',
    {
      description: 'Get list of discovered sites from ZAP',
      inputSchema: {
        type: 'object',
        properties: {},
      },
    },
    async (): Promise<ToolResult> => {
      const client = getZAPClient();
      if (!client) {
        return formatToolResult(false, null, 'ZAP client not initialized');
      }
      const result = await client.getSites();
      return formatToolResult(result.success, result.data, result.error);
    }
  );

  // Get URLs
  server.tool(
    'zap.get_urls',
    {
      description: 'Get list of discovered URLs from ZAP',
      inputSchema: {
        type: 'object',
        properties: {
          baseURL: {
            type: 'string',
            description: 'Filter by base URL (optional)',
          },
        },
      },
    },
    async ({ baseURL }: any): Promise<ToolResult> => {
      const client = getZAPClient();
      if (!client) {
        return formatToolResult(false, null, 'ZAP client not initialized');
      }
      const result = await client.getUrls(baseURL);
      return formatToolResult(result.success, result.data, result.error);
    }
  );

  // Create context
  server.tool(
    'zap.create_context',
    {
      description: 'Create a scanning context in ZAP',
      inputSchema: {
        type: 'object',
        properties: {
          contextName: {
            type: 'string',
            description: 'Name for the context',
          },
        },
        required: ['contextName'],
      },
    },
    async ({ contextName }: any): Promise<ToolResult> => {
      const client = getZAPClient();
      if (!client) {
        return formatToolResult(false, null, 'ZAP client not initialized');
      }
      const result = await client.createContext(contextName);
      return formatToolResult(result.success, result.data, result.error);
    }
  );

  // Include URL in context
  server.tool(
    'zap.include_in_context',
    {
      description: 'Include a URL pattern in a context',
      inputSchema: {
        type: 'object',
        properties: {
          contextName: {
            type: 'string',
            description: 'Context name',
          },
          regex: {
            type: 'string',
            description: 'URL regex pattern to include',
          },
        },
        required: ['contextName', 'regex'],
      },
    },
    async ({ contextName, regex }: any): Promise<ToolResult> => {
      const client = getZAPClient();
      if (!client) {
        return formatToolResult(false, null, 'ZAP client not initialized');
      }
      const result = await client.includeInContext(contextName, regex);
      return formatToolResult(result.success, result.data, result.error);
    }
  );
}
