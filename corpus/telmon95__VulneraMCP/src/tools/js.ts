import { Server } from '../mcp/server';
import axios from 'axios';
import beautify from 'js-beautify';
import { formatToolResult, ToolResult } from '../types';
import { setWorkingMemory } from '../integrations/redis';

export function registerJsTools(server: Server) {
  // Download JS file
  server.tool(
    'js.download',
    {
      description: 'Download JavaScript file from URL',
      inputSchema: {
        type: 'object',
        properties: {
          url: { type: 'string', description: 'URL of the JS file' },
        },
        required: ['url'],
      },
    },
    async ({ url }: any): Promise<ToolResult> => {
      try {
        const response = await axios.get(url, {
          timeout: 30000,
          headers: {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
          },
        });

        const content = response.data;
        await setWorkingMemory(`js:${url}`, content, 3600);

        return formatToolResult(true, {
          url,
          content,
          length: content.length,
          contentType: response.headers['content-type'],
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Beautify JS
  server.tool(
    'js.beautify',
    {
      description: 'Beautify and format JavaScript source code',
      inputSchema: {
        type: 'object',
        properties: {
          source: { type: 'string', description: 'JavaScript source code' },
          indentSize: { type: 'number', description: 'Indentation size', default: 2 },
        },
        required: ['source'],
      },
    },
    async ({ source, indentSize = 2 }: any): Promise<ToolResult> => {
      try {
        const beautified = beautify.js(source, {
          indent_size: indentSize,
          space_in_empty_paren: true,
          preserve_newlines: true,
        });

        return formatToolResult(true, {
          beautified,
          originalLength: source.length,
          beautifiedLength: beautified.length,
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Find endpoints in JS
  server.tool(
    'js.find_endpoints',
    {
      description: 'Extract API endpoints, URLs, and paths from JavaScript code',
      inputSchema: {
        type: 'object',
        properties: {
          source: { type: 'string', description: 'JavaScript source code' },
        },
        required: ['source'],
      },
    },
    async ({ source }: any): Promise<ToolResult> => {
      try {
        // Find full URLs
        const urlRegex = /\bhttps?:\/\/[\w\-\.:%]+[\w\-\/_\.\?\=\%\&\#]*/g;
        const urls = Array.from(new Set(source.match(urlRegex) || []));

        // Find relative paths
        const pathRegex = /["'`](\/[-a-zA-Z0-9_@:\/\.]+)["'`]/g;
        const paths: string[] = [];
        let match: RegExpExecArray | null;
        while ((match = pathRegex.exec(source)) !== null) {
          paths.push(match[1]);
        }

        // Find API endpoints (common patterns)
        const apiRegex = /(?:api|endpoint|url|path)[\s:=]+["'`]([^"'`]+)["'`]/gi;
        const apiEndpoints: string[] = [];
        while ((match = apiRegex.exec(source)) !== null) {
          apiEndpoints.push(match[1]);
        }

        const uniquePaths = Array.from(new Set(paths));
        const uniqueApis = Array.from(new Set(apiEndpoints));

        return formatToolResult(true, {
          urls,
          paths: uniquePaths,
          apiEndpoints: uniqueApis,
          summary: {
            totalUrls: urls.length,
            totalPaths: uniquePaths.length,
            totalApis: uniqueApis.length,
          },
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Extract secrets/API keys
  server.tool(
    'js.extract_secrets',
    {
      description: 'Heuristically extract potential API keys, tokens, and secrets from JS',
      inputSchema: {
        type: 'object',
        properties: {
          source: { type: 'string', description: 'JavaScript source code' },
        },
        required: ['source'],
      },
    },
    async ({ source }: any): Promise<ToolResult> => {
      try {
        const secrets: any = {
          apiKeys: [],
          tokens: [],
          passwords: [],
          awsKeys: [],
          googleKeys: [],
          candidates: [],
        };

        // API Key patterns
        const apiKeyPatterns = [
          /(?:api[_-]?key|apikey)[\s:=]+["'`]([A-Za-z0-9_\-]{20,})["'`]/gi,
          /(?:secret[_-]?key|secretkey)[\s:=]+["'`]([A-Za-z0-9_\-]{20,})["'`]/gi,
        ];

        // Token patterns
        const tokenPatterns = [
          /(?:token|access[_-]?token)[\s:=]+["'`]([A-Za-z0-9_\-]{20,})["'`]/gi,
          /(?:bearer|authorization)[\s:]+["'`]?([A-Za-z0-9_\-\.]{20,})["'`]?/gi,
        ];

        // AWS keys
        const awsPattern = /AKIA[0-9A-Z]{16}/g;

        // Google API keys
        const googlePattern = /AIza[0-9A-Za-z\-_]{35}/g;

        // Extract matches
        apiKeyPatterns.forEach((pattern) => {
          let match: RegExpExecArray | null;
          while ((match = pattern.exec(source)) !== null) {
            secrets.apiKeys.push(match[1]);
          }
        });

        tokenPatterns.forEach((pattern) => {
          let match: RegExpExecArray | null;
          while ((match = pattern.exec(source)) !== null) {
            secrets.tokens.push(match[1]);
          }
        });

        const awsMatches = source.match(awsPattern) || [];
        secrets.awsKeys = Array.from(new Set(awsMatches));

        const googleMatches = source.match(googlePattern) || [];
        secrets.googleKeys = Array.from(new Set(googleMatches));

        // General long strings that might be secrets
        const candidatePattern = /["'`]([A-Za-z0-9_\-]{32,})["'`]/g;
        let candidateMatch: RegExpExecArray | null;
        while ((candidateMatch = candidatePattern.exec(source)) !== null) {
          const candidate = candidateMatch[1];
          // Filter out URLs and common false positives
          if (
            !candidate.startsWith('http') &&
            !candidate.includes('/') &&
            candidate.length < 200
          ) {
            secrets.candidates.push(candidate);
          }
        }

        // Deduplicate
        secrets.apiKeys = Array.from(new Set(secrets.apiKeys));
        secrets.tokens = Array.from(new Set(secrets.tokens));
        secrets.candidates = Array.from(new Set(secrets.candidates)).slice(0, 50);

        return formatToolResult(true, {
          ...secrets,
          summary: {
            totalApiKeys: secrets.apiKeys.length,
            totalTokens: secrets.tokens.length,
            totalAwsKeys: secrets.awsKeys.length,
            totalGoogleKeys: secrets.googleKeys.length,
            totalCandidates: secrets.candidates.length,
          },
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Analyze JS file from URL
  server.tool(
    'js.analyze',
    {
      description: 'Download, beautify, and analyze a JavaScript file - extract endpoints and secrets',
      inputSchema: {
        type: 'object',
        properties: {
          url: { type: 'string', description: 'URL of the JS file to analyze' },
        },
        required: ['url'],
      },
    },
    async ({ url }: any): Promise<ToolResult> => {
      try {
        // Download
        let source: string;
        try {
          const response = await axios.get(url, {
            timeout: 30000,
            headers: {
              'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            },
          });
          source = response.data;
        } catch (error: any) {
          return formatToolResult(false, null, `Failed to download: ${error.message}`);
        }

        // Beautify
        let beautified: string;
        try {
          beautified = beautify.js(source, {
            indent_size: 2,
            space_in_empty_paren: true,
            preserve_newlines: true,
          });
        } catch {
          beautified = source;
        }

        // Find endpoints
        const urlRegex = /\bhttps?:\/\/[\w\-\.:%]+[\w\-\/_\.\?\=\%\&\#]*/g;
        const urls = Array.from(new Set(beautified.match(urlRegex) || []));
        const pathRegex = /["'`](\/[-a-zA-Z0-9_@:\/\.]+)["'`]/g;
        const paths: string[] = [];
        let match: RegExpExecArray | null;
        while ((match = pathRegex.exec(beautified)) !== null) {
          paths.push(match[1]);
        }
        const endpoints = {
          urls,
          paths: Array.from(new Set(paths)),
        };

        // Extract secrets (simplified)
        const secrets: any = {
          apiKeys: [],
          tokens: [],
          candidates: [],
        };
        const apiKeyPattern = /(?:api[_-]?key|apikey)[\s:=]+["'`]([A-Za-z0-9_\-]{20,})["'`]/gi;
        let keyMatch: RegExpExecArray | null;
        while ((keyMatch = apiKeyPattern.exec(beautified)) !== null) {
          secrets.apiKeys.push(keyMatch[1]);
        }
        secrets.apiKeys = Array.from(new Set(secrets.apiKeys));

        await setWorkingMemory(`js:analysis:${url}`, {
          endpoints,
          secrets,
        }, 7200);

        return formatToolResult(true, {
          url,
          endpoints,
          secrets,
          summary: {
            endpointsFound: (endpoints.urls?.length || 0) + (endpoints.paths?.length || 0),
            secretsFound: (secrets.apiKeys?.length || 0) + (secrets.tokens?.length || 0),
          },
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );
}

