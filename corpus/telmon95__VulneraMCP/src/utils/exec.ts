import { spawn, ChildProcess } from 'child_process';
import { ToolResult } from '../types';

export interface ExecResult {
  stdout: string;
  stderr: string;
  code: number;
}

export function runCommand(
  command: string,
  args: string[],
  timeout: number = 30000
): Promise<ExecResult> {
  return new Promise((resolve, reject) => {
    const process: ChildProcess = spawn(command, args, {
      stdio: ['ignore', 'pipe', 'pipe'],
      shell: false,
    });

    let stdout = '';
    let stderr = '';
    let timeoutId: NodeJS.Timeout;

    process.stdout?.on('data', (data: Buffer) => {
      stdout += data.toString();
    });

    process.stderr?.on('data', (data: Buffer) => {
      stderr += data.toString();
    });

    process.on('close', (code: number | null) => {
      if (timeoutId) clearTimeout(timeoutId);
      resolve({
        stdout: stdout.trim(),
        stderr: stderr.trim(),
        code: code ?? 0,
      });
    });

    process.on('error', (error: Error) => {
      if (timeoutId) clearTimeout(timeoutId);
      reject(error);
    });

    if (timeout > 0) {
      timeoutId = setTimeout(() => {
        process.kill();
        reject(new Error(`Command timeout after ${timeout}ms`));
      }, timeout);
    }
  });
}

export async function checkCommandExists(command: string): Promise<boolean> {
  try {
    const result = await runCommand('which', [command], 5000);
    return result.code === 0 && result.stdout.length > 0;
  } catch {
    return false;
  }
}

export function formatToolResult(
  success: boolean,
  data?: any,
  error?: string,
  code?: number
): ToolResult {
  return { success, data, error, code };
}

