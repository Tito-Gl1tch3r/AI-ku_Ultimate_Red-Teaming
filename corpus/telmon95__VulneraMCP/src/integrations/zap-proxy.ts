import { IncomingMessage, ServerResponse } from 'http';
import { ZAPClient, ZAPAlert } from './zap';
import { saveTestResult } from './postgres';

export interface ProxyRequest {
  method: string;
  url: string;
  headers: Record<string, string>;
  body?: string;
  timestamp: number;
}

export interface ProxyResponse {
  statusCode: number;
  headers: Record<string, string>;
  body: string;
  timestamp: number;
}

export interface EnhancedFinding {
  zapAlert?: ZAPAlert;
  customFinding?: {
    type: string;
    severity: 'low' | 'medium' | 'high' | 'critical';
    confidence: number;
    description: string;
    evidence: string;
    url: string;
    param?: string;
  };
  correlationScore: number;
  aiScore?: number;
  verified: boolean;
}

/**
 * MCP Proxy Layer
 * Intercepts requests, enhances them, routes through ZAP, and adds AI intelligence
 */
export class MCPProxyLayer {
  private zapClient: ZAPClient;
  private requestHistory: ProxyRequest[] = [];
  private responseHistory: Map<string, ProxyResponse> = new Map();
  private customFindings: EnhancedFinding[] = [];

  constructor(zapClient: ZAPClient) {
    this.zapClient = zapClient;
  }

  /**
   * Process incoming request through proxy
   */
  async processRequest(
    method: string,
    url: string,
    headers: Record<string, string>,
    body?: string
  ): Promise<{ request: ProxyRequest; response?: ProxyResponse; findings: EnhancedFinding[] }> {
    const request: ProxyRequest = {
      method,
      url,
      headers,
      body,
      timestamp: Date.now(),
    };

    // Store request
    this.requestHistory.push(request);
    const requestId = `${method}_${url}_${Date.now()}`;

    // Send through ZAP
    const zapResponse = await this.zapClient.sendRequest(url, method, headers, body);
    
    // Extract response if available
    let response: ProxyResponse | undefined;
    if (zapResponse.success && zapResponse.data) {
      // Parse ZAP response format
      response = {
        statusCode: zapResponse.data.statusCode || 200,
        headers: zapResponse.data.headers || {},
        body: zapResponse.data.body || '',
        timestamp: Date.now(),
      };
      this.responseHistory.set(requestId, response);
    }

    // Analyze for custom findings
    const customFindings = await this.analyzeRequest(request, response);

    // Get ZAP alerts for this URL
    const zapAlerts = await this.getZAPAlertsForURL(url);

    // Correlate findings
    const findings = this.correlateFindings(zapAlerts, customFindings, url);

    return {
      request,
      response,
      findings,
    };
  }

  /**
   * Analyze request for custom vulnerabilities
   */
  private async analyzeRequest(
    request: ProxyRequest,
    response?: ProxyResponse
  ): Promise<EnhancedFinding[]> {
    const findings: EnhancedFinding[] = [];

    // 1. Check for sensitive parameters
    const sensitiveParams = this.detectSensitiveParameters(request);
    if (sensitiveParams.length > 0) {
      findings.push({
        customFinding: {
          type: 'sensitive_parameter_exposure',
          severity: 'medium',
          confidence: 0.7,
          description: `Sensitive parameters detected: ${sensitiveParams.join(', ')}`,
          evidence: JSON.stringify(request),
          url: request.url,
          param: sensitiveParams.join(', '),
        },
        correlationScore: 0.7,
        verified: false,
      });
    }

    // 2. Check for authentication bypass patterns
    if (response && this.detectAuthBypass(request, response)) {
      findings.push({
        customFinding: {
          type: 'authentication_bypass',
          severity: 'high',
          confidence: 0.6,
          description: 'Potential authentication bypass detected',
          evidence: `Request: ${JSON.stringify(request)}, Response: ${JSON.stringify(response)}`,
          url: request.url,
        },
        correlationScore: 0.6,
        verified: false,
      });
    }

    // 3. Check for IDOR patterns
    if (this.detectIDOR(request)) {
      findings.push({
        customFinding: {
          type: 'idor',
          severity: 'high',
          confidence: 0.5,
          description: 'Potential IDOR vulnerability - user-controlled resource ID',
          evidence: JSON.stringify(request),
          url: request.url,
        },
        correlationScore: 0.5,
        verified: false,
      });
    }

    // 4. Check for business logic flaws
    if (this.detectBusinessLogicFlaw(request)) {
      findings.push({
        customFinding: {
          type: 'business_logic_flaw',
          severity: 'medium',
          confidence: 0.6,
          description: 'Potential business logic vulnerability detected',
          evidence: JSON.stringify(request),
          url: request.url,
        },
        correlationScore: 0.6,
        verified: false,
      });
    }

    // 5. Check for missing security headers
    if (response && this.detectMissingSecurityHeaders(response)) {
      findings.push({
        customFinding: {
          type: 'missing_security_headers',
          severity: 'low',
          confidence: 0.8,
          description: 'Missing security headers (CSP, HSTS, X-Frame-Options, etc.)',
          evidence: JSON.stringify(response.headers),
          url: request.url,
        },
        correlationScore: 0.8,
        verified: true,
      });
    }

    return findings;
  }

  /**
   * Detect sensitive parameters in request
   */
  private detectSensitiveParameters(request: ProxyRequest): string[] {
    const sensitiveKeywords = [
      'admin', 'role', 'permission', 'token', 'auth', 'password', 'secret',
      'key', 'api_key', 'access_token', 'userId', 'user_id', 'id', 'amount',
      'price', 'discount', 'privilege', 'privileges', 'isAdmin', 'is_admin',
    ];

    const found: string[] = [];
    const urlLower = request.url.toLowerCase();
    const bodyLower = request.body?.toLowerCase() || '';

    for (const keyword of sensitiveKeywords) {
      if (urlLower.includes(keyword) || bodyLower.includes(keyword)) {
        found.push(keyword);
      }
    }

    return found;
  }

  /**
   * Detect potential authentication bypass
   */
  private detectAuthBypass(request: ProxyRequest, response: ProxyResponse): boolean {
    // Check if request without auth headers gets 200 OK
    if (response.statusCode === 200 && !request.headers['Authorization'] && !request.headers['Cookie']) {
      // Check if URL looks like it should require auth
      const protectedPaths = ['/api/admin', '/api/user', '/api/account', '/dashboard', '/admin'];
      return protectedPaths.some(path => request.url.includes(path));
    }
    return false;
  }

  /**
   * Detect IDOR patterns
   */
  private detectIDOR(request: ProxyRequest): boolean {
    // Check for numeric IDs in URL or body
    const idPattern = /\/(\d+)\//g;
    const urlMatches = request.url.match(idPattern);
    const bodyMatches = request.body?.match(idPattern);

    if (urlMatches || bodyMatches) {
      // Check if it's a user-related endpoint
      const userPatterns = ['/user/', '/account/', '/profile/', '/order/', '/transaction/'];
      return userPatterns.some(pattern => request.url.includes(pattern));
    }
    return false;
  }

  /**
   * Detect business logic flaws
   */
  private detectBusinessLogicFlaw(request: ProxyRequest): boolean {
    // Check for suspicious operations
    const suspiciousPatterns = [
      { method: 'POST', path: '/refund', param: 'amount' },
      { method: 'PUT', path: '/price', param: 'amount' },
      { method: 'DELETE', path: '/order', param: 'id' },
      { method: 'POST', path: '/transfer', param: 'amount' },
    ];

    return suspiciousPatterns.some(pattern => {
      return request.method === pattern.method &&
             request.url.includes(pattern.path) &&
             (request.url.includes(pattern.param) || request.body?.includes(pattern.param));
    });
  }

  /**
   * Detect missing security headers
   */
  private detectMissingSecurityHeaders(response: ProxyResponse): boolean {
    const requiredHeaders = [
      'Content-Security-Policy',
      'X-Frame-Options',
      'X-Content-Type-Options',
      'Strict-Transport-Security',
    ];

    const missing = requiredHeaders.filter(header => !response.headers[header]);
    return missing.length > 0;
  }

  /**
   * Get ZAP alerts for a specific URL
   */
  private async getZAPAlertsForURL(url: string): Promise<ZAPAlert[]> {
    const result = await this.zapClient.getAlerts(url);
    if (result.success && result.data) {
      return result.data.alerts || [];
    }
    return [];
  }

  /**
   * Correlate ZAP alerts with custom findings
   */
  private correlateFindings(
    zapAlerts: ZAPAlert[],
    customFindings: EnhancedFinding[],
    url: string
  ): EnhancedFinding[] {
    const correlated: EnhancedFinding[] = [];

    // Add ZAP alerts
    for (const alert of zapAlerts) {
      correlated.push({
        zapAlert: alert,
        correlationScore: this.calculateCorrelationScore(alert),
        verified: alert.confidence === 'High' || alert.confidence === 'Confirmed',
      });
    }

    // Add custom findings
    for (const finding of customFindings) {
      // Check if ZAP already found something similar
      const similarZAPAlert = zapAlerts.find(alert => 
        this.areFindingsSimilar(alert, finding.customFinding)
      );

      if (similarZAPAlert) {
        // Merge findings
        correlated.push({
          zapAlert: similarZAPAlert,
          customFinding: finding.customFinding,
          correlationScore: Math.max(
            this.calculateCorrelationScore(similarZAPAlert),
            finding.correlationScore
          ),
          verified: true,
        });
      } else {
        // Add as new finding
        correlated.push(finding);
      }
    }

    // Calculate AI scores
    return correlated.map(finding => ({
      ...finding,
      aiScore: this.calculateAIScore(finding),
    }));
  }

  /**
   * Calculate correlation score for a finding
   */
  private calculateCorrelationScore(alert: ZAPAlert): number {
    const riskScores: Record<ZAPAlert['risk'], number> = {
      'Informational': 0.2,
      'Low': 0.4,
      'Medium': 0.6,
      'High': 0.8,
      'Critical': 1.0,
    };

    const confidenceScores: Record<ZAPAlert['confidence'], number> = {
      'False Positive': 0.0,
      'Low': 0.3,
      'Medium': 0.6,
      'High': 0.8,
      'Confirmed': 1.0,
    };

    return (riskScores[alert.risk] || 0) * (confidenceScores[alert.confidence] || 0);
  }

  /**
   * Check if findings are similar
   */
  private areFindingsSimilar(zapAlert: ZAPAlert, customFinding?: EnhancedFinding['customFinding']): boolean {
    if (!customFinding) return false;

    // Simple similarity check based on URL and type
    return zapAlert.url === customFinding.url &&
           this.mapVulnerabilityTypes(zapAlert.name) === customFinding.type;
  }

  /**
   * Map ZAP alert names to our vulnerability types
   */
  private mapVulnerabilityTypes(zapAlertName: string): string {
    const name = zapAlertName.toLowerCase();
    if (name.includes('xss')) return 'xss';
    if (name.includes('sql')) return 'sqli';
    if (name.includes('csrf')) return 'csrf';
    if (name.includes('idor')) return 'idor';
    if (name.includes('auth')) return 'authentication_bypass';
    return 'unknown';
  }

  /**
   * Calculate AI-powered score
   */
  private calculateAIScore(finding: EnhancedFinding): number {
    let score = finding.correlationScore;

    // Boost score if both ZAP and custom finding agree
    if (finding.zapAlert && finding.customFinding) {
      score *= 1.3;
    }

    // Boost score if verified
    if (finding.verified) {
      score *= 1.2;
    }

    return Math.min(score, 1.0);
  }

  /**
   * Get all findings
   */
  getFindings(): EnhancedFinding[] {
    return this.customFindings;
  }

  /**
   * Clear findings
   */
  clearFindings(): void {
    this.customFindings = [];
    this.requestHistory = [];
    this.responseHistory.clear();
  }
}




