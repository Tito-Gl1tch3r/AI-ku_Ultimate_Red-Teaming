import type { AgentRunResult, ToolCallRecord, ToolResult, TokenUsage, TraceEvent } from '@jackchen_me/open-multi-agent';
import { z } from 'zod';

const providerSchema = z.enum(['anthropic', 'openai', 'copilot', 'gemini', 'grok']);
const strategySchema = z.enum(['agent', 'team', 'tasks', 'fanout']);

const jsonSchemaSchema: z.ZodType<any> = z.lazy(() =>
  z.object({
    type: z.string().optional(),
    description: z.string().optional(),
    properties: z.record(jsonSchemaSchema).optional(),
    items: z.union([jsonSchemaSchema, z.array(jsonSchemaSchema)]).optional(),
    enum: z.array(z.union([z.string(), z.number(), z.boolean(), z.null()])).optional(),
    required: z.array(z.string()).optional(),
    additionalProperties: z.union([z.boolean(), jsonSchemaSchema]).optional(),
  }).passthrough(),
);

const loopDetectionSchema = z.object({
  maxRepetitions: z.number().int().positive().optional(),
  loopDetectionWindow: z.number().int().positive().optional(),
  onLoopDetected: z.enum(['warn', 'terminate']).optional(),
}).optional();

const hookConfigSchema = z.object({
  promptPrefix: z.string().optional(),
  promptSuffix: z.string().optional(),
  outputPrefix: z.string().optional(),
  outputSuffix: z.string().optional(),
}).strict().optional();

const runnerAgentSchema = z.object({
  name: z.string().min(1),
  role: z.string().min(1).optional(),
  model: z.string().min(1).optional(),
  provider: providerSchema.optional(),
  baseURL: z.string().min(1).optional(),
  apiKey: z.string().min(1).optional(),
  systemPrompt: z.string().min(1).optional(),
  tools: z.array(z.string().min(1)).optional(),
  maxTurns: z.number().int().positive().max(20).optional(),
  maxTokens: z.number().int().positive().optional(),
  temperature: z.number().min(0).max(1).optional(),
  timeoutMs: z.number().int().positive().optional(),
  loopDetection: loopDetectionSchema,
  outputSchema: jsonSchemaSchema.optional(),
  beforeRun: hookConfigSchema,
  afterRun: hookConfigSchema,
}).strict();

const runnerTaskSchema = z.object({
  title: z.string().min(1),
  description: z.string().min(1),
  assignee: z.string().min(1).optional(),
  dependsOn: z.array(z.string().min(1)).optional(),
  maxRetries: z.number().int().min(0).max(10).optional(),
  retryDelayMs: z.number().int().min(1).max(120000).optional(),
  retryBackoff: z.number().positive().max(10).optional(),
}).strict();

const fanoutSchema = z.object({
  analysts: z.array(runnerAgentSchema).min(1).optional(),
  synthesizer: runnerAgentSchema.optional(),
  sharedPrompt: z.string().min(1).optional(),
  synthesisPrompt: z.string().min(1).optional(),
}).strict().optional();

export const runnerInputSchema = z.object({
  workspaceRoot: z.string().min(1),
  prompt: z.string().min(1),
  model: z.string().min(1),
  provider: providerSchema.default('anthropic'),
  apiKey: z.string().min(1).optional(),
  baseUrl: z.string().min(1).optional(),
  systemPrompt: z.string().min(1).optional(),
  maxTurns: z.number().int().positive().max(20).optional(),
  maxTokens: z.number().int().positive().optional(),
  temperature: z.number().min(0).max(1).optional(),
  timeoutMs: z.number().int().positive().optional(),
  executionMode: z.string().optional(),
  teamMode: z.string().optional(),
  needsTools: z.boolean().optional(),
  contextSummary: z.string().min(1).optional(),
  strategy: strategySchema.optional(),
  sharedMemory: z.boolean().optional(),
  traceEnabled: z.boolean().optional(),
  loopDetection: loopDetectionSchema,
  approvalMode: z.enum(['off', 'auto_approve', 'manual']).optional(),
  approvalControlPath: z.string().min(1).optional(),
  beforeRun: hookConfigSchema,
  afterRun: hookConfigSchema,
  outputSchema: jsonSchemaSchema.optional(),
  agents: z.array(runnerAgentSchema).optional(),
  tasks: z.array(runnerTaskSchema).optional(),
  fanout: fanoutSchema,
}).strict();

export type RunnerInput = z.infer<typeof runnerInputSchema>;
export type RunnerAgentInput = z.infer<typeof runnerAgentSchema>;
export type RunnerTaskInput = z.infer<typeof runnerTaskSchema>;

export interface BridgeAgentResult {
  name: string;
  role: string;
  success: boolean;
  output: string;
  tokenUsage: TokenUsage;
  toolCalls: ToolCallRecord[];
  structured?: unknown;
  loopDetected?: boolean;
}

export interface BridgeTaskResult {
  id: string;
  title: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'blocked' | 'skipped';
  assignee?: string;
  dependsOn?: string[];
  result?: string;
  retries?: number;
}

export interface BridgeRunResult {
  success: boolean;
  output: string;
  content: string;
  messages: AgentRunResult['messages'];
  tokenUsage: TokenUsage;
  toolCalls: ToolCallRecord[];
  agents: BridgeAgentResult[];
  tasks: BridgeTaskResult[];
  structured?: unknown;
  traces?: TraceEvent[];
  strategy?: string;
}

export type RunnerEvent =
  | {
      type: 'run_started';
      data: Pick<RunnerInput, 'workspaceRoot' | 'model' | 'provider'> & { strategy?: string };
    }
  | {
      type: 'team_started';
      data: {
        name: string;
        agents: string[];
        strategy?: string;
      };
    }
  | {
      type: 'decision_trace';
      data: Record<string, unknown>;
    }
  | {
      type: 'agent_started' | 'agent_completed';
      data: {
        name: string;
        role: string;
        taskId?: string;
        taskTitle?: string;
      };
    }
  | {
      type: 'agent_message';
      data: {
        from: string;
        to: string;
        content: string;
      };
    }
  | {
      type: 'approval_requested';
      data: {
        mode: string;
        completedTasks: Array<{ id?: string, title?: string, status?: string, assignee?: string }>;
        nextTasks: Array<{ id?: string, title?: string, status?: string, assignee?: string }>;
        scope?: 'task_pipeline' | 'tool_call';
        summary?: string;
        toolName?: string;
        toolInput?: Record<string, unknown>;
        riskLevel?: 'safe' | 'review' | 'high';
        riskReason?: string;
      };
    }
  | {
      type: 'task_started' | 'task_completed' | 'task_failed' | 'task_retry' | 'task_skipped';
      data: {
        id?: string;
        title?: string;
        assignee?: string;
        dependsOn?: string[];
        result?: string;
        attempt?: number;
        maxAttempts?: number;
        error?: string;
        nextDelayMs?: number;
        retries?: number;
      };
    }
  | {
      type: 'trace';
      data: TraceEvent;
    }
  | {
      type: 'tool_call';
      data: {
        name: string;
        input: Record<string, unknown>;
      };
    }
  | {
      type: 'tool_result';
      data: {
        name: string;
        result: ToolResult;
      };
    }
  | {
      type: 'run_completed';
      data: BridgeRunResult;
    }
  | {
      type: 'run_failed';
      data: {
        message: string;
      };
    };

export interface ToolEventHandlers {
  onToolCall?: (name: string, input: Record<string, unknown>) => void;
  onToolResult?: (name: string, result: ToolResult) => void;
  onEvent?: (event: Exclude<RunnerEvent, { type: 'run_started' | 'run_completed' | 'run_failed' | 'tool_call' | 'tool_result' }>) => void;
}
