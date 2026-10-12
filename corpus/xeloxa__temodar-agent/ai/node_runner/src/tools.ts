import { execFile } from 'node:child_process';
import path from 'node:path';
import { realpath } from 'node:fs/promises';
import { promisify } from 'node:util';

import {
  bashTool,
  defineTool,
  fileEditTool,
  fileReadTool,
  fileWriteTool,
  grepTool,
} from '@jackchen_me/open-multi-agent';
import type { ToolDefinition } from '@jackchen_me/open-multi-agent';
import { z } from 'zod';

const execFileAsync = promisify(execFile);

function normalizePathInput(candidatePath: string, workspaceRoot: string): string {
  const trimmed = String(candidatePath ?? '').trim();
  if (!trimmed) {
    return trimmed;
  }

  const unixCandidate = trimmed.replace(/\\/g, '/');
  if (unixCandidate === '/workspace') {
    return workspaceRoot;
  }
  if (unixCandidate.startsWith('/workspace/')) {
    return path.resolve(workspaceRoot, unixCandidate.slice('/workspace/'.length));
  }

  if (path.isAbsolute(trimmed)) {
    return trimmed;
  }

  return path.resolve(workspaceRoot, trimmed);
}

function createReadToolAlias(workspaceRoot: string, name: 'read' | 'file_read'): ToolDefinition {
  return {
    ...fileReadTool,
    name,
    execute: async (input, context) => {
      const normalized = input as { path: string; offset?: number; limit?: number };
      const filePath = normalizePathInput(normalized.path, workspaceRoot);
      return fileReadTool.execute({ ...normalized, path: filePath }, context);
    },
  };
}

function createWriteToolAlias(workspaceRoot: string, name: 'write' | 'file_write'): ToolDefinition {
  return {
    ...fileWriteTool,
    name,
    execute: async (input, context) => {
      const normalized = input as { path: string; content: string };
      const filePath = normalizePathInput(normalized.path, workspaceRoot);
      return fileWriteTool.execute({ ...normalized, path: filePath }, context);
    },
  };
}

function createEditToolAlias(workspaceRoot: string, name: 'edit' | 'file_edit'): ToolDefinition {
  return {
    ...fileEditTool,
    name,
    execute: async (input, context) => {
      const normalized = input as {
        path: string;
        old_string?: string;
        new_string?: string;
        oldText?: string;
        newText?: string;
        replace_all?: boolean;
      };

      const oldString = normalized.old_string ?? normalized.oldText;
      const newString = normalized.new_string ?? normalized.newText;
      if (typeof oldString !== 'string' || typeof newString !== 'string') {
        throw new Error('edit requires old_string/new_string or oldText/newText');
      }

      const filePath = normalizePathInput(normalized.path, workspaceRoot);
      return fileEditTool.execute(
        {
          ...normalized,
          path: filePath,
          old_string: oldString,
          new_string: newString,
          replace_all: normalized.replace_all,
        },
        context,
      );
    },
  };
}

function createWorkspaceGrepTool(workspaceRoot: string): ToolDefinition {
  return {
    ...grepTool,
    execute: async (input, context) => {
      const normalized = input as { pattern: string; path?: string; glob?: string; maxResults?: number };
      const searchPath = normalized.path ? normalizePathInput(normalized.path, workspaceRoot) : workspaceRoot;
      return grepTool.execute({ ...normalized, path: searchPath }, context);
    },
  };
}

function createWorkspaceBashTool(workspaceRoot: string): ToolDefinition {
  return {
    ...bashTool,
    execute: async (input, context) => {
      const normalized = input as { command: string; timeout?: number; timeoutMs?: number; cwd?: string };
      const cwd = normalized.cwd ? normalizePathInput(normalized.cwd, workspaceRoot) : workspaceRoot;
      const timeout = normalized.timeoutMs ?? normalized.timeout;
      return bashTool.execute(
        {
          command: normalized.command,
          timeout,
          cwd,
        },
        context,
      );
    },
  };
}

function formatExecError(error: unknown): string {
  if (error && typeof error === 'object') {
    const execError = error as { stdout?: string | Buffer; stderr?: string | Buffer; message?: string };
    const stdout = execError.stdout ? execError.stdout.toString() : '';
    const stderr = execError.stderr ? execError.stderr.toString() : '';
    const combined = [stdout, stderr].filter(Boolean).join('');
    return combined || execError.message || 'command failed';
  }
  return String(error || 'command failed');
}

async function runSemgrep(config: string, workspaceRoot: string): Promise<string> {
  const resolvedWorkspace = await realpath(workspaceRoot).catch(() => workspaceRoot);

  try {
    const { stdout, stderr } = await execFileAsync('semgrep', ['--config', config, '--json', '.'], {
      cwd: resolvedWorkspace,
      timeout: 120000,
      maxBuffer: 10 * 1024 * 1024,
    });

    return [stdout, stderr].filter(Boolean).join('') || '(no output)';
  } catch (error) {
    throw new Error(formatExecError(error));
  }
}

function createSemgrepTool(workspaceRoot: string): ToolDefinition {
  return defineTool({
    name: 'run_semgrep',
    description: 'Run semgrep inside the workspace and return JSON output.',
    inputSchema: z.object({
      config: z.string().min(1).default('auto'),
    }),
    execute: async ({ config }) => {
      const output = await runSemgrep(config ?? 'auto', workspaceRoot);
      return { data: output };
    },
  });
}

export function buildTools(workspaceRoot: string): ToolDefinition[] {
  return [
    createReadToolAlias(workspaceRoot, 'read'),
    createReadToolAlias(workspaceRoot, 'file_read'),
    createWriteToolAlias(workspaceRoot, 'write'),
    createWriteToolAlias(workspaceRoot, 'file_write'),
    createEditToolAlias(workspaceRoot, 'edit'),
    createEditToolAlias(workspaceRoot, 'file_edit'),
    createWorkspaceGrepTool(workspaceRoot),
    createWorkspaceBashTool(workspaceRoot),
    createSemgrepTool(workspaceRoot),
  ];
}
