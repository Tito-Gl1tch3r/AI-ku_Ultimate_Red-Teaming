import { mkdtemp, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { pathToFileURL } from 'node:url'
import { afterEach, describe, expect, it } from 'vitest'
import { Context } from '@pentest-harness/cordis'
import Loader from '@pentest-harness/cordis-plugin-loader'
import Include from '@pentest-harness/cordis-plugin-include'
import { CallId } from '@pentest-harness/dsh-llm'
import { Session, SessionId } from '@pentest-harness/dsh-session'
import AgentRegistry, { Inbox } from '@pentest-harness/dsh-agent'
import type { Agent } from '@pentest-harness/dsh-agent'
import SystemPrompt from '@pentest-harness/dsh-system-prompt'
import ToolRuntime from '@pentest-harness/dsh-tools'
import TerminalSessionService from '@pentest-harness/dsh-terminal'
import SandboxProvider from '@pentest-harness/dsh-sandbox'
import type { ConfinedArgv, SandboxPolicy } from '@pentest-harness/dsh-sandbox'
import SandboxPolicyService from '@pentest-harness/dsh-sandbox-policy'
import LocalSubprocessRuntime from '@pentest-harness/dsh-subprocess-local'
import * as TerminalLocal from '@pentest-harness/dsh-terminal-bash'
import * as ToolPty from '@pentest-harness/dsh-tool-terminal'

let root: string | undefined
let context: Context | undefined

afterEach(async () => {
  await context?.fiber.dispose()
  context = undefined
  if (root !== undefined) await rm(root, { recursive: true, force: true })
  root = undefined
})

class PassthroughSandbox extends SandboxProvider {
  confine(argv: readonly string[], _policy: SandboxPolicy): ConfinedArgv {
    return { argv: [...argv], enforcement: 'full', denialSignatures: [], runnerFailureRules: [] }
  }
}

function agent(ctx: Context): Agent {
  const scope = ctx.plugin(() => {})
  const id = SessionId('pty-loader-agent')
  const session = Session.create(id)
  const value: Agent = {
    id, options: {}, session, inbox: new Inbox(session, { inserted: () => {}, discarded: () => {}, claimed: () => {} }),
    status: 'idle',
    ctx: scope.ctx,
    send: () => {},
    followup: () => {}, steer: () => {}, inject: () => {}, cancel() {},
    runMaintenance: job => job(new AbortController().signal),
    whenIdle: () => Promise.resolve(),
  }
  ctx.agents.register(value)
  return value
}

function resultText(result: { content: { type: string; text?: string }[] }): string {
  return result.content.filter(block => block.type === 'text').map(block => block.text).join('')
}

const suite = process.platform === 'linux' || process.platform === 'darwin' ? describe : describe.skip

suite('terminal real Loader composition through cordis.yml', () => {
  it('boots cordis.yml and preserves shell state across real tool calls', async () => {
    root = await mkdtemp(join(tmpdir(), 'dsh-pty-loader-'))
    const configPath = join(root, 'cordis.yml')
    await writeFile(configPath, [
      "- name: '@pentest-harness/dsh-agent'",
      "- name: '@pentest-harness/dsh-system-prompt'",
      "- name: '@pentest-harness/dsh-tools'",
      "- name: '@pentest-harness/dsh-terminal'",
      "- name: '@pentest-harness/dsh-test-sandbox'",
      "- name: '@pentest-harness/dsh-sandbox-policy'",
      '  config:',
      '    mode: danger-full-access',
      `    workspaceRoot: ${JSON.stringify(root)}`,
      "- name: '@pentest-harness/dsh-subprocess-local'",
      "- name: '@pentest-harness/dsh-terminal-bash'",
      '  config:',
      '    pollIntervalMs: 10',
      '    exactProbeAfterMs: 20',
      '    idleSilenceMs: 250',
      '    handoffGraceMs: 250',
      '    timeoutMs: 2000',
      '    disposeGraceMs: 500',
      "- name: '@pentest-harness/dsh-tool-terminal'",
      '',
    ].join('\n'))

    context = new Context()
    context.baseUrl = pathToFileURL(root).href + '/'
    await context.plugin(Loader)
    context.loader.builtins.include = Include
    const modules = new Map<string, unknown>([
      ['@pentest-harness/dsh-agent', AgentRegistry],
      ['@pentest-harness/dsh-system-prompt', SystemPrompt],
      ['@pentest-harness/dsh-tools', ToolRuntime],
      ['@pentest-harness/dsh-terminal', TerminalSessionService],
      ['@pentest-harness/dsh-test-sandbox', PassthroughSandbox],
      ['@pentest-harness/dsh-sandbox-policy', SandboxPolicyService],
      ['@pentest-harness/dsh-subprocess-local', LocalSubprocessRuntime],
      ['@pentest-harness/dsh-terminal-bash', TerminalLocal],
      ['@pentest-harness/dsh-tool-terminal', ToolPty],
    ])
    context.loader.internal = {
      version: 'v2',
      async import(specifier: string) {
        if (!modules.has(specifier)) throw new Error(`unexpected Loader import: ${specifier}`)
        return modules.get(specifier)
      },
    } as unknown as NonNullable<typeof context.loader.internal>
    await context.loader.create({ name: 'cordis:include', config: { path: pathToFileURL(configPath).href } })
    await context.loader.await()

    const owner = agent(context)
    const signal = new AbortController().signal
    const spawn = await context.tools.execute({
      signal, callId: CallId('spawn'), name: 'terminal_open', arguments: { type: 'shell', name: 'main', cwd: root }, agent: owner,
    })
    expect(resultText(spawn)).toContain('started terminal session pty-1 (main)')

    await context.tools.execute({
      signal, callId: CallId('state'), name: 'terminal_send', arguments: { sessionId: 'pty-1', text: 'export KEEP=loader; cd /' }, agent: owner,
    })
    const read = await context.tools.execute({
      signal, callId: CallId('read'), name: 'terminal_send', arguments: { sessionId: 'pty-1', text: 'printf "cwd=%s keep=%s\\n" "$PWD" "$KEEP"' }, agent: owner,
    })
    expect(resultText(read)).toContain('cwd=/ keep=loader')
    expect(context.terminals.list(owner)).toHaveLength(1)
  }, 15_000)
})
