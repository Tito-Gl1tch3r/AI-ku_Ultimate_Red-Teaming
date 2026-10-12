import { Server } from '../mcp/server';
import { formatToolResult, ToolResult } from '../types';
import { saveTrainingData } from '../integrations/postgres';

// Pre-loaded training data from Intigriti CSRF guide and other sources
const CSRF_TRAINING_DATA = [
  {
    source: 'intigriti',
    sourceId: 'csrf-basic',
    vulnerabilityType: 'CSRF',
    targetPattern: '/api/profile/update',
    payloadPattern: '<form method="POST"',
    successPattern: 'email updated|profile updated|success',
    failurePattern: 'error|invalid|unauthorized',
    contextData: {
      technique: 'Basic CSRF',
      description: 'Simple form-based CSRF attack',
      example: '<form method="POST" action="https://app.example.com/api/profile/update">',
    },
    score: 7,
  },
  {
    source: 'intigriti',
    sourceId: 'csrf-content-type',
    vulnerabilityType: 'CSRF',
    targetPattern: '/api/',
    payloadPattern: 'enctype="text/plain"',
    successPattern: 'success|updated',
    failurePattern: 'error|invalid content-type',
    contextData: {
      technique: 'Content-Type Bypass',
      description: 'Bypass JSON-only APIs using text/plain',
      example: 'enctype="text/plain" with JSON-like payload',
    },
    score: 8,
  },
  {
    source: 'intigriti',
    sourceId: 'csrf-method',
    vulnerabilityType: 'CSRF',
    targetPattern: '/api/',
    payloadPattern: 'method="POST"|_method=PUT',
    successPattern: 'success|updated',
    failurePattern: 'method not allowed|cors error',
    contextData: {
      technique: 'Method-based CSRF',
      description: 'Change HTTP method to bypass CORS',
      example: 'Use POST instead of PUT/PATCH',
    },
    score: 7,
  },
  {
    source: 'intigriti',
    sourceId: 'csrf-token-bypass',
    vulnerabilityType: 'CSRF',
    targetPattern: '/api/',
    payloadPattern: 'csrf_token=|anti-csrf',
    successPattern: 'success|updated',
    failurePattern: 'invalid token|csrf required',
    contextData: {
      technique: 'Token Validation Bypass',
      description: 'Bypass anti-CSRF tokens',
      methods: ['remove token', 'blank value', 'random value', 'hardcoded valid token'],
    },
    score: 9,
  },
  {
    source: 'intigriti',
    sourceId: 'csrf-referrer',
    vulnerabilityType: 'CSRF',
    targetPattern: '/api/',
    payloadPattern: 'no-referrer',
    successPattern: 'success|updated',
    failurePattern: 'invalid referrer|referrer required',
    contextData: {
      technique: 'Referrer-based Bypass',
      description: 'Bypass referrer validation',
      example: '<meta name="referrer" content="no-referrer">',
    },
    score: 8,
  },
];

const XSS_TRAINING_DATA = [
  {
    source: 'portswigger',
    sourceId: 'xss-reflected-basic',
    vulnerabilityType: 'XSS',
    targetPattern: '/search|/query|?q=|?search=',
    payloadPattern: '<script>alert|"><script>|javascript:',
    successPattern: 'alert|script|onerror',
    failurePattern: 'filtered|blocked|sanitized',
    contextData: {
      technique: 'Reflected XSS',
      description: 'Basic reflected XSS in search parameters',
    },
    score: 7,
  },
  {
    source: 'portswigger',
    sourceId: 'xss-dom',
    vulnerabilityType: 'XSS',
    targetPattern: 'document.write|innerHTML|eval(',
    payloadPattern: '#|location.hash|window.name',
    successPattern: 'alert|XSS|payload executed',
    failurePattern: 'sanitized|filtered',
    contextData: {
      technique: 'DOM-based XSS',
      description: 'XSS via DOM manipulation',
    },
    score: 8,
  },
];

const SQLI_TRAINING_DATA = [
  {
    source: 'portswigger',
    sourceId: 'sqli-basic',
    vulnerabilityType: 'SQL Injection',
    targetPattern: '?id=|?user=|?product=',
    payloadPattern: "' OR '1'='1|' UNION SELECT|' AND SLEEP",
    successPattern: 'sql syntax|mysql|postgresql|database error',
    failurePattern: 'parameterized|prepared statement',
    contextData: {
      technique: 'Basic SQL Injection',
      description: 'Classic SQL injection patterns',
    },
    score: 9,
  },
  {
    source: 'portswigger',
    sourceId: 'sqli-time-based',
    vulnerabilityType: 'SQL Injection',
    targetPattern: '?id=',
    payloadPattern: 'SLEEP|WAITFOR|BENCHMARK',
    successPattern: 'delayed response|timeout|> 5 seconds',
    failurePattern: 'immediate response|no delay',
    contextData: {
      technique: 'Time-based SQL Injection',
      description: 'Blind SQL injection using time delays',
    },
    score: 8,
  },
];

const REGISTRATION_TRAINING_DATA = [
  {
    source: 'infosecwriteups',
    sourceId: 'registration-email-enum',
    vulnerabilityType: 'User Enumeration',
    targetPattern: '/register|/signup|/api/register',
    payloadPattern: 'email=|username=',
    successPattern: 'already exists|taken|registered',
    failurePattern: 'available|success|created',
    contextData: {
      technique: 'Email/Username Enumeration',
      description: 'Enumerate existing users during registration',
    },
    score: 6,
  },
  {
    source: 'infosecwriteups',
    sourceId: 'registration-weak-validation',
    vulnerabilityType: 'Weak Validation',
    targetPattern: '/register|/signup',
    payloadPattern: 'email=admin@|username=admin',
    successPattern: 'success|created|registered',
    failurePattern: 'invalid|forbidden|reserved',
    contextData: {
      technique: 'Weak Input Validation',
      description: 'Bypass registration restrictions',
    },
    score: 7,
  },
];

const GOOGLE_DORKING_PATTERNS = [
  {
    source: 'medium',
    sourceId: 'dork-filetype',
    vulnerabilityType: 'Information Disclosure',
    targetPattern: 'filetype:pdf|filetype:doc|filetype:xls',
    payloadPattern: 'site:target.com filetype:',
    successPattern: 'results found|files indexed',
    failurePattern: 'no results',
    contextData: {
      technique: 'Filetype Dorking',
      description: 'Find specific file types on target',
      examples: ['filetype:pdf', 'filetype:doc', 'filetype:xls'],
    },
    score: 5,
  },
  {
    source: 'medium',
    sourceId: 'dork-inurl',
    vulnerabilityType: 'Information Disclosure',
    targetPattern: 'inurl:admin|inurl:login|inurl:api',
    payloadPattern: 'site:target.com inurl:',
    successPattern: 'admin panel|login page|api endpoint',
    failurePattern: 'no results',
    contextData: {
      technique: 'InURL Dorking',
      description: 'Find specific URL patterns',
      examples: ['inurl:admin', 'inurl:login', 'inurl:api'],
    },
    score: 6,
  },
  {
    source: 'medium',
    sourceId: 'dork-intitle',
    vulnerabilityType: 'Information Disclosure',
    targetPattern: 'intitle:"index of"|intitle:"directory listing"',
    payloadPattern: 'site:target.com intitle:',
    successPattern: 'directory listing|index of',
    failurePattern: 'no results',
    contextData: {
      technique: 'InTitle Dorking',
      description: 'Find pages with specific titles',
    },
    score: 5,
  },
];

export function registerTrainingExtractorTools(server: Server) {
  // Import all pre-loaded training data
  server.tool(
    'training.import_all',
    {
      description: 'Import all pre-loaded training data from Intigriti, PortSwigger, and other sources',
      inputSchema: {
        type: 'object',
        properties: {
          sources: {
            type: 'array',
            items: { type: 'string' },
            description: 'Sources to import (csrf, xss, sqli, registration, dorking, all)',
            default: ['all'],
          },
        },
      },
    },
    async ({ sources = ['all'] }: any): Promise<ToolResult> => {
      try {
        const allData: any[] = [];
        const importSources = sources.includes('all')
          ? ['csrf', 'xss', 'sqli', 'registration', 'dorking']
          : sources;

        if (importSources.includes('csrf')) {
          allData.push(...CSRF_TRAINING_DATA);
        }
        if (importSources.includes('xss')) {
          allData.push(...XSS_TRAINING_DATA);
        }
        if (importSources.includes('sqli')) {
          allData.push(...SQLI_TRAINING_DATA);
        }
        if (importSources.includes('registration')) {
          allData.push(...REGISTRATION_TRAINING_DATA);
        }
        if (importSources.includes('dorking')) {
          allData.push(...GOOGLE_DORKING_PATTERNS);
        }

        const imported: number[] = [];
        for (const data of allData) {
          try {
            const id = await saveTrainingData(
              data.source,
              data.sourceId,
              data.vulnerabilityType,
              data.targetPattern,
              data.payloadPattern,
              data.successPattern,
              data.failurePattern,
              data.contextData,
              data.score
            );
            imported.push(id);
          } catch (error: any) {
            console.error(`Error importing ${data.sourceId}:`, error.message);
          }
        }

        return formatToolResult(true, {
          imported: imported.length,
          total: allData.length,
          ids: imported,
          sources: importSources,
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Extract patterns from bug bounty writeup text
  server.tool(
    'training.extract_from_writeup',
    {
      description: 'Extract training patterns from bug bounty writeup text',
      inputSchema: {
        type: 'object',
        properties: {
          writeupText: { type: 'string', description: 'Bug bounty writeup text' },
          vulnerabilityType: { type: 'string', description: 'Type of vulnerability' },
          source: { type: 'string', description: 'Source of writeup', default: 'custom' },
        },
        required: ['writeupText', 'vulnerabilityType'],
      },
    },
    async (params: any): Promise<ToolResult> => {
      try {
        const text = params.writeupText.toLowerCase();
        const vulnType = params.vulnerabilityType;

        // Extract URLs/endpoints
        const urlPattern = /https?:\/\/[^\s"<>]+/gi;
        const urls = text.match(urlPattern) || [];
        const targetPattern = urls[0]?.split('?')[0] || '';

        // Extract payloads
        const payloadPatterns = [
          /payload[:\s]+([^\n]+)/gi,
          /exploit[:\s]+([^\n]+)/gi,
          /<script[^>]*>([^<]+)<\/script>/gi,
          /'[^']*'/g,
          /"[^"]*"/g,
        ];

        let payloadPattern = '';
        for (const pattern of payloadPatterns) {
          const matches = text.match(pattern);
          if (matches && matches.length > 0) {
            payloadPattern = matches[0].substring(0, 100);
            break;
          }
        }

        // Extract success indicators
        const successPatterns = [
          /success|vulnerable|exploited|confirmed|poc|proof of concept/gi,
          /alert\(|xss|injection|bypass/gi,
        ];
        let successPattern = 'success|vulnerable|exploited';
        for (const pattern of successPatterns) {
          if (pattern.test(text)) {
            successPattern = pattern.source.replace(/[\\^$.*+?()[\]{}|]/g, '');
            break;
          }
        }

        // Extract failure indicators
        const failurePattern = 'error|blocked|filtered|sanitized';

        // Calculate score based on keywords
        let score = 5;
        if (text.includes('critical') || text.includes('rce') || text.includes('takeover')) {
          score = 10;
        } else if (text.includes('high') || text.includes('sql injection') || text.includes('auth bypass')) {
          score = 9;
        } else if (text.includes('xss') || text.includes('csrf')) {
          score = 7;
        }

        const id = await saveTrainingData(
          params.source || 'custom',
          `writeup-${Date.now()}`,
          vulnType,
          targetPattern,
          payloadPattern,
          successPattern,
          failurePattern,
          { extractedFrom: 'writeup', originalText: params.writeupText.substring(0, 500) },
          score
        );

        return formatToolResult(true, {
          id,
          extracted: {
            targetPattern,
            payloadPattern,
            successPattern,
            failurePattern,
            score,
          },
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Get CSRF-specific training data
  server.tool(
    'training.get_csrf_patterns',
    {
      description: 'Get all CSRF exploitation patterns from training data',
      inputSchema: {
        type: 'object',
        properties: {
          technique: {
            type: 'string',
            enum: ['basic', 'content-type', 'method', 'token-bypass', 'referrer', 'all'],
            description: 'Specific CSRF technique',
            default: 'all',
          },
        },
      },
    },
    async ({ technique = 'all' }: any): Promise<ToolResult> => {
      try {
        let patterns = CSRF_TRAINING_DATA;
        if (technique !== 'all') {
          patterns = patterns.filter((p) => p.sourceId.includes(technique));
        }

        return formatToolResult(true, {
          patterns,
          count: patterns.length,
          techniques: patterns.map((p) => p.contextData.technique),
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );
}









