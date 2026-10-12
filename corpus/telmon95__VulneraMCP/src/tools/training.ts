import { Server } from '../mcp/server';
import { formatToolResult, ToolResult } from '../types';
import {
  saveTrainingData,
  getTrainingData,
  getTestResults,
  getTestStatistics,
} from '../integrations/postgres';

// Simple pattern matcher for learning from training data
class PatternMatcher {
  private patterns: Map<string, any[]> = new Map();

  learnPattern(
    vulnType: string,
    targetPattern: string,
    payloadPattern: string,
    successPattern: string,
    failurePattern: string
  ) {
    if (!this.patterns.has(vulnType)) {
      this.patterns.set(vulnType, []);
    }
    this.patterns.get(vulnType)!.push({
      targetPattern,
      payloadPattern,
      successPattern,
      failurePattern,
    });
  }

  matchPattern(vulnType: string, target: string, payload: string, response: string): {
    confidence: number;
    pattern?: any;
  } {
    const patterns = this.patterns.get(vulnType) || [];
    let bestMatch = null;
    let bestScore = 0;

    for (const pattern of patterns) {
      let score = 0;
      
      // Simple pattern matching (can be enhanced with regex/ML)
      if (target.includes(pattern.targetPattern) || pattern.targetPattern.includes(target)) {
        score += 0.3;
      }
      if (payload.includes(pattern.payloadPattern) || pattern.payloadPattern.includes(payload)) {
        score += 0.3;
      }
      if (response.includes(pattern.successPattern)) {
        score += 0.4;
      }
      if (response.includes(pattern.failurePattern)) {
        score -= 0.2;
      }

      if (score > bestScore) {
        bestScore = score;
        bestMatch = pattern;
      }
    }

    return {
      confidence: bestScore,
      pattern: bestMatch,
    };
  }
}

const patternMatcher = new PatternMatcher();

export function registerTrainingTools(server: Server) {
  // Import training data from HTB/PortSwigger
  server.tool(
    'training.import',
    {
      description: 'Import training data from HTB or PortSwigger labs',
      inputSchema: {
        type: 'object',
        properties: {
          source: {
            type: 'string',
            enum: ['htb', 'portswigger', 'custom', 'cve_exploit'],
            description: 'Source of training data',
          },
          sourceId: { type: 'string', description: 'ID from source (e.g., lab name)' },
          vulnerabilityType: {
            type: 'string',
            description: 'Type of vulnerability (XSS, SQLi, IDOR, etc.)',
          },
          targetPattern: { type: 'string', description: 'Pattern to match target URLs' },
          payloadPattern: { type: 'string', description: 'Pattern for successful payloads' },
          successPattern: { type: 'string', description: 'Pattern indicating success in response' },
          failurePattern: { type: 'string', description: 'Pattern indicating failure in response' },
          contextData: { type: 'object', description: 'Additional context data' },
          score: { type: 'number', description: 'Score for this training example (0-10)' },
        },
        required: ['source', 'vulnerabilityType', 'targetPattern', 'payloadPattern'],
      },
    },
    async (params: any): Promise<ToolResult> => {
      try {
        const id = await saveTrainingData(
          params.source,
          params.sourceId || '',
          params.vulnerabilityType,
          params.targetPattern,
          params.payloadPattern,
          params.successPattern || '',
          params.failurePattern || '',
          params.contextData,
          params.score || 5
        );

        // Learn the pattern
        patternMatcher.learnPattern(
          params.vulnerabilityType,
          params.targetPattern,
          params.payloadPattern,
          params.successPattern || '',
          params.failurePattern || ''
        );

        return formatToolResult(true, {
          id,
          message: 'Training data imported successfully',
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Get training data
  server.tool(
    'training.get',
    {
      description: 'Retrieve training data for learning patterns',
      inputSchema: {
        type: 'object',
        properties: {
          vulnerabilityType: { type: 'string', description: 'Filter by vulnerability type' },
          source: { type: 'string', description: 'Filter by source (htb, portswigger)' },
          limit: { type: 'number', description: 'Maximum number of results', default: 100 },
        },
      },
    },
    async ({ vulnerabilityType, source, limit = 100 }: any): Promise<ToolResult> => {
      try {
        const data = await getTrainingData(vulnerabilityType, source, limit);
        return formatToolResult(true, {
          trainingData: data,
          count: data.length,
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Match patterns from training data
  server.tool(
    'training.match',
    {
      description: 'Match current test against learned patterns',
      inputSchema: {
        type: 'object',
        properties: {
          vulnerabilityType: { type: 'string', description: 'Type of vulnerability to match' },
          target: { type: 'string', description: 'Target URL' },
          payload: { type: 'string', description: 'Payload used' },
          response: { type: 'string', description: 'Response received' },
        },
        required: ['vulnerabilityType', 'target', 'payload', 'response'],
      },
    },
    async (params: any): Promise<ToolResult> => {
      try {
        const match = patternMatcher.matchPattern(
          params.vulnerabilityType,
          params.target,
          params.payload,
          params.response
        );

        // Also check database for similar patterns
        const trainingData = await getTrainingData(params.vulnerabilityType, undefined, 50);
        const similarPatterns = trainingData.filter((pattern: any) => {
          return (
            params.target.includes(pattern.target_pattern) ||
            params.payload.includes(pattern.payload_pattern)
          );
        });

        return formatToolResult(true, {
          match,
          similarPatterns: similarPatterns.slice(0, 5),
          recommendation: match.confidence > 0.5 ? 'High confidence match' : 'Low confidence',
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Get test statistics
  server.tool(
    'training.stats',
    {
      description: 'Get statistics about test results and training data',
      inputSchema: {
        type: 'object',
        properties: {},
      },
    },
    async (): Promise<ToolResult> => {
      try {
        const stats = await getTestStatistics();
        const trainingCount = await getTrainingData(undefined, undefined, 1000);
        
        return formatToolResult(true, {
          testStatistics: stats,
          trainingDataCount: trainingCount.length,
          successRate: stats.reduce((acc: number, stat: any) => {
            const total = parseInt(stat.total_tests) || 0;
            const success = parseInt(stat.successful_tests) || 0;
            return total > 0 ? (success / total) * 100 : 0;
          }, 0) / stats.length,
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Import from PortSwigger Academy format
  server.tool(
    'training.import_portswigger',
    {
      description: 'Import training data from PortSwigger Academy lab solution',
      inputSchema: {
        type: 'object',
        properties: {
          labName: { type: 'string', description: 'Name of the PortSwigger lab' },
          labUrl: { type: 'string', description: 'URL of the lab' },
          vulnerabilityType: { type: 'string', description: 'Type of vulnerability' },
          solution: { type: 'object', description: 'Solution data with payloads and steps' },
        },
        required: ['labName', 'vulnerabilityType', 'solution'],
      },
    },
    async (params: any): Promise<ToolResult> => {
      try {
        const solution = params.solution;
        const payloads = solution.payloads || [];
        const results: any[] = [];

        for (const payload of payloads) {
          const id = await saveTrainingData(
            'portswigger',
            params.labName,
            params.vulnerabilityType,
            params.labUrl || '',
            payload.payload || payload,
            solution.successPattern || 'success',
            solution.failurePattern || 'error',
            { solution, labUrl: params.labUrl },
            solution.score || 7
          );
          results.push(id);
        }

        return formatToolResult(true, {
          imported: results.length,
          ids: results,
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );

  // Import from HTB format
  server.tool(
    'training.import_htb',
    {
      description: 'Import training data from HackTheBox challenge',
      inputSchema: {
        type: 'object',
        properties: {
          challengeName: { type: 'string', description: 'Name of the HTB challenge' },
          challengeUrl: { type: 'string', description: 'URL of the challenge' },
          vulnerabilityType: { type: 'string', description: 'Type of vulnerability' },
          exploit: { type: 'object', description: 'Exploit data with payloads and steps' },
        },
        required: ['challengeName', 'vulnerabilityType', 'exploit'],
      },
    },
    async (params: any): Promise<ToolResult> => {
      try {
        const exploit = params.exploit;
        const payloads = exploit.payloads || [exploit.payload || ''];
        const results: any[] = [];

        for (const payload of payloads) {
          const id = await saveTrainingData(
            'htb',
            params.challengeName,
            params.vulnerabilityType,
            params.challengeUrl || '',
            payload,
            exploit.successPattern || 'flag',
            exploit.failurePattern || 'error',
            { exploit, challengeUrl: params.challengeUrl },
            exploit.score || 8
          );
          results.push(id);
        }

        return formatToolResult(true, {
          imported: results.length,
          ids: results,
        });
      } catch (error: any) {
        return formatToolResult(false, null, error.message);
      }
    }
  );
}









