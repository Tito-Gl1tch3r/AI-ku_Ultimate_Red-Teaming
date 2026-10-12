/**
 * Bash executable resolution, dependency-free so non-package consumers (the
 * repository's coverage-gate probe in `vitest.config.ts`) can share the ONE
 * resolution definition with the executor and its suites — a probe that
 * resolved differently from the code under test could exempt a file whose
 * suites actually run.
 *
 * @module @pentest-harness/dsh-bash-local/resolve
 */

import { existsSync } from 'node:fs'
import { join } from 'node:path'

/**
 * Well-known Windows bash locations plus PATH entries, newest first. Windows
 * ships no bash; the practical sources are a Git-for-Windows install, a WSL
 * distribution's bash, and anything a user put on PATH (Cygwin, MSYS2, busybox
 * sh wrappers). Explicitly parameterized (env) so resolution is a pure
 * function of its inputs on every platform.
 * @param env - the environment to probe; defaults to the process environment.
 * @returns candidate `bash` executable paths in resolution order.
 */
export function candidateBashPaths(env: NodeJS.ProcessEnv = process.env): string[] {
  const programFiles = env.ProgramFiles ?? 'C:\\Program Files'
  const programFilesX86 = env['ProgramFiles(x86)'] ?? 'C:\\Program Files (x86)'
  const localAppData = env.LOCALAPPDATA ?? ''
  const candidates = [
    join(programFiles, 'Git', 'bin', 'bash.exe'),
    join(programFilesX86, 'Git', 'bin', 'bash.exe'),
  ]
  if (localAppData.length > 0) {
    // The Microsoft Store Git build installs under LocalAppData\Programs\Git.
    candidates.push(join(localAppData, 'Programs', 'Git', 'bin', 'bash.exe'))
  }
  // WSL: bash through the interop launcher, usable when a distribution exists.
  candidates.push(join(env.SystemRoot ?? 'C:\\Windows', 'System32', 'bash.exe'))
  // Store app execution aliases and user-added locations live on PATH.
  for (const entry of (env.PATH ?? '').split(';')) {
    const trimmed = entry.trim().replace(/^"|"$/g, '')
    if (trimmed.length === 0) continue
    candidates.push(join(trimmed, 'bash.exe'))
  }
  return candidates
}

/**
 * Resolve the bash executable this executor spawns.
 * @param configured - an explicit `bashPath` config value, trusted as-is.
 * @param env - the environment to probe on Windows; defaults to the process environment.
 * @param platform - the platform to resolve for; defaults to the process platform.
 * @returns the first existing well-known location on Windows (Git for Windows,
 *   the Store build, WSL, then a PATH entry), else `bash` for PATH resolution.
 */
export function resolveBashPath(
  configured?: string,
  env: NodeJS.ProcessEnv = process.env,
  platform: NodeJS.Platform = process.platform,
): string {
  if (configured !== undefined && configured.length > 0) return configured
  if (platform === 'win32') {
    for (const candidate of candidateBashPaths(env)) {
      if (existsSync(candidate)) return candidate
    }
  }
  return 'bash'
}
