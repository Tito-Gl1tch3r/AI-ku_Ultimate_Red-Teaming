import React, { useEffect, useMemo, useState, useRef } from 'react'
import { client } from '../lib/api'
import { useNavigate, useParams } from 'react-router-dom'
import { Button, Modal, Form, OverlayTrigger, Tooltip } from 'react-bootstrap'
import { toast } from 'react-toastify'
import DataTable, { createTheme } from 'react-data-table-component'
import {
  ArrowLeft, Play, Pause, CalendarClock, CalendarCheck, CalendarX, Archive, Trash2, RefreshCw, Download, RotateCcwKey, Search, Copy, ChevronDown, ChevronUp, X, MailOpen 
} from 'lucide-react'
import '../components/datatableThemes'
import { useTheme } from '../../hooks/useTheme'
import { copyToClipboard } from '../utils/common'
import { inputClsSearchbar } from '../utils/styles'

const Tag = ({ className = '', children }) => (
  <span
    className={[
      'inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] font-semibold',
      'bg-white/90 dark:bg-white/10 text-slate-800 dark:text-slate-100',
      'ring-1 ring-black/10 dark:ring-white/10',
      className,
    ].join(' ')}
  >
    {children}
  </span>
)

const StatusBadge = ({ status }) => {
  const k = (status || '').toLowerCase()
  if (k === 'sent' || k === 'completed' || k === 'success') {
    return (
      <Tag className="bg-emerald-500/12 text-emerald-700 ring-emerald-500/25 dark:bg-emerald-500/15 dark:text-emerald-300 dark:ring-emerald-500/30">
        {status}
      </Tag>
    )
  }
  if (k === 'failed' || k === 'error') {
    return (
      <Tag className="bg-rose-500/12 text-rose-700 ring-rose-500/25 dark:bg-rose-500/15 dark:text-rose-300 dark:ring-rose-500/30">
        {status}
      </Tag>
    )
  }
  if (k === 'pending' || k === 'scheduled' || k === 'queued') {
    return (
      <Tag className="bg-amber-500/12 text-amber-700 ring-amber-500/25 dark:bg-amber-500/15 dark:text-amber-300 dark:ring-amber-500/30">
        {status}
      </Tag>
    )
  }
  return (
    <Tag className="bg-slate-500/10 text-slate-700 ring-slate-500/20 dark:bg-slate-500/15 dark:text-slate-300 dark:ring-slate-500/30">
      {status || '—'}
    </Tag>
  )
}

const TruncatedTextWithTooltip = ({ text, maxWidth = 460 }) => {
  const textRef = useRef(null)
  const [isTruncated, setIsTruncated] = useState(false)

  useEffect(() => {
    const element = textRef.current
    if (element) {
      setIsTruncated(element.scrollWidth > element.clientWidth)
    }
  }, [text])

  const content = (
    <div ref={textRef} className="truncate" style={{ maxWidth }}>
      <span className="text-xs">{text || '—'}</span>
    </div>
  )

  if (!text || !isTruncated) {
    return content
  }

  return (
    <OverlayTrigger
      placement="top"
      overlay={<Tooltip className="error-tooltip">{text}</Tooltip>}
    >
      {content}
    </OverlayTrigger>
  )
}

// Timeline
function TimelineBar({ logs }) {
  const points = React.useMemo(
    () => (logs || [])
      .filter(l => l.sent_at)
      .map(l => ({ t: new Date(l.sent_at).getTime(), email: l.to_email, status: l.status })),
    [logs]
  )

  if (points.length === 0) {
    return <p className="text-slate-500 dark:text-slate-300 text-sm m-0">No sent emails yet.</p>
  }

  const min = Math.min(...points.map(p => p.t))
  const max = Math.max(...points.map(p => p.t))
  const range = Math.max(1, max - min)
  const fmt = (ts) => new Date(ts).toLocaleTimeString()
  const colorFor = (s) => (String(s).toLowerCase() === 'failed' ? 'bg-rose-500' : 'bg-[var(--mlf-primary)]')

  return (
    <div className="space-y-1.5">
      <div className="relative h-3 rounded-full overflow-visible ring-1 ring-black/10 dark:ring-white/10 bg-slate-200/70 dark:bg-white/10">
        <div
          className="absolute inset-0 opacity-30 pointer-events-none"
          style={{
            background: 'linear-gradient(90deg, transparent, rgba(109,113,236,.25), transparent)',
            WebkitMaskImage: 'radial-gradient(90% 50% at 50% 50%, #000 60%, transparent 100%)',
            maskImage: 'radial-gradient(90% 50% at 50% 50%, #000 60%, transparent 100%)'
          }}
        />
        {points.map((p, i) => {
          const leftPct = ((p.t - min) / range) * 100
          const tip = (
            <Tooltip id={`tl-tip-${i}`} className="timeline-tooltip">
              <div className="flex flex-col gap-0.5">
                <div className="font-medium">{p.email}</div>
                <div className="text-xs opacity-80">{fmt(p.t)} • {String(p.status || '').toUpperCase()}</div>
              </div>
            </Tooltip>
          )
          return (
            <OverlayTrigger
              key={i}
              placement="top"
              delay={{ show: 120, hide: 80 }}
              overlay={tip}
              flip
              popperConfig={{ strategy: 'fixed', modifiers: [{ name: 'preventOverflow', options: { padding: 8 } }] }}
            >
              <div
                className={`absolute top-1/2 -translate-y-1/2 -translate-x-1/2 ${colorFor(p.status)} rounded-full border border-white/70 dark:border-white/20 shadow cursor-help`}
                style={{ left: `${leftPct}%`, width: 10, height: 10 }}
              />
            </OverlayTrigger>
          )
        })}
      </div>
      <div className="d-flex justify-content-between text-slate-500 dark:text-slate-400 text-xs">
        <span>{fmt(min)}</span><span>{fmt(max)}</span>
      </div>
    </div>
  )
}

// Datatables definitions
const tableStyles = (isDark) => {
  const headBg = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.035)'
  return {
    table: { style: { backgroundColor: 'transparent' } },
    header: { style: { minHeight: '52px', backgroundColor: 'transparent' } },
    headRow: { style: { backgroundColor: headBg, borderRadius: 12, minHeight: '60px' } },
    headCells: {
      style: {
        fontWeight: 700, fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.02em',
        paddingTop: '18px', paddingBottom: '18px', color: isDark ? '#cbd5e1' : '#1f2937',
      },
    },
    rows: {
      style: { minHeight: '56px', backgroundColor: 'transparent', color: isDark ? '#e5e7eb' : '#111827' },
      highlightOnHoverStyle: {
        backgroundColor: isDark ? 'rgba(109,113,236,0.18)' : 'rgba(109,113,236,0.10)',
        transitionDuration: '0.15s', borderBottomColor: 'transparent', outline: 'none',
      },
      stripedStyle: { backgroundColor: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)' },
    },
    pagination: {
      style: { backgroundColor: 'transparent', color: isDark ? '#e5e7eb' : '#0f172a' },
      pageButtonsStyle: {
        borderRadius: '10px', height: '32px', width: '32px', padding: 0, margin: '0 2px',
        color: isDark ? '#e5e7eb' : '#334155',
      },
    },
  }
}

export default function CampaignDetail() {
  const { id } = useParams()
  const api = client()
  const nav = useNavigate()

  // Data
  const [detail, setDetail] = useState(null)
  const [targets, setTargets] = useState([])
  const [logs, setLogs] = useState([])
  const [error, setError] = useState(null)

  // Schedule
  const [showSched, setShowSched] = useState(false)
  const [when, setWhen] = useState('')

  // Confirms
  const [confirmUnsched, setConfirmUnsched] = useState(false)
  const [confirmArchive, setConfirmArchive] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  // Variables
  const [showVars, setShowVars] = useState(false)
  const [varsData, setVarsData] = useState(null)
  const [varsQuery, setVarsQuery] = useState('')

  // Errors
  const [showErrorDetails, setShowErrorDetails] = useState(false)

  // Opened emails
  const [confirmOpen, setConfirmOpen] = useState({ show: false, email: null, nextVal: true });
  const [openedOnly, setOpenedOnly] = useState(false)

  // Filters
  const [targetsQuery, setTargetsQuery] = useState('');

  const filteredTargets = useMemo(() => {
    const q = (targetsQuery || '').toLowerCase().trim()
    let data = targets

    if (openedOnly) {
      data = data.filter(t => !!t.opened)
    }

    if (!q) return data
    return data.filter(t => {
      const hay = `${t.first_name || ''} ${t.last_name || ''} ${t.email || ''} ${t.status || ''} ${t.error || ''}`.toLowerCase()
      return hay.includes(q)
    })
  }, [targets, targetsQuery, openedOnly])


  // Theme selector
  const isDark = useTheme()

  const pad2 = (n) => String(n).padStart(2, '0')
  const toLocalInputValue = (d) => {
    const x = new Date(d)
    return `${x.getFullYear()}-${pad2(x.getMonth() + 1)}-${pad2(x.getDate())}T${pad2(x.getHours())}:${pad2(x.getMinutes())}`
  }
  const openSchedule = () => {
    const base = detail?.scheduled_start_at ? new Date(detail.scheduled_start_at) : new Date(Date.now() + 15 * 60 * 1000)
    setWhen(toLocalInputValue(base))
    setShowSched(true)
  }

  const load = async () => {
    try {
      const [d, t, l] = await Promise.all([
        api.get(`/api/campaigns/${id}`),
        api.get(`/api/campaigns/${id}/targets_status`),
        api.get(`/api/campaigns/${id}/logs`)
      ])
      setDetail(d.data)
      setTargets(t.data)
      setLogs(l.data)
      setError(null)

    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to load campaign')
    }
  }
  useEffect(() => { load() }, [id])

  // Reload every 5s
  useEffect(() => {
    const int = setInterval(() => { load() }, 5000)
    return () => clearInterval(int)
  }, [id])

  // Tooltip styles for error column
  useEffect(() => {
    const styleEl = document.createElement('style')
    styleEl.textContent = `
      .error-tooltip .tooltip-inner {
        max-width: 400px !important;
        text-align: center;
      }
    `
    document.head.appendChild(styleEl)
    return () => document.head.removeChild(styleEl)
  }, [])

  const openVars = async () => {
    try {
      const r = await api.get(`/api/campaigns/${id}/variables`)
      setVarsData(r.data)
      setShowVars(true)
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Could not load variables')
    }
  }

  const _MON = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
  const icsPretty = (s) => {
    if (!s || s.length < 15) return '—'
    const y = s.slice(0, 4), m = s.slice(4, 6), d = s.slice(6, 8)
    const H = s.slice(9, 11), Mi = s.slice(11, 13)
    return `${d} ${_MON[parseInt(m, 10) - 1] || m} ${y} ${H}:${Mi}`
  }
  const meetingLine = (d) => {
    const subject = d.meeting_summary || d.calendar_summary || 'Meeting'
    const start = icsPretty(d.meeting_begin)
    const end = icsPretty(d.meeting_end)
    const tz = d.meeting_tz || d.calendar_tz || (Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC')
    return `${subject} [${start} - ${end} ${tz}]`
  }

  const start = async () => {
    try {
      await api.post(`/api/campaigns/${id}/start`)
      toast.success('Started')
      load()

    } catch (e) {
      toast.error(e.response?.data?.detail || 'Start failed')
    }
  }
  const pause = async () => {
    try {
      await api.post(`/api/campaigns/${id}/pause`)
      toast.info('Paused')
      load()

    } catch (e) {
      toast.error(e.response?.data?.detail || 'Pause failed')
    }
  }

  const resume = async () => {
    try {
      await api.post(`/api/campaigns/${id}/resume`)
      toast.success('Campaign resumed')
      load()

    } catch (e) {
      toast.error(e.response?.data?.detail || 'Resume failed')
    }
  }

  const archive = async () => {
    try {
      await api.post(`/api/campaigns/${id}/archive`)
      toast.info('Archived'); load()

    } catch {
      toast.error('Archive failed')
    }
  }

  const schedule = async () => {
    const ts = Date.parse(when)
    if (isNaN(ts)) {
      toast.error('Please choose a valid date and time')
      return
    }
    if (ts <= Date.now()) {
      toast.error('Scheduled time cannot be in the past')
      return
    }
    try {
      await api.post(`/api/campaigns/${id}/schedule`, { scheduled_start_at: when })
      toast.success('Start time scheduled')
      setShowSched(false)
      load()

    } catch (e) {
      toast.error(e.response?.data?.detail || 'Schedule failed')
    }
  }

  const unschedule = async () => {
    try {
      await api.post(`/api/campaigns/${id}/unschedule`)
      toast.info('Schedule removed')
      load()

    } catch (e) {
      toast.error(e.response?.data?.detail || 'Action failed')
    }
  }

  const exportResults = async () => {
    try {
      const res = await api.get(`/api/campaigns/${id}/export`, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const a = document.createElement('a')
      a.href = url; a.download = `${detail?.name || 'campaign'}_Results.xlsx`
      document.body.appendChild(a); a.click(); a.remove(); window.URL.revokeObjectURL(url)
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed to export')
    }
  }

  if (error) return <div className="alert alert-danger">{error}</div>
  if (!detail) return <p className="text-slate-600 dark:text-slate-300">Loading…</p>

  const isCancel = !!detail.has_calendar_cancellation
  const isResched = !!detail.has_calendar_reschedule
  const isInvite = !!detail.has_calendar_invite && !isCancel && !isResched


  // Opened mails
  const canToggleOpen = (row) => {
    if (detail?.status === 'archived') return false
    return String(row?.status || '').toLowerCase() === 'sent'
  }

  const setOpened = async (email, opened) => {
    try {
      const res = await api.post(`/api/campaigns/${id}/opened`, { email, opened });
      const updated = Number(res?.data?.updated || 0)
      if (updated > 0) {
        toast.success(opened ? 'Marked as opened' : 'Marked as not opened');
        load();
      } else {
        toast.info('This campaign has not started (or no email enqueued) for that recipient yet.');
      }
    } catch (e) {
      const errorMsg = e?.response?.data?.detail || 'Failed to update opened state'
      toast.error(errorMsg);
    }
  }

  const trimMiddle = (s, max = 32) => {
    const str = String(s ?? '')
    if (str.length <= max) return str
    const head = Math.ceil((max - 1) * 0.6)
    const tail = (max - 1) - head
    return str.slice(0, head) + '…' + str.slice(-tail)
  }

  // Datatables definitions
  const targetColumns = [
    {
      name: 'Name',
      selector: r => `${r.first_name || ''} ${r.last_name || ''}`.trim(),
      sortable: true,
      grow: 1.6
    },
    {
      name: 'Email', selector: r => r.email || '',
      sortable: true,
      grow: 1.8
    },
    {
      name: 'Status',
      sortable: true,
      width: '160px',
      selector: r => r.status || '',
      cell: r => <StatusBadge status={r.status} />
    },
    {
      name: 'Sent at',
      selector: r => r.sent_at ? new Date(r.sent_at).toLocaleString() : '—',
      sortable: true,
      width: '190px'
    },
    {
      name: 'Error',
      grow: 2.2,
      cell: r => <TruncatedTextWithTooltip text={r.error} maxWidth={460} />
    },
    {
      name: 'Opened',
      width: '220px',
      sortable: false,
      center: true,
      cell: r => {
        const allowed = canToggleOpen(r)
        const ts = r.opened_at ? new Date(r.opened_at).toLocaleString() : ''
        const onToggle = (e) => {
          e.stopPropagation()
          if (!allowed) {
            if (detail?.status === 'archived') {
              toast.info('Archived campaigns are read-only and cannot be edited.')
            } else {
              toast.info('Only sent emails can be marked as opened.')
            }
            return
          }
          setConfirmOpen({ show: true, email: r.email, nextVal: e.target.checked })
        }
        return (
          <div className="inline-flex items-center justify-center gap-3 w-full">
            <span
              className="text-xs text-slate-500 dark:text-slate-400 w-[150px] text-right whitespace-nowrap leading-none"
              title={ts}
            >
              {ts}
            </span>
            <div className="check-accent form-check m-0 table-checkbox">
              <input
                className="form-check-input me-0"
                type="checkbox"
                checked={!!r.opened}
                onChange={onToggle}
                disabled={!allowed}
                aria-label={`Opened for ${r.email}`}
              />
            </div>
          </div>
        )
      }
    }


  ]

  // Variables datatable
  const filterVarsRows = (rows) => {
    const q = (varsQuery || '').toLowerCase().trim()
    if (!q) return rows
    return rows.filter(r => {
      const hay = (r.name + ' ' + r.email + ' ' + Object.values(r.values || {}).join(' ')).toLowerCase()
      return hay.includes(q)
    })
  }

  const varsColumns = varsData ? ([
    {
      name: 'Name',
      selector: r => r.name,
      sortable: true,
      grow: 1.2
    },
    {
      name: 'Email',
      selector: r => r.email,
      sortable: true,
      grow: 1.6
    },
    ...varsData.headers.map(h => {
      const lower = h.toLowerCase()
      const allowCopy = !(lower === 'extrafield' || lower === 'name' || lower === 'email')

      return {
        name: h,
        sortable: false,
        grow: 1.2,
        cell: r => {
          const raw = r.values?.[h] ?? ''
          const trimmed = trimMiddle(raw, 36)

          return (
            <div
              className="grid items-center min-w-0 gap-2"
              style={{ gridTemplateColumns: 'minmax(0,1fr) auto' }}
            >
              <OverlayTrigger
                placement="top"
                delay={{ show: 200, hide: 80 }}
                flip
                popperConfig={{ strategy: 'fixed' }}
                overlay={<Tooltip>{String(raw)}</Tooltip>}
              >
                <span className="block truncate" title={String(raw)}>
                  {trimmed}
                </span>
              </OverlayTrigger>

              {allowCopy && raw ? (
                <button
                  type="button"
                  className="inline-flex h-7 w-7 items-center justify-center rounded-md hover:bg-black/5 dark:hover:bg-white/10"
                  onClick={(e) => { e.stopPropagation(); copyToClipboard(raw) }}
                  aria-label={`Copy ${h}`}
                  title="Copy"
                >
                  <Copy size={14} />
                </button>
              ) : null}
            </div>
          )
        }
      }
    }),
    {
    name: 'Opened',
    width: '90px',
    center: true,
    cell: r => {
      const t = targets.find(t => t.email === r.email)
      const allowed = canToggleOpen(t || {})
      const checked = !!t?.opened
      return (
        <div className="check-accent form-check m-0 table-checkbox">
          <input
            className="form-check-input me-0"
            type="checkbox"
            checked={checked}
            disabled={!allowed}
            onChange={(e) => {
              e.stopPropagation()
              if (!allowed) {
                if (detail?.status === 'archived') {
                  toast.info('Archived campaigns are read-only and cannot be edited.')
                } else {
                  toast.info('Only sent emails can be marked as opened.')
                }
                return
              }
              setConfirmOpen({ show: true, email: r.email, nextVal: e.target.checked })
            }}
            aria-label={`Opened for ${r.email}`}
          />
        </div>
      )
    }
  }


  ]) : []

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <OverlayTrigger placement="bottom" overlay={<Tooltip>Back</Tooltip>}>
              <button className="rail-btn" onClick={() => nav('/campaigns')} aria-label="Back">
                <ArrowLeft size={18} />
              </button>
            </OverlayTrigger>
            <h1 className="text-xl font-semibold text-slate-900 dark:text-white m-0 truncate">
              {detail.name}
            </h1>
          </div>

          <div className="mt-1 text-sm text-slate-600 dark:text-slate-300">
            Server: <strong>{detail.server}</strong> • Profile: <strong>{detail.profile}</strong> ({detail.profile_email}) • Template: <strong>{detail.template}</strong> • Lists:{' '}
            {Array.isArray(detail.lists) && detail.lists.length > 0 ? (
              <>
                {detail.lists.join(', ')}
                {detail.remove_duplicate_targets && (
                  <span className="ml-1 text-emerald-700 dark:text-emerald-300">(duplicates removed)</span>
                )}
              </>
            ) : (
              '—'
            )}
          </div>
          {detail.scheduled_start_at && (
            <div className="text-xs text-slate-500 dark:text-slate-400">
              Scheduled: {new Date(detail.scheduled_start_at).toLocaleString()}
            </div>
          )}
          {detail.use_batches && (
            <div className="text-xs text-slate-500 dark:text-slate-400">
              Batches: size <strong>{detail.batch_size}</strong> • delay <strong>{detail.batch_delay_seconds}</strong>s
            </div>
          )}
        </div>

        <div className="flex flex-wrap gap-2 justify-end">
          <OverlayTrigger placement="bottom" overlay={<Tooltip>Reload</Tooltip>}>
            <button className="rail-btn" onClick={load}><RefreshCw size={18} /></button>
          </OverlayTrigger>
          <OverlayTrigger placement="bottom" overlay={<Tooltip>Export results</Tooltip>}>
            <button className="rail-btn" onClick={exportResults}><Download size={18} /></button>
          </OverlayTrigger>

          {detail.status === 'stopped' && (
            <>
              <OverlayTrigger placement="bottom" overlay={<Tooltip>Start</Tooltip>}>
                <button className="rail-btn text-[var(--mlf-primary)]" onClick={start}><Play size={18} /></button>
              </OverlayTrigger>
              <OverlayTrigger placement="bottom" overlay={<Tooltip>Schedule</Tooltip>}>
                <button className="rail-btn" onClick={openSchedule}><CalendarClock size={18} /></button>
              </OverlayTrigger>
            </>
          )}

          {detail.status === 'running' && (
            <OverlayTrigger placement="bottom" overlay={<Tooltip>Pause</Tooltip>}>
              <button className="rail-btn" onClick={pause}><Pause size={18} /></button>
            </OverlayTrigger>
          )}

          {detail.status === 'paused' && (
            <>
              <OverlayTrigger placement="bottom" overlay={<Tooltip>Resume</Tooltip>}>
                <button className="rail-btn text-[var(--mlf-primary)]" onClick={resume}><Play size={18} /></button>
              </OverlayTrigger>
              <OverlayTrigger placement="bottom" overlay={<Tooltip>Schedule</Tooltip>}>
                <button className="rail-btn" onClick={openSchedule}><CalendarClock size={18} /></button>
              </OverlayTrigger>
            </>
          )}

          {detail.status === 'scheduled' && (
            <>
              <OverlayTrigger placement="bottom" overlay={<Tooltip>Change schedule</Tooltip>}>
                <button className="rail-btn" onClick={openSchedule}><CalendarCheck size={18} /></button>
              </OverlayTrigger>
              <OverlayTrigger placement="bottom" overlay={<Tooltip>Unschedule</Tooltip>}>
                <button className="rail-btn" onClick={() => setConfirmUnsched(true)}><CalendarX size={18} /></button>
              </OverlayTrigger>
            </>
          )}

          {detail.status !== 'archived' ? (
            <OverlayTrigger placement="bottom" overlay={<Tooltip>Archive</Tooltip>}>
              <button className="rail-btn" onClick={() => setConfirmArchive(true)}><Archive size={18} /></button>
            </OverlayTrigger>
          ) : (
            <OverlayTrigger placement="bottom" overlay={<Tooltip>Delete</Tooltip>}>
              <button className="rail-btn" onClick={() => setConfirmDelete(true)}><Trash2 size={18} /></button>
            </OverlayTrigger>
          )}
        </div>
      </div>

      {detail.last_error ? (
        <div className="rounded-2xl ring-1 ring-rose-500/25 bg-rose-50/90 dark:bg-rose-500/10 shadow-card">
          <div className="p-4 relative">
            <div className="absolute top-3 right-3 z-10 flex items-center gap-1">
              <OverlayTrigger placement="bottom" overlay={<Tooltip>Copy</Tooltip>}>
                <button
                  type="button"
                  className="rail-btn"
                  onClick={async () => {
                    const txt = showErrorDetails
                      ? (detail.last_error_trace || detail.last_error || '')
                      : (detail.last_error || '')
                    copyToClipboard(String(txt))
                  }}
                  aria-label="Copy error"
                >
                  <Copy size={18} />
                </button>
              </OverlayTrigger>

              {detail.last_error_trace ? (
                <OverlayTrigger
                  placement="bottom"
                  overlay={<Tooltip>{showErrorDetails ? 'Hide details' : 'Show details'}</Tooltip>}
                >
                  <button
                    type="button"
                    className="rail-btn"
                    onClick={() => setShowErrorDetails(v => !v)}
                    aria-label={showErrorDetails ? 'Hide details' : 'Show details'}
                  >
                    {showErrorDetails ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                  </button>
                </OverlayTrigger>
              ) : null}

              <OverlayTrigger placement="bottom" overlay={<Tooltip>Dismiss</Tooltip>}>
                <button
                  type="button"
                  className="rail-btn"
                  onClick={async () => {
                    try {
                      await api.post(`/api/campaigns/${id}/clear_error`)
                      toast.info('Error cleared')
                      setShowErrorDetails(false)
                      load()
                    } catch (e) {
                      toast.error(e?.response?.data?.detail || 'Failed to clear')
                    }
                  }}
                  aria-label="Dismiss"
                >
                  <X size={18} />
                </button>
              </OverlayTrigger>
            </div>

            <div className="pr-20">
              <div className="text-sm font-semibold text-rose-700 dark:text-rose-200">
                Worker error {detail.last_error_at ? `• ${new Date(detail.last_error_at).toLocaleString()}` : ''}
              </div>

              <div
                className="mt-1 text-sm text-rose-800 dark:text-rose-100 break-words"
                style={{ whiteSpace: 'pre-wrap' }}
              >
                {detail.last_error}
              </div>

              {showErrorDetails && detail.last_error_trace ? (
                <pre
                  className="mt-3 block w-full text-xs overflow-auto max-h-96 p-3 rounded-lg
                            bg-white/70 dark:bg-white/5 ring-1 ring-black/10 dark:ring-white/10
                            text-rose-900/90 dark:text-rose-100/90"
                  style={{
                    whiteSpace: 'pre-wrap',
                    fontFamily:
                      'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace'
                  }}
                >
                  {detail.last_error_trace}
                </pre>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}


      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          ['Total', detail.total],
          ['Sent', detail.sent],
          ['Failed', detail.failed],
          ['Pending', detail.pending],
        ].map(([label, val], i) => (
          <div key={i} className="rounded-2xl ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-glass/80 shadow-card">
            <div className="p-4">
              <div className="text-xs font-medium text-slate-600 dark:text-slate-300">{label}</div>
              <div className="text-2xl font-semibold text-slate-900 dark:text-white">{val}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Calendar invite card */}
      {isInvite && (
        <div className="rounded-2xl ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-glass/80 shadow-card">
          <div className="p-4">
            <h2 className="text-sm font-semibold text-slate-900 dark:text-white mb-2">Calendar invite</h2>
            <div className="text-sm text-slate-700 dark:text-slate-200 space-y-1">
              <div>
                <span className="text-slate-500">UID: </span>
                {detail.calendar_uid ? <code>{detail.calendar_uid}</code> : <span className="text-slate-500">Not generated yet</span>}
              </div>
              <div><span className="text-slate-500">ICS PRODID: </span><code>{detail.calendar_ics_prodid || '—'}</code></div>
              <div><span className="text-slate-500">Meeting info: </span><code>{meetingLine(detail)}</code></div>
              {detail.meeting_url && (
                <div className="flex items-center gap-2">
                  <span className="text-slate-500">
                    Meeting URL
                    {detail.meeting_provider && detail.meeting_provider !== 'none' && (
                      <span className="ml-1 text-slate-500/80 text-xs">
                        (
                        {detail.meeting_provider === 'gmeet'
                          ? 'Google Meet'
                          : detail.meeting_provider === 'teams'
                            ? 'Teams'
                            : detail.meeting_provider}
                        )
                      </span>
                    )}
                    :
                  </span>
                  <code className="truncate" title={detail.meeting_url}>
                    {detail.meeting_url}
                  </code>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Calendar reschedule card */}
      {isResched && (
        <div className="rounded-2xl ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-glass/80 shadow-card">
          <div className="p-4">
            <h2 className="text-sm font-semibold text-slate-900 dark:text-white mb-2">Calendar reschedule</h2>
            <div className="text-sm text-slate-700 dark:text-slate-200 space-y-1">
              <div>
                <span className="text-slate-500">UID: </span>
                {detail.calendar_uid ? <code>{detail.calendar_uid}</code> : <span className="text-slate-500">Not set</span>}
              </div>
              <div>
                <span className="text-slate-500">Sequence: </span>
                {typeof detail.meeting_sequence === 'number' ? <code>{detail.meeting_sequence}</code> : <span className="text-slate-500">—</span>}
              </div>
              <div><span className="text-slate-500">ICS PRODID: </span><code>{detail.calendar_ics_prodid || '—'}</code></div>
              <div><span className="text-slate-500">Meeting info: </span><code>{meetingLine(detail)}</code></div>

              {detail.meeting_url && (
                <div className="flex items-center gap-2">
                  <span className="text-slate-500">
                    Meeting URL
                    {detail.meeting_provider && detail.meeting_provider !== 'none' && (
                      <span className="ml-1 text-slate-500/80 text-xs">
                        (
                        {detail.meeting_provider === 'gmeet'
                          ? 'Google Meet'
                          : detail.meeting_provider === 'teams'
                            ? 'Teams'
                            : detail.meeting_provider}
                        )
                      </span>
                    )}
                    :
                  </span>
                  <code className="truncate" title={detail.meeting_url}>
                    {detail.meeting_url}
                  </code>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Calendar cancellation card */}
      {isCancel && (
        <div className="rounded-2xl ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-glass/80 shadow-card">
          <div className="p-4">
            <h2 className="text-sm font-semibold text-slate-900 dark:text-white mb-2">Calendar cancellation</h2>
            <div className="text-sm text-slate-700 dark:text-slate-200 space-y-1">
              <div>
                <span className="text-slate-500">UID: </span>
                {detail.calendar_uid ? <code>{detail.calendar_uid}</code> : <span className="text-slate-500">Not set</span>}
              </div>
              <div>
                <span className="text-slate-500">Sequence: </span>
                {typeof detail.meeting_sequence === 'number' ? <code>{detail.meeting_sequence}</code> : <span className="text-slate-500">—</span>}
              </div>
              <div><span className="text-slate-500">ICS PRODID: </span><code>{detail.calendar_ics_prodid || '—'}</code></div>
              <div><span className="text-slate-500">Meeting info: </span><code>{meetingLine(detail)}</code></div>
            </div>
          </div>
        </div>
      )}

      {/* Timeline */}
      <div className="rounded-2xl ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-glass/80 shadow-card">
        <div className="p-4">
          <h2 className="text-sm font-semibold text-slate-900 dark:text-white mb-2">Timeline</h2>
          <TimelineBar logs={logs} />
        </div>
      </div>

      {/* Targets & Status */}
      <div className="rounded-2xl ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-glass/80 shadow-card">
        <div className="p-4">
          <div className="d-flex justify-content-between align-items-center">
            <h2 className="text-sm font-semibold text-slate-900 dark:text-white mb-0">
              Targets &amp; Status
            </h2>
            <div className="d-flex align-items-center gap-2">
              <div className="position-relative" style={{ width: 220 }}>
                <Search
                  size={16}
                  className="position-absolute"
                  style={{ left: 12, top: '50%', transform: 'translateY(-50%)', opacity: 0.7, pointerEvents: 'none' }}
                />
                <input
                  className={inputClsSearchbar}
                  style={{ paddingLeft: '2.4rem', height: 36 }}
                  placeholder="Search targets…"
                  value={targetsQuery}
                  onChange={(e) => setTargetsQuery(e.target.value)}
                  aria-label="Search targets"
                />
              </div>

               <OverlayTrigger
                  placement="top"
                  overlay={<Tooltip>{openedOnly ? 'Show all targets' : 'Show only opened'}</Tooltip>}
                >
                  <button
                    className={`rail-btn ${openedOnly ? 'text-[var(--mlf-primary)]' : ''}`}
                    onClick={() => setOpenedOnly(v => !v)}
                    aria-pressed={openedOnly}
                    aria-label={openedOnly ? 'Show all targets' : 'Show only opened'}
                  >
                    <MailOpen size={18} />
                  </button>
                </OverlayTrigger>

              <OverlayTrigger placement="top" overlay={<Tooltip>See generated variables</Tooltip>}>
                <button className="rail-btn" onClick={openVars} aria-label="Variables">
                  <RotateCcwKey size={18} />
                </button>
              </OverlayTrigger>
            </div>
          </div>

          <div className="mt-2">
            <DataTable
              columns={targetColumns}
              data={filteredTargets}
              theme={isDark ? 'datatablesDark' : 'datatablesLight'}
              customStyles={tableStyles(isDark)}
              striped
              highlightOnHover
              responsive
              pagination
              paginationPerPage={10}
              paginationRowsPerPageOptions={[10, 20, 50, 100]}
              persistTableHead
              dense
              noDataComponent={<div className="p-3 text-sm text-slate-600 dark:text-slate-300">No targets.</div>}
            />
          </div>
        </div>
      </div>

      {/* Schedule modal */}
      <Modal show={showSched} onHide={() => setShowSched(false)} centered contentClassName="modal-matte">
        <Modal.Header closeButton className="border-0 pt-4 px-4">
          <Modal.Title>Schedule start</Modal.Title>
        </Modal.Header>
        <Modal.Body className="px-4 pb-3">
          <Form.Control type="datetime-local" className={inputClsSearchbar} value={when} onChange={(e) => setWhen(e.target.value)} />
        </Modal.Body>
        <Modal.Footer className="border-0 px-4 pb-4">
          <Button variant="secondary" onClick={() => setShowSched(false)}>Cancel</Button>
          <Button variant="primary" onClick={schedule}>Save</Button>
        </Modal.Footer>
      </Modal>

      {/* Confirm unschedule modal */}
      <Modal show={confirmUnsched} onHide={() => setConfirmUnsched(false)} centered contentClassName="modal-matte">
        <Modal.Header closeButton className="border-0 pt-4 px-4"><Modal.Title>Unschedule campaign?</Modal.Title></Modal.Header>
        <Modal.Body className="px-4 pb-2">
          This will remove the scheduled start time. You can schedule it again later.
        </Modal.Body>
        <Modal.Footer className="border-0 px-4 pb-4">
          <Button variant="secondary" onClick={() => setConfirmUnsched(false)}>Cancel</Button>
          <Button
            variant="warning"
            onClick={async () => {
              try {
                await api.post(`/api/campaigns/${id}/unschedule`)
                toast.info('Schedule removed')
                setConfirmUnsched(false)
                load()
              } catch (e) {
                toast.error(e.response?.data?.detail || 'Action failed')
              }
            }}
          >
            Yes, unschedule
          </Button>
        </Modal.Footer>
      </Modal>

      {/* Confirm archive modal */}
      <Modal show={confirmArchive} onHide={() => setConfirmArchive(false)} centered contentClassName="modal-matte">
        <Modal.Header closeButton className="border-0 pt-4 px-4"><Modal.Title>Archive this campaign?</Modal.Title></Modal.Header>
        <Modal.Body className="px-4 pb-2">
          Archiving will hide this campaign from active views. You can still access it in archived lists.
        </Modal.Body>
        <Modal.Footer className="border-0 px-4 pb-4">
          <Button variant="secondary" onClick={() => setConfirmArchive(false)}>Cancel</Button>
          <Button
            variant="rose"
            onClick={async () => {
              try {
                await api.post(`/api/campaigns/${id}/archive`)
                toast.info('Campaign archived')
                setConfirmArchive(false)
                load()
              } catch (e) {
                toast.error(e?.response?.data?.detail || 'Archive failed')
              }
            }}
          >
            Yes, archive
          </Button>
        </Modal.Footer>
      </Modal>

      {/* Confirm delete modal */}
      <Modal show={confirmDelete} onHide={() => setConfirmDelete(false)} centered contentClassName="modal-matte">
        <Modal.Header closeButton className="border-0 pt-4 px-4"><Modal.Title>Delete campaign?</Modal.Title></Modal.Header>
        <Modal.Body className="px-4 pb-2">
          This will permanently delete this archived campaign and its logs. This cannot be undone.
        </Modal.Body>
        <Modal.Footer className="border-0 px-4 pb-4">
          <Button variant="secondary" onClick={() => setConfirmDelete(false)}>Cancel</Button>
          <Button
            variant="rose"
            onClick={async () => {
              try {
                await api.delete(`/api/campaigns/${id}`)
                toast.success('Campaign deleted')
                setConfirmDelete(false)
                nav('/campaigns')
              } catch (e) {
                toast.error(e?.response?.data?.detail || 'Delete failed')
              }
            }}
          >
            Yes, delete
          </Button>
        </Modal.Footer>
      </Modal>

      {/* Variables modal */}
      <Modal show={showVars} onHide={() => setShowVars(false)} size="xl" centered scrollable contentClassName="modal-matte">
        <Modal.Header closeButton className="border-0 pt-4 px-4">
          <Modal.Title>Campaign variables</Modal.Title>
        </Modal.Header>
        <Modal.Body className="px-4 pb-3">
          {!varsData ? (
            <div className="text-slate-600 dark:text-slate-300 text-sm">Loading…</div>
          ) : (
            <>
              <div className="mb-3">
                <div className="text-slate-500 dark:text-slate-400 text-xs mb-2">Static variables used</div>
                {Object.keys(varsData.static_vars).length === 0 ? (
                  <div className="text-slate-600 dark:text-slate-300 text-sm">No static variables detected in this template.</div>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(varsData.static_vars).map(([k, v]) => (
                      <span
                        key={k}
                        className="inline-flex items-center gap-2 px-2 py-1 rounded-md text-[12px]
                                   bg-white/90 dark:bg-white/10 ring-1 ring-black/10 dark:ring-white/10
                                   text-slate-800 dark:text-slate-100 max-w-[420px]"
                        title={String(v)}
                      >
                        <span className="font-semibold">{k}:</span>
                        <span className="truncate">{String(v)}</span>
                        <button
                          type="button"
                          className="inline-flex h-6 w-6 items-center justify-center rounded hover:bg-black/5 dark:hover:bg-white/10"
                          onClick={() => copyToClipboard(v)}
                          aria-label="Copy"
                        >
                          <Copy size={13} />
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <div className="relative mb-2">
                <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 opacity-70" />
                <input
                  className={inputClsSearchbar}
                  style={{ paddingLeft: '2.4rem' }}
                  placeholder="Search by name, email or value…"
                  value={varsQuery}
                  onChange={(e) => setVarsQuery(e.target.value)}
                />
              </div>

              <DataTable
                columns={varsColumns}
                data={filterVarsRows(varsData.rows)}
                theme={isDark ? 'datatablesDark' : 'datatablesLight'}
                customStyles={tableStyles(isDark)}
                striped
                highlightOnHover
                responsive
                pagination
                paginationPerPage={8}
                paginationRowsPerPageOptions={[8, 15, 25, 50]}
                persistTableHead
                dense
                noDataComponent={<div className="p-3 text-sm text-slate-600 dark:text-slate-300">No generated values yet.</div>}
              />
            </>
          )}
        </Modal.Body>
        <Modal.Footer className="border-0 px-4 pb-4">
          <Button variant="secondary" onClick={() => setShowVars(false)}>Close</Button>
        </Modal.Footer>
      </Modal>

      {/* Confirm marked as opened */}
      <Modal show={confirmOpen.show} onHide={() => setConfirmOpen({ show: false, email: null, nextVal: true })} centered contentClassName="modal-matte">
        <Modal.Header closeButton className="border-0 pt-4 px-4">
          <Modal.Title>{confirmOpen.nextVal ? 'Mark as opened?' : 'Mark as not opened?'}</Modal.Title>
        </Modal.Header>
        <Modal.Body className="px-4 pb-2">
          {confirmOpen.nextVal ? (
            <>Do you want to confirm that <strong>{confirmOpen.email}</strong> has opened the email?</>
          ) : (
            <>Do you want to unmark <strong>{confirmOpen.email}</strong> as opened?</>
          )}
        </Modal.Body>
        <Modal.Footer className="border-0 px-4 pb-4">
          <Button variant="secondary" onClick={() => setConfirmOpen({ show: false, email: null, nextVal: true })}>Cancel</Button>
          <Button
            variant={"primary"}
            onClick={async () => {
              const { email, nextVal } = confirmOpen
              setConfirmOpen({ show: false, email: null, nextVal: true })
              await setOpened(email, nextVal)
            }}
          >
            {confirmOpen.nextVal ? 'Yes, mark opened' : 'Yes, unmark'}
          </Button>
        </Modal.Footer>
      </Modal>

    </div>
  )
}
