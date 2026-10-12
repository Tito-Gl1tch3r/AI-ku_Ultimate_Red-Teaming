import { Server } from '../mcp/server';
import axios, { AxiosResponse } from 'axios';
import { formatToolResult, ToolResult, SecurityTestResult } from '../types';
import { saveFinding, saveTestResult } from '../integrations/postgres';
import { runCommand } from '../utils/exec';

export function registerSecurityTools(server: Server) {
  // XSS Testing
  server.tool(
    'security.test_xss',
    {
      description: 'Test for XSS vulnerabilities (non-destructive payloads)',
      inputSchema: {
        type: 'object',
        properties: {
          url: { type: 'string', description: 'Target URL' },
          params: {
            type: 'object',
            description: 'Parameters to test (key-value pairs)',
          },
          method: {
            type: 'string',
            description: 'HTTP method',
            enum: ['GET', 'POST', 'PUT'],
            default: 'GET',
          },
        },
        required: ['url'],
      },
    },
    async ({ url, params = {}, method = 'GET' }: any): Promise<ToolResult> => {
      try {
        const payloads = [
          '<script>alert(1)</script>',
          '"><img src=x onerror=alert(1)>',
          "'><svg onload=alert(1)>",
          'javascript:alert(1)',
          '<iframe src=javascript:alert(1)>',
        ];

        const results: SecurityTestResult[] = [];

        for (const payload of payloads) {
          try {
            let response: AxiosResponse;
            const testParams = { ...params, test: payload };

            if (method === 'GET') {
              response = await axios.get(url, {
                params: testParams,
                validateStatus: () => true,
                timeout: 15000,
                headers: {
                  'User-Agent': 'Mozilla/5.0',
                },
              });
            } else {
              response = await axios.post(url, testParams, {
                validateStatus: () => true,
                timeout: 15000,
                headers: {
                  'User-Agent': 'Mozilla/5.0',
                  'Content-Type': 'application/x-www-form-urlencoded',
                },
              });
            }

            const body = typeof response.data === 'string' ? response.data : JSON.stringify(response.data);
            const reflected = body.includes(payload);
            const inHeaders = JSON.stringify(response.headers).includes(payload);

            const result: SecurityTestResult = {
              payload,
              response: {
                status: response.status,
                reflected,
                inHeaders,
                bodyLength: body.length,
              },
            };

            if (reflected || inHeaders) {
              result.vulnerability = 'XSS';
              result.severity = 'high';
              
              await saveFinding({
                target: url,
                type: 'XSS',
                severity: 'high',
                description: `Potential XSS vulnerability - payload reflected: ${payload}`,
                payload,
                response: body.substring(0, 1000),
                timestamp: new Date(),
                score: 8,
              });
            }

            results.push(result);
          } catch (error: any) {
            results.push({
              payload,
              error: error.message,
            });
          }
        }

        const xssScore = results.some((r: any) => r.vulnerable) ? 7 : 3;
        await saveTestResult(url, 'xss_test', true, { results }, undefined, xssScore, JSON.stringify(params), JSON.stringify(results));

        return formatToolResult(true, {
          results,
          summary: {
            totalTests: payloads.length,
            potentialVulns: results.filter((r) => r.vulnerability).length,
          },
        });
      } catch (error: any) {
        await saveTestResult(url, 'xss_test', false, null, error.message, 0, undefined, undefined);
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // SQL Injection Testing
  server.tool(
    'security.test_sqli',
    {
      description: 'Test for SQL injection vulnerabilities',
      inputSchema: {
        type: 'object',
        properties: {
          url: { type: 'string', description: 'Target URL' },
          param: { type: 'string', description: 'Parameter name to test', default: 'id' },
        },
        required: ['url'],
      },
    },
    async ({ url, param = 'id' }: any): Promise<ToolResult> => {
      try {
        // Try sqlmap first if available
        const sqlmapExists = await runCommand('which', ['sqlmap']).then(() => true).catch(() => false);
        
        if (sqlmapExists) {
          try {
            const result = await runCommand('sqlmap', [
              '-u', url,
              '-p', param,
              '--batch',
              '--risk=1',
              '--level=1',
              '--timeout=10',
            ], 60000);
            
            const vulnerable = result.stdout.includes('is vulnerable') || result.stdout.includes('injection');
            
            if (vulnerable) {
              await saveFinding({
                target: url,
                type: 'SQL Injection',
                severity: 'critical',
                description: `SQL injection vulnerability detected in parameter: ${param}`,
                payload: `sqlmap -u ${url} -p ${param}`,
                response: result.stdout.substring(0, 1000),
                timestamp: new Date(),
                score: 10,
              });
            }
            
            return formatToolResult(true, {
              tool: 'sqlmap',
              vulnerable,
              output: result.stdout,
            });
          } catch (e) {
            // Fall through to manual testing
          }
        }

        // Manual testing fallback
        const payloads = [
          "' OR '1'='1",
          "' AND SLEEP(5)-- ",
          "1' UNION SELECT NULL--",
          "admin'--",
        ];

        const results: SecurityTestResult[] = [];
        const startTime = Date.now();

        for (const payload of payloads) {
          try {
            const testStart = Date.now();
            const response = await axios.get(url, {
              params: { [param]: payload },
              timeout: 20000,
              validateStatus: () => true,
            });
            const testDuration = Date.now() - testStart;

            const body = typeof response.data === 'string' ? response.data : JSON.stringify(response.data);
            const errorIndicators = [
              'sql syntax',
              'mysql',
              'postgresql',
              'ora-',
              'sqlite',
              'database error',
            ];
            const hasError = errorIndicators.some((indicator) =>
              body.toLowerCase().includes(indicator)
            );
            const isTimeBased = payload.includes('SLEEP') && testDuration > 4000;

            const result: SecurityTestResult = {
              payload,
              response: {
                status: response.status,
                duration: testDuration,
                hasError,
                isTimeBased,
              },
            };

            if (hasError || isTimeBased) {
              result.vulnerability = 'SQL Injection';
              result.severity = 'critical';
              
              await saveFinding({
                target: url,
                type: 'SQL Injection',
                severity: 'critical',
                description: `Potential SQL injection - error indicators or time-based delay detected`,
                payload,
                response: body.substring(0, 1000),
                timestamp: new Date(),
                score: 10,
              });
            }

            results.push(result);
          } catch (error: any) {
            results.push({
              payload,
              error: error.message,
            });
          }
        }

        const sqliScore = results.some((r: any) => r.vulnerable) ? 9 : 4;
        await saveTestResult(url, 'sqli_test', true, { results }, undefined, sqliScore, param, JSON.stringify(results));

        return formatToolResult(true, {
          results,
          summary: {
            totalTests: payloads.length,
            potentialVulns: results.filter((r) => r.vulnerability).length,
          },
        });
      } catch (error: any) {
        await saveTestResult(url, 'sqli_test', false, null, error.message, 0, param, undefined);
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // IDOR Testing
  server.tool(
    'security.test_idor',
    {
      description: 'Test for IDOR (Insecure Direct Object Reference) vulnerabilities',
      inputSchema: {
        type: 'object',
        properties: {
          url: { type: 'string', description: 'Target URL with ID parameter' },
          idParam: { type: 'string', description: 'ID parameter name', default: 'id' },
          testIds: {
            type: 'array',
            items: { type: 'number' },
            description: 'IDs to test (e.g., [1, 2, 3])',
          },
        },
        required: ['url'],
      },
    },
    async ({ url, idParam = 'id', testIds = [1, 2, 3, 999, 1000] }: any): Promise<ToolResult> => {
      try {
        const results: any[] = [];
        let baselineResponse: AxiosResponse | null = null;

        for (const testId of testIds) {
          try {
            const response = await axios.get(url, {
              params: { [idParam]: testId },
              validateStatus: () => true,
              timeout: 15000,
            });

            if (!baselineResponse) {
              baselineResponse = response;
            }

            const isDifferent = response.status !== baselineResponse.status ||
              response.data !== baselineResponse.data;

            const result = {
              id: testId,
              status: response.status,
              length: typeof response.data === 'string' 
                ? response.data.length 
                : JSON.stringify(response.data).length,
              isDifferent,
              accessible: response.status === 200,
            };

            if (isDifferent && response.status === 200) {
              await saveFinding({
                target: url,
                type: 'IDOR',
                severity: 'high',
                description: `Potential IDOR - different response for ID: ${testId}`,
                payload: `${idParam}=${testId}`,
                response: typeof response.data === 'string' 
                  ? response.data.substring(0, 1000)
                  : JSON.stringify(response.data).substring(0, 1000),
                timestamp: new Date(),
                score: 7,
              });
            }

            results.push(result);
          } catch (error: any) {
            results.push({
              id: testId,
              error: error.message,
            });
          }
        }

        const idorScore = results.some((r: any) => r.vulnerable) ? 8 : 4;
        await saveTestResult(url, 'idor_test', true, { results }, undefined, idorScore, JSON.stringify(testIds), JSON.stringify(results));

        return formatToolResult(true, {
          results,
          summary: {
            totalTests: testIds.length,
            accessible: results.filter((r) => r.accessible).length,
            potentialVulns: results.filter((r) => r.isDifferent && r.accessible).length,
          },
        });
      } catch (error: any) {
        await saveTestResult(url, 'idor_test', false, null, error.message, 0, JSON.stringify(testIds), undefined);
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // CSP Testing
  server.tool(
    'security.test_csp',
    {
      description: 'Test Content Security Policy configuration',
      inputSchema: {
        type: 'object',
        properties: {
          url: { type: 'string', description: 'Target URL' },
        },
        required: ['url'],
      },
    },
    async ({ url }: any): Promise<ToolResult> => {
      try {
        const response = await axios.get(url, {
          validateStatus: () => true,
          timeout: 15000,
        });

        const cspHeader = response.headers['content-security-policy'] ||
          response.headers['x-content-security-policy'];

        const issues: string[] = [];
        let severity: 'low' | 'medium' | 'high' = 'low';

        if (!cspHeader) {
          issues.push('No CSP header found');
          severity = 'medium';
        } else {
          if (!cspHeader.includes("'unsafe-inline'") && cspHeader.includes('script-src')) {
            // Good - no unsafe-inline
          } else if (cspHeader.includes("'unsafe-inline'")) {
            issues.push("CSP allows 'unsafe-inline' in script-src");
            severity = 'high';
          }

          if (!cspHeader.includes("'unsafe-eval'") && cspHeader.includes('script-src')) {
            // Good
          } else if (cspHeader.includes("'unsafe-eval'")) {
            issues.push("CSP allows 'unsafe-eval'");
            severity = 'medium';
          }

          if (!cspHeader.includes('default-src')) {
            issues.push('No default-src directive');
            severity = 'medium';
          }
        }

        if (issues.length > 0 && severity !== 'low') {
          await saveFinding({
            target: url,
            type: 'CSP Misconfiguration',
            severity,
            description: `CSP issues: ${issues.join(', ')}`,
            response: cspHeader || 'No CSP header',
            timestamp: new Date(),
            score: severity === 'high' ? 6 : 4,
          });
        }

        return formatToolResult(true, {
          cspHeader: cspHeader || null,
          issues,
          severity,
          secure: issues.length === 0,
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Auth Bypass Testing
  server.tool(
    'security.test_auth_bypass',
    {
      description: 'Test for authentication bypass vulnerabilities',
      inputSchema: {
        type: 'object',
        properties: {
          url: { type: 'string', description: 'Protected endpoint URL' },
          method: {
            type: 'string',
            enum: ['GET', 'POST', 'PUT', 'DELETE'],
            default: 'GET',
          },
        },
        required: ['url'],
      },
    },
    async ({ url, method = 'GET' }: any): Promise<ToolResult> => {
      try {
        const bypassAttempts = [
          { headers: {} }, // No auth
          { headers: { 'X-Forwarded-For': '127.0.0.1' } },
          { headers: { 'X-Original-IP': '127.0.0.1' } },
          { headers: { 'X-Real-IP': '127.0.0.1' } },
          { headers: { 'Authorization': 'Bearer null' } },
          { headers: { 'Authorization': 'Bearer undefined' } },
        ];

        const results: any[] = [];

        for (const attempt of bypassAttempts) {
          try {
            const config: any = {
              url,
              method: method.toLowerCase(),
              validateStatus: () => true,
              timeout: 15000,
              headers: {
                'User-Agent': 'Mozilla/5.0',
                ...attempt.headers,
              },
            };

            const response = await axios(config);

            const result = {
              attempt: attempt.headers,
              status: response.status,
              accessible: response.status === 200,
              bodyLength: typeof response.data === 'string'
                ? response.data.length
                : JSON.stringify(response.data).length,
            };

            if (result.accessible) {
              await saveFinding({
                target: url,
                type: 'Auth Bypass',
                severity: 'critical',
                description: `Potential auth bypass - accessible without proper authentication`,
                payload: JSON.stringify(attempt.headers),
                response: typeof response.data === 'string'
                  ? response.data.substring(0, 1000)
                  : JSON.stringify(response.data).substring(0, 1000),
                timestamp: new Date(),
                score: 9,
              });
            }

            results.push(result);
          } catch (error: any) {
            results.push({
              attempt: attempt.headers,
              error: error.message,
            });
          }
        }

        const authScore = results.some((r: any) => r.vulnerable) ? 9 : 4;
        await saveTestResult(url, 'auth_bypass_test', true, { results }, undefined, authScore, method, JSON.stringify(results));

        return formatToolResult(true, {
          results,
          summary: {
            totalTests: bypassAttempts.length,
            accessible: results.filter((r) => r.accessible).length,
          },
        });
      } catch (error: any) {
        await saveTestResult(url, 'auth_bypass_test', false, null, error.message, 0, method, undefined);
        return formatToolResult(false, null, error.message);
      }
    }
  );
}

