/**
 * WorkflowView — the live agent-run tab rendered as a professional
 * operations console.
 *
 * Header stats + latest reasoning banner on top; below, the trickest-style
 * horizontal run flow (reasoning and tool nodes, connected left → right),
 * rendered from real session events so a running agent updates the view live.
 */
import { Fragment, useEffect, useMemo, useRef, useState } from 'react'
import type { PropsLocale, PropsRuntime } from '@pentest-harness/dsh-client-ui-slots'
import type { SessionId } from '@pentest-harness/dsh-client-runtime/client'
import type { ConversationNode, RunningToolCall } from '@pentest-harness/dsh-client-runtime/client'
import type { TrajectorySnapshot } from '@pentest-harness/dsh-client-ui-trajectory/src/client/trajectory-contract.ts'
import { PentestLogo } from '@pentest-harness/dsh-client-ui-primitives'
import { NS } from './locales.ts'
import css from './WorkflowView.module.css'

export interface WorkflowViewInjected {
  readonly sessionId: SessionId
}

type WorkflowViewProps =
  PropsRuntime<'conversation.view'>
  & PropsLocale<typeof NS>
  & WorkflowViewInjected

/** One tool chip under the agent. */
interface ToolChip {
  seq: number
  time: number
  name: string
  args: string
  status: 'done' | 'failed' | 'running'
  start: number | null
}

/** One thought milestone on the run. */
interface Thought {
  seq: number
  time: number
  text: string
}

/** One detailed timeline row: the agent narrating or a tool executing. */
interface TimelineRow {
  seq: number
  time: number
  type: 'thought' | 'tool'
  /** Full narration text for thought rows. */
  text?: string
  /** Tool name + parsed description for tool rows. */
  tool?: string
  description?: string
  command?: string
  status?: 'done' | 'failed' | 'running'
  start?: number | null
}

const EMPTY_TRAJECTORY: TrajectorySnapshot = {
  eventNodes: [],
  eventLocations: new Map(),
  requests: [],
  callSchemas: new Map(),
  partial: null,
  runningCalls: [],
}

function buildModel(
  nodes: readonly ConversationNode[],
  runningCallIds: ReadonlySet<string>,
): { chips: ToolChip[]; thoughts: Thought[] } {
  const chips: ToolChip[] = []
  const thoughts: Thought[] = []

  for (const node of nodes) {
    if (node.kind === 'assistant') {
      const text = (node.blocks ?? [])
        .map(b => (b.kind === 'text' ? (b.text ?? '') : ''))
        .join(' ')
        .trim()
      if (text === '') continue
      thoughts.push({ seq: node.seq, time: node.time, text: text.slice(0, 900) })
    } else if (node.kind === 'tool-result') {
      const isRunning = node.callId !== undefined && runningCallIds.has(node.callId)
      chips.push({
        seq: node.seq,
        time: node.time,
        name: node.call?.name ?? 'tool',
        args: node.call?.argsRaw ?? '',
        status: isRunning ? 'running' : node.isError ? 'failed' : 'done',
        start: node.callTime ?? null,
      })
    }
  }

  return { chips, thoughts }
}

/** Human tool names. */
const TOOL_LABEL: Record<string, string> = {
  bash: 'Shell command', write: 'Write file', read: 'Read file', edit: 'Edit file',
  web_search: 'Web search', http: 'HTTP request', todo_write: 'Plan update',
}

/** Pull the agent's own description out of the tool args JSON. */
function describeCall(argsRaw: string): { description?: string; command?: string } {
  try {
    const parsed = JSON.parse(argsRaw) as Record<string, unknown>
    const description = typeof parsed.description === 'string' ? parsed.description : undefined
    let command: string | undefined
    if (typeof parsed.command === 'string') command = parsed.command
    else if (typeof parsed.content === 'string') command = parsed.content
    else if (typeof parsed.file_path === 'string') command = parsed.file_path
    if (command === undefined && description !== undefined) {
      // no body field; show the first non-description key's value briefly
      const other = Object.entries(parsed).find(([k]) => k !== 'description')
      if (other && typeof other[1] === 'string') command = other[1]
    }
    const out: { description?: string; command?: string } = {}
    if (description !== undefined) out.description = description
    if (command !== undefined) out.command = command
    return out
  } catch {
    // truncated/odd JSON: salvage the first string value heuristically
    const m = /"(?:command|content|file_path|input)"\s*:\s*"((?:[^"\\]|\\.)*)"/.exec(argsRaw)
    if (m !== null) {
      try { return { command: JSON.parse(`"${m[1]}"`) as string } } catch { /* fall through */ }
    }
    return {}
  }
}

/** One-line the command down for the timeline body. */
function oneLine(text: string | undefined, max = 220): string {
  if (text === undefined) return ''
  const flat = text.replace(/\s+/g, ' ').trim()
  return flat.length > max ? flat.slice(0, max) + '…' : flat
}

export function WorkflowView({ useSession }: WorkflowViewProps): JSX.Element {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 1000)
    return () => { window.clearInterval(id) }
  }, [])

  const trajectory = useSession(s => s.views.get('trajectory') ?? EMPTY_TRAJECTORY)
  const nodes: readonly ConversationNode[] = trajectory.eventNodes

  const runningCallIds = useMemo(() => {
    const set = new Set<string>()
    for (const rc of trajectory.runningCalls ?? []) {
      if (rc !== null && typeof rc === 'object' && 'callId' in rc) {
        const id = (rc as { callId?: unknown }).callId
        if (typeof id === 'string') set.add(id)
      }
    }
    return set
  }, [trajectory.runningCalls])

  const { chips, thoughts } = useMemo(
    () => buildModel(nodes, runningCallIds),
    [nodes, runningCallIds],
  )

  const toolCount = chips.length
  const failedCount = chips.filter(c => c.status === 'failed').length
  const live = chips.some(c => c.status === 'running')
  const lastThought = thoughts.at(-1)?.text ?? null

  // Live calls (call head seen, no settled result yet) render as running rows.
  const liveRows: TimelineRow[] = []
  for (const rc of trajectory.runningCalls ?? []) {
    if (rc === null || typeof rc !== 'object' || !('callId' in rc)) continue
    const call = rc as RunningToolCall
    const desc = describeCall(call.argsRaw)
    liveRows.push({
      seq: -1, time: call.time, type: 'tool',
      tool: call.name,
      ...(desc.description !== undefined ? { description: desc.description } : {}),
      command: oneLine(desc.command),
      status: 'running', start: call.time,
    })
  }

  // Detailed timeline: every thought (full text) + every tool (description +
  // one-lined command), interleaved chronologically, newest first.
  const timeline: TimelineRow[] = useMemo(() => {
    const rows: TimelineRow[] = []
    for (const th of thoughts) {
      rows.push({ seq: th.seq, time: th.time, type: 'thought', text: th.text })
    }
    for (const c of chips) {
      const desc = describeCall(c.args)
      rows.push({
        seq: c.seq, time: c.time, type: 'tool',
        tool: c.name,
        ...(desc.description !== undefined ? { description: desc.description } : {}),
        command: oneLine(desc.command),
        status: c.status, start: c.start,
      })
    }
    rows.sort((a, b) => a.seq - b.seq)
    return rows.slice(-80)
  }, [thoughts, chips])

  // Flow rows: chronological order for the left-to-right canvas.
  const flowRows = useMemo(
    () => [...timeline, ...liveRows].sort((a, b) => a.time - b.time),
    [timeline, liveRows],
  )

  const flowRef = useRef<HTMLDivElement | null>(null)
  const [zoom, setZoom] = useState(1)
  useEffect(() => {
    const el = flowRef.current
    if (el !== null) el.scrollLeft = el.scrollWidth
  }, [flowRows.length])

  return (
    <div className={css.wrap}>
      <div className={css.header}>
        <div className={css.brand}>
          <span className={css.logoMark}><PentestLogo size={22} mono /></span>
          <div>
            <div className={css.kicker}>LIVE WORKFLOW</div>
            <h2 className={css.title}>Agent Run</h2>
          </div>
        </div>
        <div className={css.meta}>
          <span className={css.live}><span />{live ? 'LIVE' : toolCount > 0 ? 'DONE' : 'IDLE'}</span>
          <span className={css.pill}><strong>{toolCount}</strong> calls</span>
          {failedCount > 0 && <span className={css.pillFail}><strong>{failedCount}</strong> failed</span>}
        </div>
      </div>

      {lastThought !== null && (
        <div className={css.thoughtBanner}>
          <span className={css.thoughtLabel}>LATEST</span>
          <p>{lastThought}</p>
        </div>
      )}

      {/* ── trickest-style flow: connected node cards, left → right ── */}
      <div className={css.flowWrap}>
        <div className={css.flowHead}>
          <span className={css.timelineTitle}>Run flow</span>
          <span className={css.timelineMeta}>{flowRows.length} steps · oldest → newest · live</span>
          <div className={css.flowZoom}>
            <button type="button" className={css.zoomBtn} onClick={() => setZoom(z => Math.max(0.5, +(z - 0.2).toFixed(2)))} aria-label="Zoom out">−</button>
            <span className={css.zoomPct}>{Math.round(zoom * 100)}%</span>
            <button type="button" className={css.zoomBtn} onClick={() => setZoom(z => Math.min(1.6, +(z + 0.2).toFixed(2)))} aria-label="Zoom in">+</button>
            <button type="button" className={css.zoomBtn} onClick={() => setZoom(1)} aria-label="Reset zoom">⟳</button>
          </div>
        </div>
        <div className={css.flow} ref={flowRef}>
          <div className={css.flowTrack} style={{ transform: `scale(${zoom})`, transformOrigin: '0 50%' }}>
            {flowRows.map((row, index) => {
              const isLast = index === flowRows.length - 1
              if (row.type === 'thought') {
                return (
                  <Fragment key={`f${row.seq}`}>
                    <div className={`${css.flowNode} ${css.flowThought}`} title={row.text}>
                      <div className={css.flowNodeTop}>
                        <span className={css.flowKindTag}>REASONING</span>
                        <span className={css.flowTime}>{new Date(row.time).toLocaleTimeString()}</span>
                      </div>
                      <p className={css.flowThoughtText}>{row.text}</p>
                    </div>
                    {!isLast && <span className={css.flowLink} aria-hidden />}
                  </Fragment>
                )
              }
              const label = TOOL_LABEL[row.tool ?? ''] ?? row.tool
              const status = row.status ?? 'done'
              const dur = status === 'running'
                ? `${Math.max(1, Math.round((now - (row.start ?? row.time)) / 1000))}s…`
                : row.start != null
                  ? `${Math.max(1, Math.round((row.time - row.start) / 1000))}s`
                  : ''
              return (
                <Fragment key={row.seq === -1 ? `live${index}` : String(row.seq)}>
                  <div className={`${css.flowNode} ${css.flowTool}`} data-status={status} title={row.command}>
                    <div className={css.flowNodeTop}>
                      <span className={css.flowKindTag}>
                        {status === 'running' ? 'RUNNING' : label?.toUpperCase() ?? 'TOOL'}
                      </span>
                      {dur !== '' && <span className={css.flowTime}>{dur}</span>}
                    </div>
                    {row.description !== undefined && <div className={css.flowDesc}>{row.description}</div>}
                    {row.command !== undefined && row.command !== '' && (
                      <code className={css.flowCmd}>{row.command}</code>
                    )}
                  </div>
                  {!isLast && <span className={css.flowLink} aria-hidden />}
                </Fragment>
              )
            })}
            {flowRows.length === 0 && <div className={css.flowEmpty}>No run activity yet — start a task in Chat.</div>}
          </div>
        </div>
      </div>

      <div className={css.footer}>
        <span className={css.footerDot} />live flow · {toolCount} calls · {flowRows.length} steps
      </div>
    </div>
  )
}
