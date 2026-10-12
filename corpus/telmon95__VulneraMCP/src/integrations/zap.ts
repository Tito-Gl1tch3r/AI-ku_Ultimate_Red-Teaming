import axios, { AxiosInstance } from 'axios';

export interface ZAPScanResult {
  success: boolean;
  data?: any;
  error?: string;
}

export interface ZAPSpiderResult {
  scanId: string;
  progress: number;
  status: string;
}

export interface ZAPActiveScanResult {
  scanId: string;
  progress: number;
  status: string;
}

export interface ZAPAlert {
  id: string;
  name: string;
  risk: 'Informational' | 'Low' | 'Medium' | 'High' | 'Critical';
  confidence: 'False Positive' | 'Low' | 'Medium' | 'High' | 'Confirmed';
  url: string;
  param?: string;
  attack?: string;
  evidence?: string;
  description?: string;
  solution?: string;
  reference?: string;
}

export interface ZAPContext {
  id: number;
  name: string;
  urls: string[];
}

/**
 * ZAP API Integration
 * Connects to OWASP ZAP via REST API
 */
export class ZAPClient {
  private client: AxiosInstance;
  private baseURL: string;
  private apiKey?: string;

  constructor(baseURL: string = 'http://localhost:8081', apiKey?: string) {
    this.baseURL = baseURL.replace(/\/$/, '');
    this.apiKey = apiKey || process.env.ZAP_API_KEY;
    
    this.client = axios.create({
      baseURL: `${this.baseURL}/JSON`,
      timeout: 30000,
    });

    this.client.interceptors.request.use((config) => {
      config.params = {
        ...(config.params || {}),
        ...(this.apiKey ? { apikey: this.apiKey } : {}),
      };
      return config;
    });
  }

  /**
   * Check if ZAP is running and accessible
   */
  async healthCheck(): Promise<ZAPScanResult> {
    try {
      const response = await this.client.get('/core/view/version/');
      return {
        success: true,
        data: {
          version: response.data.version,
          status: 'running',
        },
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'ZAP is not accessible',
      };
    }
  }

  /**
   * Start a spider scan
   */
  async startSpider(url: string, maxChildren?: number, recurse?: boolean, contextName?: string): Promise<ZAPScanResult> {
    try {
      const params: any = { url };
      if (maxChildren) params.maxChildren = maxChildren;
      if (recurse !== undefined) params.recurse = recurse;
      if (contextName) params.contextName = contextName;

      const response = await this.client.get('/spider/action/scan/', { params });
      
      // Handle different response formats
      const scanId = response.data.scan || response.data.scanId || response.data;
      if (!scanId && scanId !== 0) {
        throw new Error('No scan ID returned from ZAP');
      }
      
      return {
        success: true,
        data: {
          scanId: scanId.toString(),
        },
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to start spider scan',
      };
    }
  }

  /**
   * Get spider scan status
   */
  async getSpiderStatus(scanId: string): Promise<ZAPScanResult> {
    try {
      const response = await this.client.get('/spider/view/status/', {
        params: { scanId: scanId.toString() },
      });
      return {
        success: true,
        data: {
          scanId,
          progress: parseInt(response.data.status || '0') || 0,
          status: response.data.status === '100' ? 'completed' : 'running',
        },
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to get spider status',
      };
    }
  }

  /**
   * Start an active scan
   */
  async startActiveScan(url: string, recurse?: boolean, inScopeOnly?: boolean, scanPolicyName?: string, method?: string, postData?: string): Promise<ZAPScanResult> {
    try {
      const params: any = { url };
      if (recurse !== undefined) params.recurse = recurse;
      if (inScopeOnly !== undefined) params.inScopeOnly = inScopeOnly;
      if (scanPolicyName) params.scanPolicyName = scanPolicyName;
      if (method) params.method = method;
      if (postData) params.postData = postData;

      const response = await this.client.get('/ascan/action/scan/', { params });
      
      // Handle different response formats
      const scanId = response.data.scan || response.data.scanId || response.data;
      if (!scanId && scanId !== 0) {
        throw new Error('No scan ID returned from ZAP');
      }
      
      return {
        success: true,
        data: {
          scanId: scanId.toString(),
        },
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to start active scan',
      };
    }
  }

  /**
   * Get active scan status
   */
  async getActiveScanStatus(scanId: string): Promise<ZAPScanResult> {
    try {
      const response = await this.client.get('/ascan/view/status/', {
        params: { scanId: scanId.toString() },
      });
      return {
        success: true,
        data: {
          scanId,
          progress: parseInt(response.data.status || '0') || 0,
          status: response.data.status === '100' ? 'completed' : 'running',
        },
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to get active scan status',
      };
    }
  }

  /**
   * Get all alerts
   */
  async getAlerts(baseURL?: string, start?: number, count?: number, riskId?: string): Promise<ZAPScanResult> {
    try {
      const params: any = {};
      if (baseURL) params.baseurl = baseURL;
      if (start !== undefined) params.start = start;
      if (count !== undefined) params.count = count;
      if (riskId) params.riskId = riskId;

      const response = await this.client.get('/alert/view/alerts/', { params });
      
      // Handle both array format and object format responses
      let alertsData: any[] = [];
      if (Array.isArray(response.data.alerts)) {
        alertsData = response.data.alerts;
      } else if (response.data.alerts && typeof response.data.alerts === 'object') {
        // If alerts is an object, convert to array
        alertsData = Object.values(response.data.alerts);
      } else if (Array.isArray(response.data)) {
        // Some ZAP versions return alerts directly as array
        alertsData = response.data;
      }
      
      const alerts: ZAPAlert[] = alertsData.map((alert: any) => ({
        id: alert.pluginId?.toString() || alert.id?.toString() || '',
        name: alert.alert || alert.name || 'Unknown Alert',
        risk: this.mapRisk(alert.risk || alert.riskString || 'Informational'),
        confidence: this.mapConfidence(alert.confidence || alert.confidenceString || 'Low'),
        url: alert.url || '',
        param: alert.param || undefined,
        attack: alert.attack || undefined,
        evidence: alert.evidence || undefined,
        description: alert.description || undefined,
        solution: alert.solution || undefined,
        reference: alert.reference || undefined,
      }));

      return {
        success: true,
        data: {
          alerts,
          count: alerts.length,
        },
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to get alerts',
      };
    }
  }

  /**
   * Get alerts summary (counts by risk level)
   */
  async getAlertsSummary(baseURL?: string): Promise<ZAPScanResult> {
    try {
      const params: any = {};
      if (baseURL) params.baseurl = baseURL;

      const response = await this.client.get('/alert/view/alertCountsByRisk/', { params });
      
      // Parse the response - ZAP returns alertCountsByRisk with risk levels as keys
      const summaryData = response.data.alertCountsByRisk || response.data;
      
      return {
        success: true,
        data: {
          informational: summaryData['0'] || summaryData.Informational || 0,
          low: summaryData['1'] || summaryData.Low || 0,
          medium: summaryData['2'] || summaryData.Medium || 0,
          high: summaryData['3'] || summaryData.High || 0,
          critical: summaryData['4'] || summaryData.Critical || 0,
          raw: summaryData,
        },
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to get alerts summary',
      };
    }
  }

  /**
   * Send a custom HTTP request through ZAP
   * Note: ZAP requires proxying through ZAP proxy. Use /core/action/sendRequest/ for direct API calls
   */
  async sendRequest(url: string, method: string = 'GET', headers?: Record<string, string>, body?: string): Promise<ZAPScanResult> {
    try {
      const params: any = { url, method };
      if (headers) {
        // ZAP expects headers as a string in format "HeaderName: HeaderValue"
        params.headers = Object.entries(headers)
          .filter(([k]) => k.toLowerCase() !== 'content-length') // Remove content-length, ZAP will add it
          .map(([k, v]) => `${k}: ${v}`)
          .join('\n');
      }
      if (body) params.body = body;

      // Try /core/action/sendRequest/ first, fallback to /httpSender/action/sendRequest/
      try {
        const response = await this.client.get('/core/action/sendRequest/', { params });
        return {
          success: true,
          data: response.data,
        };
      } catch (coreError: any) {
        // Fallback to httpSender endpoint
        const response = await this.client.get('/httpSender/action/sendRequest/', { params });
        return {
          success: true,
          data: response.data,
        };
      }
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to send request',
      };
    }
  }

  /**
   * Create a context for scanning
   */
  async createContext(contextName: string): Promise<ZAPScanResult> {
    try {
      const response = await this.client.get('/context/action/newContext/', {
        params: { contextName },
      });
      return {
        success: true,
        data: {
          contextId: parseInt(response.data.contextId),
          name: contextName,
        },
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to create context',
      };
    }
  }

  /**
   * Include URL in context
   * Note: ZAP API accepts contextName or contextId. We use contextName here.
   */
  async includeInContext(contextName: string, regex: string): Promise<ZAPScanResult> {
    try {
      // First try with contextName, if that fails and we have a numeric contextName, try as contextId
      try {
        const response = await this.client.get('/context/action/includeInContext/', {
          params: { contextName, regex },
        });
        return {
          success: true,
          data: response.data,
        };
      } catch (error: any) {
        // If contextName fails and it's numeric, try as contextId
        if (!isNaN(Number(contextName))) {
          const response = await this.client.get('/context/action/includeInContext/', {
            params: { contextId: contextName, regex },
          });
          return {
            success: true,
            data: response.data,
          };
        }
        throw error;
      }
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to include URL in context',
      };
    }
  }

  /**
   * Set scan policy
   */
  async setScanPolicy(policyName: string, attackStrength?: string, alertThreshold?: string): Promise<ZAPScanResult> {
    try {
      const params: any = { scanPolicyName: policyName };
      if (attackStrength) params.attackStrength = attackStrength;
      if (alertThreshold) params.alertThreshold = alertThreshold;

      const response = await this.client.get('/ascan/action/addScanPolicy/', { params });
      return {
        success: true,
        data: response.data,
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to set scan policy',
      };
    }
  }

  /**
   * Get sites tree (discovered URLs)
   */
  async getSites(): Promise<ZAPScanResult> {
    try {
      const response = await this.client.get('/core/view/sites/');
      return {
        success: true,
        data: {
          sites: response.data.sites || [],
        },
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to get sites',
      };
    }
  }

  /**
   * Get URLs for a specific site
   */
  async getUrls(baseURL?: string): Promise<ZAPScanResult> {
    try {
      const params: any = {};
      if (baseURL) params.baseurl = baseURL;

      const response = await this.client.get('/core/view/urls/', { params });
      return {
        success: true,
        data: {
          urls: response.data.urls || [],
        },
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Failed to get URLs',
      };
    }
  }

  /**
   * Map ZAP risk string to our risk enum
   */
  private mapRisk(risk: string): ZAPAlert['risk'] {
    const riskMap: Record<string, ZAPAlert['risk']> = {
      '0': 'Informational',
      '1': 'Low',
      '2': 'Medium',
      '3': 'High',
      '4': 'Critical',
      'Informational': 'Informational',
      'Low': 'Low',
      'Medium': 'Medium',
      'High': 'High',
      'Critical': 'Critical',
    };
    return riskMap[risk] || 'Informational';
  }

  /**
   * Map ZAP confidence string to our confidence enum
   */
  private mapConfidence(confidence: string): ZAPAlert['confidence'] {
    const confMap: Record<string, ZAPAlert['confidence']> = {
      '0': 'False Positive',
      '1': 'Low',
      '2': 'Medium',
      '3': 'High',
      '4': 'Confirmed',
      'False Positive': 'False Positive',
      'Low': 'Low',
      'Medium': 'Medium',
      'High': 'High',
      'Confirmed': 'Confirmed',
    };
    return confMap[confidence] || 'Low';
  }
}

// Singleton instance
let zapClient: ZAPClient | null = null;

export function initZAP(baseURL?: string, apiKey?: string): ZAPClient {
  if (!zapClient) {
    zapClient = new ZAPClient(
      baseURL || process.env.ZAP_URL || 'http://localhost:8081',
      apiKey || process.env.ZAP_API_KEY
    );
  }
  return zapClient;
}

export function getZAPClient(): ZAPClient | null {
  return zapClient;
}

