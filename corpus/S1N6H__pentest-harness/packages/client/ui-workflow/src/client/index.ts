/**
 * Live agent-run workflow plugin: registers a `conversation.view` tab (beside
 * Chat / Trajectory / Bounty) that renders the agent's run as a live stream —
 * turns, steps, tool calls with running/done/failed status — derived from the
 * same trajectory node stream the Bounty console consumes, so it reflects the
 * session in real time.
 */
import type { Context } from '@pentest-harness/cordis'
import type { SessionId } from '@pentest-harness/dsh-client-runtime/client'
import type {} from '@pentest-harness/dsh-client-locale/client'
import type {} from '@pentest-harness/dsh-client-ui-conversation/client'
import { WorkflowView, type WorkflowViewInjected } from './WorkflowView.tsx'
import { en, NS, zh } from './locales.ts'

/** Required services: slots, sessions (session binding), locale. */
export const inject = ['slots', 'sessions', 'locale']

/**
 * Client plugin body: register the workflow tab into the conversation view.
 * @param ctx - client root context.
 */
export function apply(ctx: Context): void {
  ctx.effect(() => ctx.locale.register(NS, { zh, en }), 'ui-workflow: dictionaries')
  const t = ctx.locale.bind(NS)

  ctx.slots.inject('conversation.view', () => ctx.slots.register({
    name: 'conversation.view',
    id: 'workflow',
    // After Bounty (20) so the tab reads Chat | Trajectory | Bounty | Workflow.
    order: 30,
    locale: NS,
    label: () => t('view.workflow'),
    inject: (sessionId: SessionId): WorkflowViewInjected => {
      const session = ctx.sessions.binding(sessionId)?.session
      if (session === undefined) {
        throw new Error(`ui-workflow: session "${sessionId}" is unavailable`)
      }
      return { sessionId }
    },
  }, WorkflowView))
}
