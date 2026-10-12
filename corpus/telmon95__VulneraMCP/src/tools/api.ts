import { Server } from '../mcp/server';
import axios from 'axios';
import { formatToolResult, ToolResult } from '../types';
import { saveFinding, saveTestResult } from '../integrations/postgres';

const INTROSPECTION_QUERY = `
  query IntrospectionQuery {
    __schema {
      queryType { name }
      mutationType { name }
      types { name kind }
    }
  }
`;

export function registerApiTools(server: Server) {
  // GraphQL introspection
  server.tool(
    'api.graphql_introspection',
    {
      description: 'Run GraphQL introspection',
      inputSchema: {
        type: 'object',
        properties: {
          url: { type: 'string' },
          headers: { type: 'object' },
        },
        required: ['url'],
      },
    },
    async ({ url, headers = {} }: any): Promise<ToolResult> => {
      try {
        const response = await axios.post(
          url,
          { query: INTROSPECTION_QUERY },
          { headers: { 'Content-Type': 'application/json', ...headers }, validateStatus: () => true, timeout: 15000 }
        );

        const ok = response.status === 200 && response.data?.data?.__schema;
        if (ok) {
          await saveFinding({
            target: url,
            type: 'GraphQL Introspection',
            severity: 'medium',
            description: 'GraphQL introspection enabled',
            response: JSON.stringify(response.data).substring(0, 1000),
            timestamp: new Date(),
            score: 5,
          });
        }

        await saveTestResult(url, 'graphql_introspection', true, { ok });

        return formatToolResult(true, { ok, status: response.status, data: response.data });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // GraphQL misconfig check
  server.tool(
    'api.graphql_misconfig',
    {
      description: 'Check GraphQL misconfig',
      inputSchema: {
        type: 'object',
        properties: {
          url: { type: 'string' },
          headers: { type: 'object' },
        },
        required: ['url'],
      },
    },
    async ({ url, headers = {} }: any): Promise<ToolResult> => {
      try {
        const response = await axios.post(
          url,
          { query: '{ __schema { types { name } } }' },
          { headers: { 'Content-Type': 'application/json', ...headers }, validateStatus: () => true, timeout: 15000 }
        );

        const enabled = response.status === 200 && !!response.data?.data?.__schema;
        const errors = response.data?.errors || [];

        return formatToolResult(true, { enabled, status: response.status, errors });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Rate limit testing
  server.tool(
    'api.rate_limit_test',
    {
      description: 'Test API rate limiting',
      inputSchema: {
        type: 'object',
        properties: {
          url: { type: 'string' },
          method: { type: 'string', enum: ['GET', 'POST', 'PUT', 'DELETE'], default: 'GET' },
          headers: { type: 'object' },
          body: { type: 'object' },
          requests: { type: 'number', default: 20 },
        },
        required: ['url'],
      },
    },
    async ({ url, method = 'GET', headers = {}, body, requests = 20 }: any): Promise<ToolResult> => {
      try {
        let rateLimited = 0;
        const statuses: number[] = [];

        for (let i = 0; i < requests; i++) {
          const response = await axios({
            url,
            method: method.toLowerCase(),
            headers,
            data: body,
            validateStatus: () => true,
            timeout: 15000,
          });
          statuses.push(response.status);
          if (response.status === 429) rateLimited++;
        }

        await saveTestResult(url, 'api_rate_limit_test', true, { statuses, rateLimited });

        return formatToolResult(true, {
          requests,
          rateLimited,
          statuses,
          likelyProtected: rateLimited > 0,
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Mass assignment testing
  server.tool(
    'api.mass_assignment_test',
    {
      description: 'Test mass assignment behavior',
      inputSchema: {
        type: 'object',
        properties: {
          url: { type: 'string' },
          method: { type: 'string', enum: ['POST', 'PUT', 'PATCH'], default: 'POST' },
          headers: { type: 'object' },
          baselineBody: { type: 'object' },
          testBody: { type: 'object' },
        },
        required: ['url', 'baselineBody'],
      },
    },
    async ({ url, method = 'POST', headers = {}, baselineBody, testBody }: any): Promise<ToolResult> => {
      try {
        const injected = testBody || { ...baselineBody, role: 'admin', isAdmin: true, privileges: ['admin'] };

        const baselineResp = await axios({
          url,
          method: method.toLowerCase(),
          headers: { 'Content-Type': 'application/json', ...headers },
          data: baselineBody,
          validateStatus: () => true,
          timeout: 15000,
        });

        const testResp = await axios({
          url,
          method: method.toLowerCase(),
          headers: { 'Content-Type': 'application/json', ...headers },
          data: injected,
          validateStatus: () => true,
          timeout: 15000,
        });

        const testBodyText = typeof testResp.data === 'string' ? testResp.data : JSON.stringify(testResp.data);
        const suspicious =
          testBodyText.includes('"role":"admin"') ||
          testBodyText.includes('"isAdmin":true') ||
          testBodyText.includes('"privileges"');

        if (suspicious) {
          await saveFinding({
            target: url,
            type: 'Mass Assignment',
            severity: 'high',
            description: 'Potential mass assignment - injected fields reflected/accepted',
            payload: JSON.stringify(injected).substring(0, 1000),
            response: testBodyText.substring(0, 1000),
            timestamp: new Date(),
            score: 7,
          });
        }

        await saveTestResult(url, 'api_mass_assignment_test', true, { suspicious });

        return formatToolResult(true, {
          baselineStatus: baselineResp.status,
          testStatus: testResp.status,
          suspicious,
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // BOLA testing
  server.tool(
    'api.bola_test',
    {
      description: 'Test BOLA/IDOR on API endpoints',
      inputSchema: {
        type: 'object',
        properties: {
          url: { type: 'string' },
          idParam: { type: 'string', default: 'id' },
          ids: { type: 'array', items: { type: 'string' } },
          headers: { type: 'object' },
        },
        required: ['url', 'ids'],
      },
    },
    async ({ url, idParam = 'id', ids, headers = {} }: any): Promise<ToolResult> => {
      try {
        const results: any[] = [];
        let baseline: any | null = null;

        for (const id of ids) {
          const response = await axios.get(url, {
            params: { [idParam]: id },
            headers,
            validateStatus: () => true,
            timeout: 15000,
          });

          if (!baseline) baseline = response;

          const different =
            response.status !== baseline.status ||
            JSON.stringify(response.data) !== JSON.stringify(baseline.data);

          results.push({ id, status: response.status, different });

          if (different && response.status === 200) {
            await saveFinding({
              target: url,
              type: 'BOLA/IDOR',
              severity: 'high',
              description: `Potential BOLA/IDOR on ${idParam}=${id}`,
              payload: `${idParam}=${id}`,
              response: JSON.stringify(response.data).substring(0, 1000),
              timestamp: new Date(),
              score: 7,
            });
          }
        }

        await saveTestResult(url, 'api_bola_test', true, { results });

        return formatToolResult(true, { results });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Swagger/OpenAPI enumeration
  server.tool(
    'api.swagger_enum',
    {
      description: 'Probe for Swagger/OpenAPI docs',
      inputSchema: {
        type: 'object',
        properties: {
          baseUrl: { type: 'string' },
          paths: { type: 'array', items: { type: 'string' } },
        },
        required: ['baseUrl'],
      },
    },
    async ({ baseUrl, paths = [] }: any): Promise<ToolResult> => {
      try {
        const common = [
          '/swagger.json',
          '/openapi.json',
          '/api-docs',
          '/v2/api-docs',
          '/swagger/v1/swagger.json',
        ];

        const candidates = [...new Set([...common, ...paths])];
        const results: any[] = [];

        for (const p of candidates) {
          const url = baseUrl.replace(/\/$/, '') + p;
          const response = await axios.get(url, { validateStatus: () => true, timeout: 15000 });
          const body = typeof response.data === 'string' ? response.data : JSON.stringify(response.data);
          const looksLikeOpenApi = body.includes('"openapi"') || body.includes('"swagger"');

          results.push({ path: p, status: response.status, openApi: looksLikeOpenApi });
        }

        return formatToolResult(true, { results });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );
}
