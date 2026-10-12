import React, { useEffect, useMemo, useRef, useState, forwardRef } from 'react'
import { client } from '../lib/api'
import DataTable from 'react-data-table-component'
import { OverlayTrigger, Tooltip, Modal, Button, Dropdown, Overlay } from 'react-bootstrap'
import { toast } from 'react-toastify'
import ThemedSelect from '../components/ThemedSelect'
import {
  Plus, MoreVertical, Pencil, Trash2, Search, CircleHelp,
  Braces, ScanText, Video, UserPlus, Copy
} from 'lucide-react'
import '../components/datatableThemes'
import { useTheme } from '../../hooks/useTheme'
import { copyToClipboard } from '../utils/common'
import { inputCls, inputSearchbarCls } from '../utils/styles'

// Suggestion inputs
function SuggestInput({ value, onChange, placeholder, options = [], type = 'text', style }) {
  const [open, setOpen] = useState(false)
  const wrapRef = useRef(null)

  const filtered = useMemo(() => {
    const q = (value || '').toLowerCase().trim()
    if (!q) return options.slice(0, 8)
    return options.filter(o => o.toLowerCase().includes(q)).slice(0, 8)
  }, [value, options])

  useEffect(() => {
    const onDoc = (e) => {
      if (!wrapRef.current) return
      if (!wrapRef.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  return (
    <div ref={wrapRef} className="relative" style={style}>
      <input
        type={type}
        className="rounded-xl bg-white/70 dark:bg-white/5 px-4 py-2 text-sm
                   text-slate-900 dark:text-slate-100 ring-1 ring-black/10 dark:ring-white/10
                   placeholder:text-slate-500 dark:placeholder:text-slate-400
                   focus:outline-none focus:ring-2 focus:ring-primary/70 w-full"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        onFocus={() => setOpen(true)}
        autoComplete="off"
      />
      {open && filtered.length > 0 && (
        <div
          className="suggest-menu"
          style={{ position: 'absolute', insetInline: 0, top: 'calc(100% + 6px)', zIndex: 1055 }}
        >
          {filtered.map((opt) => (
            <button
              type="button"
              key={opt}
              className="suggest-item"
              onMouseDown={(e) => { e.preventDefault(); onChange(opt); setOpen(false) }}
            >
              {opt}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default function Config() {
  const api = client()

  // Tabs
  const [tab, setTab] = useState('vars') // vars|delivery

  // Data
  const [vars, setVars] = useState([])
  const [settings, setSettings] = useState({})
  const [q, setQ] = useState('')

  // Variables modal
  const [show, setShow] = useState(false)
  const [edit, setEdit] = useState(null)
  const [form, setForm] = useState({ name: '', kind: 'text', value: '', pattern: '', tenant_guid: '', per_recipient: false })

  // Confirm delete modal
  const [showDel, setShowDel] = useState(false)
  const [rowToDel, setRowToDel] = useState(null)

  // Tenant resolver popover
  const [tenOpen, setTenOpen] = useState(false)
  const [tenantDomain, setTenantDomain] = useState('')
  const [tenantResolving, setTenantResolving] = useState(false)
  const tenBtnRef = useRef(null)
  const modalBodyRef = useRef(null)

  // Theme selector
  const isDark = useTheme()

  // Constants
  const PRODID_OPTIONS = [
    'Microsoft Exchange Server 2019',
    '-//Microsoft Corporation//Outlook 16.0 MIMEDIR//EN',
    '-//Microsoft Corporation//CDO for Windows 2000//EN',
    'Microsoft Office Outlook 16.0',
    'Microsoft Exchange Calendar Agent',
    '-//Google Inc//Google Calendar 70.9054//EN'
  ]

  const MESSAGE_ID_FULL_REGEX_OPTIONS = [
    '<[A-Z0-9]{2}PR[0-9]{2}[A-Z]{2}[A-F0-9]{32}@[A-Z]{2}0PR[0-9]{2}CB[0-9]{4}\\.[A-Z]{3}PRD[0-9]{2}\\.PROD\\.OUTLOOK\\.COM>',
    '<[a-f0-9]{8}\\.[a-f0-9]{8}\\.[a-f0-9]{6}\\.[a-f0-9]{4}@mx\\.google\\.com>',
    '[A-Za-z0-9._%+-]{24}@domain.com',
  ]

  const CAL_UID_REGEX_OPTIONS = [
    '[A-F0-9]{64}', // 64 hex (Outlook)
    '[0-9A-Za-z]{22,32}', // base62-ish token
    '[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}', // GUID/UUID
    '[0-9]{10}\\.[A-Za-z0-9]{8}@example\\.com', // email-like UID (valid for RFC5545)
    '[a-z0-9]{26}@google\\.com' // Google
  ]

  const load = async () => {
    const [v, s] = await Promise.all([
      api.get('/api/config/vars'),
      api.get('/api/config/settings'),
    ])
    setVars(v.data); setSettings(s.data.values || {})
  }
  useEffect(() => { load() }, [])

  // Helpers
  const prettyErr = (e) => {
    const d = e?.response?.data?.detail
    if (!d) return 'Failed to save variable'
    if (typeof d === 'string') return d
    if (Array.isArray(d) && d.length && d[0]?.msg) return d[0].msg
    return 'Failed to save variable'
  }

  const openCreate = () => {
    setEdit(null)
    setForm({ name: '', kind: 'text', value: '', pattern: '', tenant_guid: '', per_recipient: false })
    setShow(true)
  }

  const openEdit = (r) => {
    setEdit(r)
    setForm({ ...r })
    setShow(true)
  }

  const askDeleteVar = (r) => {
    setRowToDel(r)
    setShowDel(true)
  }

  const confirmDeleteVar = async () => {
    if (!rowToDel) return
    try {
      await api.delete(`/api/config/vars/${rowToDel.id}`)
      toast.success('Variable deleted')
      setShowDel(false)
      setRowToDel(null)
      load()
    }
    catch {
      toast.error('Failed to delete variable')
    }
  }

  const saveVar = async () => {
    try {
      const payload = { ...form }
      if (payload.kind === 'teams' && !payload.name.startsWith('TeamsMeeting_')) {
        payload.name = `TeamsMeeting_${payload.name || 'Var'}`
      }
      if (edit) await api.put(`/api/config/vars/${edit.id}`, payload)
      else await api.post('/api/config/vars', payload)

      toast.success('Variable saved')
      setShow(false)
      setTenOpen(false)
      load()

    } catch (e) {
      toast.error(prettyErr(e))
    }
  }

  const saveSettings = async () => {
    try {
      await api.put('/api/config/settings', { values: settings })
      toast.success('Settings saved')
      load()
    }
    catch {
      toast.error('Failed to save settings')
    }
  }

  // Search
  const filteredVars = useMemo(() => {
    const s = q.trim().toLowerCase()
    return vars.filter(r => {
      const val = r.kind === 'text' ? r.value || ''
        : r.kind === 'regex' ? r.pattern || ''
          : r.kind === 'teams' ? (r.per_recipient ? '(per email)' : (r.value || '')) : ''
      return !s ||
        r.name?.toLowerCase().includes(s) ||
        r.kind?.toLowerCase().includes(s) ||
        val.toLowerCase().includes(s)
    })
  }, [vars, q])

  const Toggle = forwardRef(({ onClick }, ref) => (
    <button
      ref={ref}
      onClick={(e) => { e.preventDefault(); onClick(e) }}
      className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-transparent hover:bg-black/5 dark:hover:bg-white/10"
      aria-label="Row actions"
    >
      <MoreVertical size={16} />
    </button>
  ))

  // Select options
  const kindOptions = [
    { value: 'text', label: 'Text (constant)' },
    { value: 'regex', label: 'Regex (random each email)' },
    { value: 'teams', label: 'Teams Meeting URL' },
  ];

  // Badges
  const PerEmailBadge = () => (
    <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-lg text-[11px] font-semibold leading-none ring-1 bg-fuchsia-500/5 text-fuchsia-700 ring-fuchsia-500/25 dark:bg-fuchsia-500/10 dark:text-fuchsia-300 dark:ring-fuchsia-500/30">
      <UserPlus size={11} /> Per email
    </span>
  )

  const KindBadge = ({ kind }) => {
    if (kind === 'regex') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-lg text-[11px] font-semibold leading-none ring-1 bg-amber-500/5 text-amber-800 ring-amber-500/25 dark:bg-amber-500/10 dark:text-amber-300 dark:ring-amber-500/30">
          <Braces size={12} /> Regex
        </span>
      )
    }
    
    if (kind === 'teams') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-lg text-[11px] font-semibold leading-none ring-1 bg-sky-500/5 text-sky-800 ring-sky-500/25 dark:bg-sky-500/10 dark:text-sky-300 dark:ring-sky-500/30">
          <Video size={12} /> Teams
        </span>
      )
    }

    // Static text
    return (
      <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-lg text-[11px] font-semibold leading-none ring-1 bg-indigo-500/5 text-indigo-700 ring-indigo-500/25 dark:bg-indigo-500/10 dark:text-indigo-300 dark:ring-indigo-500/30">
        <ScanText size={12} /> Static
      </span>
    )
  }

  // Datatables definitions
  const columns = [
    {
      name: 'Name',
      sortable: true,
      grow: 1,
      minWidth: '280px',
      maxWidth: '360px',
      cell: r => (
        <div className="truncate" style={{ maxWidth: 240 }} title={r.name || ''}>
          {r.name || ''}
        </div>
      )
    },
    {
      name: 'Type',
      sortable: true,
      width: '280px',
      cell: r => (
        <div className="flex items-center gap-2">
          <KindBadge kind={r.kind} />
          {r.kind === 'regex' && <PerEmailBadge />}
          {r.kind === 'teams' && r.per_recipient && <PerEmailBadge />}
        </div>
      )
    },
    {
      name: 'Value',
      grow: 3,
      cell: r => {
        const isStaticText = r.kind === 'text' && r.value
        const isStaticTeams = r.kind === 'teams' && !r.per_recipient && r.value
        const canCopy = isStaticText || isStaticTeams
        const val =
          r.kind === 'text' ? (r.value || '') :
            r.kind === 'regex' ? (r.pattern || '') :
              r.kind === 'teams' ? (r.per_recipient ? '(per email)' : (r.value || '')) : ''
        return (
          <div className="flex items-center gap-2">
            <span className="truncate" style={{ maxWidth: 480 }} title={val}>{val}</span>
            {canCopy && (
              <OverlayTrigger placement="top" overlay={<Tooltip>Copy value</Tooltip>}>
                <button
                  className="inline-flex h-7 w-7 items-center justify-center rounded-lg text-[var(--mlf-primary)]
                             hover:bg-black/5 dark:hover:bg-white/10"
                  onClick={(e) => { e.stopPropagation(); copyToClipboard(val) }}
                  aria-label="Copy value"
                >
                  <Copy size={14} />
                </button>
              </OverlayTrigger>
            )}
          </div>
        )
      }
    },
    {
      name: '',
      width: '56px',
      cell: r => (
        <div className="position-relative z-20">
          <Dropdown align="end">
            <Dropdown.Toggle as={Toggle} />
            <Dropdown.Menu
              renderOnMount
              className={`${isDark ? 'dropdown-menu-dark' : ''} menu-elevated`}
              popperConfig={{
                strategy: 'fixed',
                modifiers: [
                  { name: 'computeStyles', options: { adaptive: false } },
                  { name: 'preventOverflow', options: { padding: 8, boundary: 'viewport' } },
                ],
              }}
            >
              <Dropdown.Item onClick={() => openEdit(r)}>
                <Pencil size={14} className="me-2" /> Edit
              </Dropdown.Item>
              <Dropdown.Item onClick={() => askDeleteVar(r)}>
                <Trash2 size={14} className="me-2" /> Delete
              </Dropdown.Item>
            </Dropdown.Menu>
          </Dropdown>
        </div>
      )
    }
  ]

  const tableStyles = useMemo(() => {
    const headBg = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.035)'
    return {
      table: { style: { backgroundColor: 'transparent' } },
      header: { style: { minHeight: '52px', backgroundColor: 'transparent' } },
      headRow: { style: { backgroundColor: headBg, borderRadius: 12, minHeight: '72px' } },
      headCells: {
        style: {
          fontWeight: 700, fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.02em',
          paddingTop: '22px', paddingBottom: '22px', color: isDark ? '#cbd5e1' : '#1f2937',
        },
      },
      rows: {
        style: { minHeight: '60px', backgroundColor: 'transparent', color: isDark ? '#e5e7eb' : '#111827' },
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
  }, [isDark])


  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-slate-900 dark:text-white">Settings</h1>

      {/* Tab selection */}
      <div className="rounded-2xl ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-glass/80 shadow-card p-2">
        <div className="inline-flex rounded-xl bg-white/80 dark:bg-white/5 ring-1 ring-black/10 dark:ring-white/10 p-1">
          <button
            onClick={() => setTab('vars')}
            className={[
              'px-3 py-2 rounded-lg text-sm transition',
              tab === 'vars'
                ? 'bg-primary/15 text-[var(--mlf-primary)] ring-1 ring-primary/25'
                : 'text-slate-700 dark:text-slate-200 hover:bg-black/5 dark:hover:bg-white/10'
            ].join(' ')}
          >
            Variables
          </button>
          <button
            onClick={() => setTab('delivery')}
            className={[
              'px-3 py-2 rounded-lg text-sm transition',
              tab === 'delivery'
                ? 'bg-primary/15 text-[var(--mlf-primary)] ring-1 ring-primary/25'
                : 'text-slate-700 dark:text-slate-200 hover:bg-black/5 dark:hover:bg-white/10'
            ].join(' ')}
          >
            Delivery &amp; Platform
          </button>
        </div>
      </div>

      {/* Variables tab */}
      {tab === 'vars' && (
        <>
          <div className="rounded-2xl ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-glass/80 shadow-card p-2">
            <div className="flex flex-wrap items-center gap-2">
              <div className="relative flex-1 min-w-[280px]">
                <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 opacity-70" />
                <input
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  placeholder="Search variables by name, type, or value"
                  className={inputSearchbarCls}
                />
              </div>
              <div className="ml-auto">
                <OverlayTrigger placement="top" overlay={<Tooltip>Create variable</Tooltip>}>
                  <button
                    onClick={openCreate}
                    className="rail-btn ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-white/5 hover:bg-white/90 dark:hover:bg-white/10 text-[var(--mlf-primary)]"
                    aria-label="Create variable"
                  >
                    <Plus size={18} />
                  </button>
                </OverlayTrigger>
              </div>
            </div>
          </div>

          <div className="rounded-2xl ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-glass/80 shadow-card p-2">
            <DataTable
              columns={columns}
              data={filteredVars}
              theme={isDark ? 'datatablesDark' : 'datatablesLight'}
              customStyles={tableStyles}
              striped
              highlightOnHover
              responsive
              pagination
              paginationPerPage={10}
              paginationRowsPerPageOptions={[10, 20, 50, 100]}
              persistTableHead
              dense
              noDataComponent={<div className="p-4 text-sm text-slate-600 dark:text-slate-300">No variables found.</div>}
            />
          </div>
        </>
      )}

      {/* Delivery tab */}
      {tab === 'delivery' && (
        <div className="rounded-2xl ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-glass/80 shadow-card">
          <div className="p-4 md:p-6 space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Default Batch Size</label>
                <input
                  className={inputCls}
                  type="number"
                  placeholder="10"
                  value={settings.default_batch_size || ''}
                  onChange={e => setSettings({ ...settings, default_batch_size: e.target.value })}
                  style={{ colorScheme: isDark ? 'dark' : 'light' }}
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Default Batch Delay (s)</label>
                <input
                  className={inputCls}
                  type="number"
                  placeholder="300"
                  value={settings.default_batch_delay || ''}
                  onChange={e => setSettings({ ...settings, default_batch_delay: e.target.value })}
                  style={{ colorScheme: isDark ? 'dark' : 'light' }}
                />
              </div>
            </div>

            <div>
              <div>
                <label className="block text-sm font-medium mb-1">SMTP default EHLO</label>
                <input
                  className={inputCls}
                  placeholder="e.g. server.example.com"
                  value={settings.smtp_default_ehlo_domain || ''}
                  onChange={e => setSettings({ ...settings, smtp_default_ehlo_domain: e.target.value })}
                />
                <div className="form-text">Used <strong>only</strong> as a fallback when a server host is not set.</div>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Message-ID</label>
              <SuggestInput
                value={settings.message_id_pattern ?? ''}
                onChange={v => setSettings({ ...settings, message_id_pattern: v })}
                placeholder='e.g. <[a-f0-9]{8}.[a-f0-9]{8}.[a-f0-9]{6}.[a-f0-9]{4}@mx.google.com>'
                options={MESSAGE_ID_FULL_REGEX_OPTIONS}
              />
              <div className="form-text">
                Regex expression to generate the Message-ID (<code>&lt;local@domain.com&gt;</code>).
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">ICS PRODID</label>
              <SuggestInput
                value={settings.ics_prodid ?? ''}
                onChange={v => setSettings({ ...settings, ics_prodid: v })}
                placeholder="e.g. Microsoft Exchange Server 2019"
                options={PRODID_OPTIONS}
              />
              <div className="form-text">
                Value written into <code>PRODID</code> in VCALENDAR invites.
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Calendar UID</label>
              <SuggestInput
                value={settings.calendar_uid_pattern ?? ''}
                onChange={v => setSettings({ ...settings, calendar_uid_pattern: v })}
                placeholder="Leave empty to use default 64-hex."
                options={CAL_UID_REGEX_OPTIONS}
              />
              <div className="form-text">
                Regex used to generate the <code>UID</code> for calendar REQUEST invites.
              </div>
            </div>

            <div className="text-end">
              <Button variant="primary" onClick={saveSettings}>Save Settings</Button>
            </div>
          </div>
        </div>
      )}

      {/* Create/edit variable modal */}
      <Modal show={show} onHide={() => { setShow(false); setTenOpen(false) }} centered contentClassName="modal-matte">
        <Modal.Header closeButton className="border-0 pt-4 px-4">
          <Modal.Title>{edit ? 'Edit Variable' : 'Create Variable'}</Modal.Title>
        </Modal.Header>

        <Modal.Body ref={modalBodyRef} className="px-4 pt-2 pb-4">
          <div className="vstack gap-3">
            <input
              className={inputCls}
              placeholder={form.kind === 'teams' ? 'Variable name (suffix only)' : 'Variable name'}
              value={form.name}
              onChange={e => {
                let v = e.target.value
                if (form.kind === 'teams' && !v.startsWith('TeamsMeeting_')) v = `TeamsMeeting_${v.replace(/^TeamsMeeting[_-]?/, '')}`
                setForm({ ...form, name: v })
              }}
            />

            <ThemedSelect
              options={kindOptions}
              value={form.kind}
              placeholder="Select kind"
              searchable={false}
              onChange={(k) => {
                const base = { ...form, kind: k };
                if (k === 'teams' && !String(base.name || '').startsWith('TeamsMeeting_')) {
                  base.name = `TeamsMeeting_${String(base.name || 'Var').replace(/^TeamsMeeting[_-]?/, '')}`;
                }
                setForm(base);
              }}
            />

            {form.kind === 'text' && (
              <input
                className={inputCls}
                placeholder="Value (e.g. https://myurl.com)"
                value={form.value || ''}
                onChange={e => setForm({ ...form, value: e.target.value })}
              />
            )}
            {form.kind === 'regex' && (
              <input
                className={inputCls}
                placeholder="Regex pattern (e.g. [A-Za-z0-9]{8})"
                value={form.pattern || ''}
                onChange={e => setForm({ ...form, pattern: e.target.value })}
              />
            )}

            {form.kind === 'teams' && (
              <>
                <div>
                  <label className="form-label flex items-center gap-2">
                    Tenant GUID
                    <button
                      type="button"
                      ref={tenBtnRef}
                      title="Resolve from domain"
                      aria-label="Resolve from domain"
                      className="inline-flex items-center justify-center h-6 w-6 rounded hover:bg-black/5 dark:hover:bg-white/10 text-[var(--mlf-primary)]"
                      onMouseDown={(e) => e.stopPropagation()}
                      onClick={(e) => { e.stopPropagation(); setTenOpen(v => !v) }}
                    >
                      <CircleHelp size={16} />
                    </button>
                  </label>

                  <input
                    className={inputCls}
                    placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                    value={form.tenant_guid || ''}
                    onChange={e => setForm({ ...form, tenant_guid: e.target.value })}
                  />

                  {/* Tenant resolver */}
                  <Overlay
                    target={tenBtnRef.current}
                    show={tenOpen}
                    placement="right"
                    container={modalBodyRef.current}
                    rootClose
                    rootCloseEvent="mousedown"
                    onHide={() => setTenOpen(false)}
                    containerPadding={8}
                  >
                    {(p) => (
                      <div
                        ref={p.ref}
                        style={p.style}
                        {...p}
                        className="tenant-popover"
                        onMouseDown={(e) => e.stopPropagation()}
                      >
                        <div className="tenant-popover-arrow" />
                        <div className="text-sm font-medium mb-2">Resolve Tenant GUID</div>

                        <input
                          className={inputCls}
                          placeholder="contoso.com"
                          value={tenantDomain}
                          onChange={(e) => setTenantDomain(e.target.value)}
                          autoFocus
                        />

                        <div className="mt-2 flex gap-2 justify-end">
                          <Button size="sm" variant="secondary" onClick={() => setTenOpen(false)}>
                            Cancel
                          </Button>
                          <Button
                            size="sm"
                            variant="primary"
                            disabled={!tenantDomain.trim() || tenantResolving}
                            onClick={async () => {
                              try {
                                setTenantResolving(true)
                                const r = await api.get(`/api/config/tenant_guid`, { params: { domain: tenantDomain } })
                                setForm(f => ({ ...f, tenant_guid: r.data.tenant_guid }))
                                copyToClipboard(r.data.tenant_guid)
                                toast.success('Tenant GUID resolved and copied')
                                setTenOpen(false)
                                setTenantDomain('')
                              } catch (e) {
                                toast.error(e?.response?.data?.detail || 'Failed to resolve')
                              }
                              finally {
                                setTenantResolving(false)
                              }
                            }}
                          >
                            {tenantResolving ? 'Resolving…' : 'Resolve'}
                          </Button>
                        </div>
                      </div>
                    )}
                  </Overlay>
                </div>

                <div className="form-check check-accent">
                  <input
                    id="per-recipient"
                    type="checkbox"
                    className="form-check-input"
                    checked={!!form.per_recipient}
                    onChange={e => setForm({ ...form, per_recipient: e.target.checked })}
                  />
                  <label htmlFor="per-recipient" className="form-check-label">
                    Generate one meeting per recipient
                  </label>
                </div>
              </>
            )}

            <div className="form-text">
              Use in templates as <code>{`{{${form.name || 'var'}}}`}</code>.
            </div>
          </div>
        </Modal.Body>

        <Modal.Footer className="border-0 pt-0 px-4 pb-4">
          <Button variant="secondary" onClick={() => { setShow(false); setTenOpen(false) }}>Cancel</Button>
          <Button variant="primary" onClick={saveVar}>Save</Button>
        </Modal.Footer>
      </Modal>

      {/* Confirm delete modal */}
      <Modal show={showDel} onHide={() => setShowDel(false)} centered contentClassName="modal-matte">
        <Modal.Header closeButton className="border-0 pt-4 px-4">
          <Modal.Title>Delete Variable</Modal.Title>
        </Modal.Header>
        <Modal.Body className="px-4 pt-2 pb-4">
          <div className="text-sm">
            Are you sure you want to <span className="fw-semibold">delete</span> this variable?
            {rowToDel && (
              <div className="mt-3 p-3 rounded-xl bg-red-500/10 ring-1 ring-red-500/20">
                <div className="font-medium">{rowToDel.name}</div>
                <div className="text-xs opacity-80 mt-1">Type: {rowToDel.kind}</div>
              </div>
            )}
          </div>
        </Modal.Body>
        <Modal.Footer className="border-0 pt-0 px-4 pb-4">
          <Button variant="secondary" onClick={() => setShowDel(false)}>Cancel</Button>
          <Button variant="rose" onClick={confirmDeleteVar}>Delete</Button>
        </Modal.Footer>
      </Modal>
    </div>
  )
}