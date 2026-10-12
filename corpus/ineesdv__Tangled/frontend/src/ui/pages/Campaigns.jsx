import React, { useEffect, useMemo, useRef, useState } from 'react'
import { client } from '../lib/api'
import { Button, Modal, OverlayTrigger, Tooltip } from 'react-bootstrap'
import { toast } from 'react-toastify'
import { useNavigate } from 'react-router-dom'
import ThemedSelect from '../components/ThemedSelect'
import {
  Plus, Archive, Trash2, Search as SearchIcon, Copy, Eye, X
} from 'lucide-react'
import { Link } from 'react-router-dom';
import StatusPill from '../components/StatusPill'
import { useTheme } from '../../hooks/useTheme'
import { inputCls, inputClsSearchbar, inputWithIconCls } from '../utils/styles'

function MultiListPicker({ all = [], value = [], onChange }) {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const ref = useRef(null)

  useEffect(() => {
    const onDoc = (e) => { if (!ref.current?.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  const selected = useMemo(() => all.filter(l => value.map(String).includes(String(l.id))), [all, value])
  const remaining = useMemo(() => {
    const s = q.trim().toLowerCase()
    return all
      .filter(l => !value.map(String).includes(String(l.id)))
      .filter(l => !s || (l.name || '').toLowerCase().includes(s))
  }, [all, value, q])

  return (
    <div ref={ref} className="relative">
      <div
        className="rounded-xl bg-white/70 dark:bg-white/5 px-2 py-2 ring-1 ring-black/10 dark:ring-white/10
             min-h-[96px] flex flex-wrap items-start gap-2"
        onClick={() => setOpen(true)}
        style={{ outline: 'none' }}
      >
        {selected.length === 0 && (
          <span className="text-sm text-slate-500 dark:text-slate-400 px-1">No lists selected</span>
        )}
        {selected.map(l => (
          <OverlayTrigger
            key={l.id}
            placement="top"
            overlay={
              <Tooltip>
                {typeof l.target_count === 'number' ? l.target_count : 0} target{(l.target_count || 0) === 1 ? '' : 's'}
              </Tooltip>
            }
          >
            <span
              className="inline-flex items-center gap-1.5 h-8 px-2 rounded-full text-xs font-medium
                        bg-white/90 dark:bg-white/10 text-slate-800 dark:text-slate-100
                        ring-1 ring-black/10 dark:ring-white/10 shadow-sm flex-none leading-none"
              title={l.name}
              role="button"
              tabIndex={0}
              onClick={(e) => { e.stopPropagation(); /* keep click from reopening dropdown */ }}
              onKeyDown={(e) => { if (e.key === 'Enter') { e.stopPropagation() } }}
            >
              <span className="truncate max-w-[260px]">
                {l.name}
              </span>
              <button
                type="button"
                className="ml-1.5 inline-flex items-center justify-center h-5 w-5 rounded-full
                          hover:bg-black/10 dark:hover:bg-white/10 focus:outline-none"
                onClick={(e) => { e.stopPropagation(); onChange(value.filter(id => String(id) !== String(l.id))) }}
                aria-label="Remove list"
              >
                <X size={14} />
              </button>
            </span>
          </OverlayTrigger>
        ))}
      </div>

      {open && (
        <div className="absolute z-50 mt-1 w-full menu-elevated rounded-xl overflow-hidden ring-1 ring-black/10 dark:ring-white/10 bg-white/95 dark:bg-[#0b1220]">
          <div className="p-2 border-b border-black/5 dark:border-white/10">
            <input
              className="w-full rounded-lg bg-white/80 dark:bg-white/10 px-3 py-2 text-sm
                         text-slate-900 dark:text-slate-100 ring-1 ring-black/10 dark:ring-white/10
                         placeholder:text-slate-500 dark:placeholder:text-slate-400
                         focus:outline-none focus:ring-2 focus:ring-primary/70"
              placeholder="Search lists…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              autoFocus
            />
          </div>
          <div className="max-h-56 overflow-auto py-1 scroll-area">
            {remaining.length === 0 && (
              <div className="px-3 py-2 text-sm text-slate-500 dark:text-slate-400">No lists</div>
            )}
            {remaining.map(l => (
              <button
                key={l.id}
                type="button"
                onClick={() => onChange([...value, l.id])}
                className="w-full text-left px-3 py-2 text-sm hover:bg-black/5 dark:hover:bg-white/10
                          flex items-center justify-between"
              >
                <span className="truncate">{l.name}</span>
                <span className="ml-2 inline-flex items-center px-1.5 h-5 rounded-md text-[10px]
                                  bg-black/5 dark:bg-white/10 text-slate-600 dark:text-slate-300">
                  {typeof l.target_count === 'number' ? l.target_count : 0}
                </span>
              </button>
            ))}

          </div>
        </div>
      )}
    </div>
  )
}

export default function Campaigns() {
  const api = client()
  const nav = useNavigate()

  // Theme selector
  const isDark = useTheme()
  
  // Data
  const [servers, setServers] = useState([])
  const [profiles, setProfiles] = useState([])
  const [templates, setTemplates] = useState([])
  const [lists, setLists] = useState([])
  const [campaigns, setCampaigns] = useState([])
  const [settings, setSettings] = useState({})
  const [show, setShow] = useState(false)

  const [form, setForm] = useState({
    name: '',
    server_id: '',
    profile_id: '',
    template_id: '',
    list_ids: [],
    use_batches: false,
    batch_size: 60,
    batch_delay_seconds: 60,
    custom_headers: [],
    schedule: false,
    scheduled_start_at: '',
    run_now: false,
    remove_duplicate_targets: true,
  });

  const [hdrKey, setHdrKey] = useState('')
  const [hdrVal, setHdrVal] = useState('')

  const [confirmArchiveAll, setConfirmArchiveAll] = useState(false)
  const [confirmDeleteAll, setConfirmDeleteAll] = useState(false)

  const load = async () => {
    const [srv, prof, tmpl, lst, cmp, cfg] = await Promise.all([
      api.get('/api/servers'),
      api.get('/api/profiles'),
      api.get('/api/templates'),
      api.get('/api/lists'),
      api.get('/api/campaigns'),
      api.get('/api/config/settings'),
    ])
    setServers(srv.data)
    setProfiles(prof.data)
    setTemplates(tmpl.data)
    setLists(lst.data)
    setCampaigns(cmp.data)

    const vals = (cfg.data && (cfg.data.values || cfg.data)) || {}
    setSettings(vals)
    setForm(f => ({
      ...f,
      batch_size: Number(vals.default_batch_size) || f.batch_size,
      batch_delay_seconds: Number(vals.default_batch_delay) || f.batch_delay_seconds,
    }))
  }
  useEffect(() => { load() }, [])

  // Refresh campaigns every 10s
  useEffect(() => {
    const tick = async () => {
      try {
        if (typeof document !== 'undefined' && document.hidden) return
        const { data } = await api.get('/api/campaigns')
        setCampaigns(data)
      } catch (e) {
      }
    }

    const id = setInterval(tick, 10000)
    return () => clearInterval(id)
  }, [api])


  const closeModal = () => {
    setShow(false)
    setHdrKey('')
    setHdrVal('')
  }

  const prettyErr = (e, fallback = 'Could not create the campaign') => {
    const d = e?.response?.data?.detail
    if (!d) return fallback
    if (typeof d === 'string') return d
    if (Array.isArray(d) && d.length && d[0]?.msg) return d[0].msg
    return fallback
  }

  const openCopy = async (id) => {
    try {
      const { data: d } = await api.get(`/api/campaigns/${id}`)
      const srv = servers.find(s => s.name === d.server)
      const prof = profiles.find(p => (p.name || p.profile_name) === d.profile)
      const tmpl = templates.find(t => t.name === d.template)
      const ch = d.custom_headers
        ? Object.entries(d.custom_headers).map(([k, v]) => ({ key: k, value: String(v) }))
        : []
      const selectedIds = Array.isArray(d.lists)
        ? d.lists.map(n => lists.find(l => l.name === n)?.id).filter(Boolean)
        : (lists.find(l => l.name === d.list_name)?.id ? [lists.find(l => l.name === d.list_name).id] : [])

      setForm({
        name: `${d.name} (copy)`,
        server_id: srv?.id || '',
        profile_id: prof?.id || '',
        template_id: tmpl?.id || '',
        list_ids: selectedIds,
        use_batches: !!d.use_batches,
        batch_size: d.batch_size ?? (Number(settings.default_batch_size) || ''),
        batch_delay_seconds: d.batch_delay_seconds ?? (Number(settings.default_batch_delay) || ''),
        custom_headers: ch,
        schedule: false,
        scheduled_start_at: '',
        run_now: false,
        remove_duplicate_targets: d.remove_duplicate_targets,
      })
      setShow(true)
    } catch (e) {
      toast.error(prettyErr(e, 'Could not load campaign to copy'))
    }
  }

  const create = async () => {
    try {
      if (!form.name || !form.name.trim()) {
        toast.error('Name cannot be empty'); return
      }
      if (!form.server_id || !form.profile_id || !form.template_id || !Array.isArray(form.list_ids) || form.list_ids.length === 0) {
        toast.error('Please fill all required fields'); return
      }

      const payload = {
        name: (form.name || '').trim(),
        server_id: Number(form.server_id),
        profile_id: Number(form.profile_id),
        template_id: Number(form.template_id),
        list_ids: form.list_ids.map(Number),
        custom_headers: Object.fromEntries((form.custom_headers || []).map(h => [h.key, h.value])),
        use_batches: !!form.use_batches,
        batch_size: form.use_batches ? Number(form.batch_size) : null,
        batch_delay_seconds: form.use_batches ? Number(form.batch_delay_seconds) : null,
        scheduled_start_at: form.schedule ? (form.scheduled_start_at || null) : null,
        run_now: !!form.run_now,
        remove_duplicate_targets: form.remove_duplicate_targets || false,
      }

      const res = await api.post('/api/campaigns', payload)
      if (payload.run_now && !payload.scheduled_start_at && res?.data?.id && res?.data?.status !== 'running') {
        try {
          await api.post(`/api/campaigns/${res.data.id}/start`)
        } catch { }
      }
      toast.success('Campaign created')
      setShow(false)
      setForm({
        name: '', server_id: '', profile_id: '', template_id: '', list_ids: [],
        use_batches: false, batch_size: 60, batch_delay_seconds: 60, custom_headers: [],
        schedule: false, scheduled_start_at: '', run_now: false
      })
      load()

    } catch (e) {
      toast.error(prettyErr(e))
    }
  }

  const active = useMemo(() =>
    campaigns.filter(c => c.status !== 'archived').sort((a, b) => new Date(b.created_at) - new Date(a.created_at)),
    [campaigns])

  const archived = useMemo(() =>
    campaigns.filter(c => c.status === 'archived').sort((a, b) => new Date(b.created_at) - new Date(a.created_at)),
    [campaigns])

  // Tabs & filters
  const [tab, setTab] = useState('active')
  const [searchActive, setSearchActive] = useState({ q: '', from: '', to: '', statuses: [] })
  const [searchArchived, setSearchArchived] = useState({ q: '', from: '', to: '', statuses: [] })
  const cur = tab === 'active' ? searchActive : searchArchived

  const CardItem = ({ c }) => (
    <div className="rounded-2xl ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-glass/80 shadow-card p-4 h-full flex flex-col">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="font-medium text-slate-900 dark:text-white truncate">{c.name}</div>
          <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            {new Date(c.created_at).toLocaleString()}
          </div>
        </div>
        <StatusPill status={c.status} />
      </div>

      <div className="mt-3 flex items-center gap-2">
        <OverlayTrigger placement="top" overlay={<Tooltip>Copy</Tooltip>}>
          <button className="rail-btn" onClick={() => openCopy(c.id)} aria-label="Copy">
            <Copy size={16} />
          </button>
        </OverlayTrigger>
        <OverlayTrigger placement="top" overlay={<Tooltip>Open</Tooltip>}>
          <Link
            to={`/campaigns/${c.id}`}
            className="rail-btn text-slate-700 dark:text-white"
            aria-label="Open"
            style={{
              textDecoration: 'none',
            }}
          >
            <Eye size={16} />
          </Link>
        </OverlayTrigger>
      </div>
    </div>
  )

  // Select options
  const serverOpts = servers.map(s => ({ value: s.id, label: s.name }))
  const profileOpts = profiles.map(p => ({ value: p.id, label: p.name || p.profile_name }))
  const templateOpts = templates.map(t => ({ value: t.id, label: t.name }))

  // Status filter options
  const ACTIVE_STATUSES = ['completed', 'running', 'stopped', 'scheduled', 'error']

  const statusMatches = (status, selected) => {
    if (!selected || selected.length === 0) return true
    return selected.includes(String(status || '').toLowerCase())
  }

  const match = (c, s) => {
    const q = (s.q || '').toLowerCase().trim()
    const nameOk = !q || (c.name || '').toLowerCase().includes(q)
    const date = c.created_at ? new Date(c.created_at) : null
    const fromOk = !s.from || (date && date >= new Date(s.from + 'T00:00'))
    const toOk = !s.to || (date && date <= new Date(s.to + 'T23:59'))
    const statusOk = statusMatches(c.status, s.statuses)
    return nameOk && fromOk && toOk && statusOk
  }

  const filteredActive = useMemo(() => active.filter(c => match(c, searchActive)), [active, searchActive])
  const filteredArchived = useMemo(() => archived.filter(c => match(c, searchArchived)), [archived, searchArchived])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-900 dark:text-white m-0">Campaigns</h1>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="rounded-2xl ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-glass/80 shadow-card p-2">
          <div className="inline-flex rounded-xl bg-white/80 dark:bg-white/5 ring-1 ring-black/10 dark:ring-white/10 p-1">
            <button
              onClick={() => { setTab('active'); setSearchActive({ q: '', from: '', to: '', statuses: [] }) }}
              className={['px-3 py-2 rounded-lg text-sm transition', tab === 'active'
                ? 'bg-primary/15 text-[var(--mlf-primary)] ring-1 ring-primary/25'
                : 'text-slate-700 dark:text-slate-200 hover:bg-black/5 dark:hover:bg-white/10'
              ].join(' ')}
            >
              Active
            </button>
            <button
              onClick={() => { setTab('archived'); setSearchArchived({ q: '', from: '', to: '', statuses: [] }) }}
              className={['px-3 py-2 rounded-lg text-sm transition', tab === 'archived'
                ? 'bg-primary/15 text-[var(--mlf-primary)] ring-1 ring-primary/25'
                : 'text-slate-700 dark:text-slate-200 hover:bg-black/5 dark:hover:bg-white/10'
              ].join(' ')}
            >
              Archived
            </button>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {tab === 'active' ? (
            <>
              <OverlayTrigger placement="top" overlay={<Tooltip>Archive all</Tooltip>}>
                <button className="rail-btn ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-white/5 hover:bg-white/90 dark:hover:bg-white/10 text-[var(--mlf-primary)]" onClick={() => setConfirmArchiveAll(true)} aria-label="Archive all">
                  <Archive size={18} />
                </button>
              </OverlayTrigger>
              <OverlayTrigger placement="top" overlay={<Tooltip>New campaign</Tooltip>}>
                <button className="rail-btn ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-white/5 hover:bg-white/90 dark:hover:bg-white/10 text-[var(--mlf-primary)]" onClick={() => setShow(true)} aria-label="New campaign">
                  <Plus size={18} />
                </button>
              </OverlayTrigger>
            </>
          ) : (
            <OverlayTrigger placement="top" overlay={<Tooltip>Delete all archived</Tooltip>}>
              <button className="rail-btn ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-white/5 hover:bg-white/90 dark:hover:bg-white/10 text-[var(--mlf-primary)]" onClick={() => setConfirmDeleteAll(true)} aria-label="Delete all archived">
                <Trash2 size={18} />
              </button>
            </OverlayTrigger>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="rounded-2xl ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-glass/80 shadow-card p-3">
        <div className="flex flex-wrap items-center gap-y-5 gap-x-8">
          <div className="relative flex-[1_1_320px] min-w-[280px]">
            <SearchIcon
              size={16}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 opacity-70"
            />
            <input
              value={cur.q}
              onChange={e => {
                const v = { ...cur, q: e.target.value };
                tab === 'active' ? setSearchActive(v) : setSearchArchived(v);
              }}
              placeholder={`Search ${tab === 'active' ? 'active' : 'archived'} campaigns`}
              className={inputClsSearchbar}
              style={{ paddingLeft: '2.75rem' }}
            />
          </div>

          <div className="flex items-center gap-4 md:gap-6 flex-wrap">
            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-600 dark:text-slate-300">From:</span>
              <div className="relative w-[150px]">
                <input
                  type="date"
                  className={inputWithIconCls}
                  value={cur.from}
                  onChange={e => {
                    const v = { ...cur, from: e.target.value };
                    tab === 'active' ? setSearchActive(v) : setSearchArchived(v);
                  }}
                  aria-label="From"
                  style={{ colorScheme: isDark ? 'dark' : 'light' }}
                />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-600 dark:text-slate-300">To:</span>
              <div className="relative w-[150px]">
                <input
                  type="date"
                  className={inputWithIconCls}
                  value={cur.to}
                  onChange={e => {
                    const v = { ...cur, to: e.target.value };
                    tab === 'active' ? setSearchActive(v) : setSearchArchived(v);
                  }}
                  aria-label="To"
                  style={{ colorScheme: isDark ? 'dark' : 'light' }}
                />
              </div>
            </div>
          </div>

          {tab === 'active' && (
            <div className="flex items-center gap-2 flex-wrap mt-1">
              {ACTIVE_STATUSES.map(s => {
                const on = (searchActive.statuses || []).includes(s);
                return (
                  <button
                    key={s}
                    type="button"
                    onClick={() => {
                      const set = new Set(searchActive.statuses || []);
                      on ? set.delete(s) : set.add(s);
                      setSearchActive({ ...searchActive, statuses: Array.from(set) });
                    }}
                    className={[
                      'px-2.5 py-1 rounded-lg text-xs font-semibold ring-1 transition',
                      on
                        ? 'bg-primary/15 text-[var(--mlf-primary)] ring-primary/25'
                        : 'bg-white/70 dark:bg-white/5 text-slate-700 dark:text-slate-200 ring-black/10 dark:ring-white/10 hover:bg-black/5 dark:hover:bg-white/10'
                    ].join(' ')}
                  >
                    {s}
                  </button>
                );
              })}
            </div>
          )}

          <div className="ml-auto">
            <OverlayTrigger placement="top" overlay={<Tooltip>Clear filters</Tooltip>}>
              <button
                className="rail-btn"
                onClick={() =>
                  tab === 'active'
                    ? setSearchActive({ q: '', from: '', to: '', statuses: [] })
                    : setSearchArchived({ q: '', from: '', to: '', statuses: [] })
                }
                aria-label="Clear filters"
              >
                <Trash2 size={16} />
              </button>
            </OverlayTrigger>
          </div>
        </div>
      </div>

      {/* Campaigns */}
      {(tab === 'active' ? filteredActive : filteredArchived).length === 0 ? (
        <div className="rounded-2xl ring-1 ring-black/10 dark:ring-0 bg-white/60 dark:bg-glass/60 shadow-card p-6 text-center text-slate-600 dark:text-slate-300">
          {tab === 'active' ? 'No campaigns yet.' : 'No archived campaigns.'}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {(tab === 'active' ? filteredActive : filteredArchived).map(c => (
            <CardItem key={c.id} c={c} />
          ))}
        </div>
      )}

      {/* Create/duplicate modal */}
      <Modal show={show} onHide={closeModal} centered contentClassName="modal-matte" dialogClassName="modal-wide">
        <Modal.Header closeButton className="border-0 pt-4 px-4">
          <Modal.Title>Create Campaign</Modal.Title>
        </Modal.Header>
        <Modal.Body className="px-4 pt-2 pb-4">
          <div className="space-y-4">
            <div>
              <div className="text-[13px] font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300 mb-2">
                Basics
              </div>
              <input
                className={inputCls}
                placeholder="Campaign name"
                value={form.name}
                onChange={e => setForm({ ...form, name: e.target.value })}
              />
            </div>

            <div>
              <div className="text-[13px] font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300 mb-2">
                Select resources
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <div className="text-sm mb-1">Server</div>
                  <ThemedSelect
                    options={serverOpts}
                    value={form.server_id}
                    onChange={(v) => setForm({ ...form, server_id: v })}
                    placeholder="Select server"
                  />
                </div>
                <div>
                  <div className="text-sm mb-1">Sender profile</div>
                  <ThemedSelect
                    options={profileOpts}
                    value={form.profile_id}
                    onChange={(v) => setForm({ ...form, profile_id: v })}
                    placeholder="Select profile"
                  />
                </div>
                <div>
                  <div className="text-sm mb-1">Template</div>
                  <ThemedSelect
                    options={templateOpts}
                    value={form.template_id}
                    onChange={(v) => setForm({ ...form, template_id: v })}
                    placeholder="Select template"
                  />
                </div>
                <div>
                  <div className="text-sm mb-1">Target lists</div>
                  <MultiListPicker
                    all={lists}
                    value={form.list_ids}
                    onChange={(ids) => setForm({ ...form, list_ids: ids })}
                  />
                  <div className="form-text mt-1">Pick one or more lists</div>
                </div>
              </div>
            </div>

            <div>
              <div className="text-[13px] font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300 mb-2">
                Delivery
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
                <div className="form-check check-accent">
                  <input
                    id="remove-duplicate-targets"
                    className="form-check-input"
                    type="checkbox"
                    checked={form.remove_duplicate_targets}
                    onChange={e =>
                      setForm({ ...form, remove_duplicate_targets: e.target.checked })
                    }
                  />
                  <label
                    htmlFor="remove-duplicate-targets"
                    className="form-check-label"
                  >
                    Remove duplicate targets
                  </label>
                </div>

                <div className="form-check check-accent">
                  <input
                    id="use-batches"
                    className="form-check-input"
                    type="checkbox"
                    checked={form.use_batches}
                    onChange={e => {
                      const use_batches = e.target.checked
                      setForm(f => ({
                        ...f,
                        use_batches,
                        batch_size: use_batches
                          ? Number(f.batch_size) || Number(settings.default_batch_size) || 60
                          : f.batch_size,
                        batch_delay_seconds: use_batches
                          ? Number(f.batch_delay_seconds) ||
                            Number(settings.default_batch_delay) ||
                            60
                          : f.batch_delay_seconds,
                      }))
                    }}
                  />
                  <label htmlFor="use-batches" className="form-check-label">
                    Use batches
                  </label>
                </div>
              </div>

              {form.use_batches && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 pb-3">
                  <div>
                    <div className="text-sm mb-1">Batch size</div>
                    <input
                      type="number"
                      className={`${inputCls} num`}
                      value={form.batch_size}
                      placeholder={String(settings.default_batch_size ?? '')}
                      onChange={e => setForm({ ...form, batch_size: Number(e.target.value) })}
                    />
                  </div>
                  <div>
                    <div className="text-sm mb-1">Batch delay (sec)</div>
                    <input
                      type="number"
                      className={`${inputCls} num`}
                      value={form.batch_delay_seconds}
                      placeholder={String(settings.default_batch_delay ?? '')}
                      onChange={e => setForm({ ...form, batch_delay_seconds: Number(e.target.value) })}
                    />
                  </div>
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
                <div className="form-check check-accent">
                  <input
                    id="run-now"
                    className="form-check-input"
                    type="checkbox"
                    checked={form.run_now}
                    onChange={e => setForm({ ...form, run_now: e.target.checked, schedule: e.target.checked ? false : form.schedule })}
                  />
                  <label htmlFor="run-now" className="form-check-label">Run campaign now</label>
                </div>
                <div className="form-check check-accent">
                  <input
                    id="schedule"
                    className="form-check-input"
                    type="checkbox"
                    checked={form.schedule}
                    onChange={e => setForm({ ...form, schedule: e.target.checked, run_now: e.target.checked ? false : form.run_now })}
                  />
                  <label htmlFor="schedule" className="form-check-label">Schedule start</label>
                </div>
              </div>

              {form.schedule && (
                <div className="pt-2 pb-3">
                  <div className="text-sm mb-1">Start at</div>
                  <input
                    type="datetime-local"
                    className={inputCls}
                    value={form.scheduled_start_at}
                    onChange={e => setForm({ ...form, scheduled_start_at: e.target.value })}
                    style={{ colorScheme: isDark ? 'dark' : 'light' }}
                  />
                </div>
              )}
            </div>

            <div>
              <div className="text-[13px] font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300 mb-2">
                Custom headers
              </div>
              <div className="grid grid-cols-1 md:grid-cols-[1fr_1fr_auto] gap-3 items-end">
                <div>
                  <div className="text-sm mb-1">Header</div>
                  <input
                    className={inputCls}
                    value={hdrKey}
                    onChange={e => setHdrKey(e.target.value)}
                    placeholder="e.g. X-Tracking-Id"
                  />
                </div>
                <div>
                  <div className="text-sm mb-1">Value</div>
                  <input
                    className={inputCls}
                    value={hdrVal}
                    onChange={e => setHdrVal(e.target.value)}
                    placeholder="e.g. abc123"
                  />
                </div>
                <div>
                  <OverlayTrigger placement="top" overlay={<Tooltip>Add header</Tooltip>}>
                    <button
                      type="button"
                      className="rail-btn bg-white/80 dark:bg-white/5 hover:bg-white/90 dark:hover:bg-white/10"
                      onClick={() => {
                        const k = (hdrKey || '').trim()
                        const v = (hdrVal || '').trim()
                        if (!k || !v) { toast.error('Both header and value are required'); return }
                        if ((form.custom_headers || []).some(h => (h.key || '').toLowerCase() === k.toLowerCase())) {
                          toast.error('Header already added'); return
                        }
                        setForm({ ...form, custom_headers: [...(form.custom_headers || []), { key: k, value: v }] })
                        setHdrKey(''); setHdrVal('')
                      }}
                      aria-label="Add header"
                    >
                      <Plus size={16} />
                    </button>
                  </OverlayTrigger>
                </div>
              </div>

              {Array.isArray(form.custom_headers) && form.custom_headers.length > 0 && (
                <div className="mt-2 space-y-2">
                  {form.custom_headers.map((h, idx) => (
                    <div key={`${h.key}-${idx}`} className="rounded-xl ring-1 ring-black/10 dark:ring-white/10 bg-white/60 dark:bg-white/5 px-3 py-1 d-flex align-items-center justify-between">
                      <div className="text-sm">
                        <span className="font-semibold text-slate-800 dark:text-slate-100">{h.key}</span>
                        <span className="text-slate-500 dark:text-slate-300">: {h.value}</span>
                      </div>
                      <OverlayTrigger placement="top" overlay={<Tooltip>Remove</Tooltip>}>
                        <button
                          type="button"
                          className="rail-btn hover:bg-black/5 dark:hover:bg-white/10"
                          onClick={() => {
                            const next = form.custom_headers.filter((_, i) => i !== idx)
                            setForm({ ...form, custom_headers: next })
                          }}
                          aria-label="Remove header"
                        >
                          <Trash2 size={16} />
                        </button>
                      </OverlayTrigger>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </Modal.Body>
        <Modal.Footer className="border-0 pt-0 px-4 pb-4">
          <Button variant="secondary" onClick={closeModal}>Cancel</Button>
          <Button variant="primary" onClick={create} disabled={!form.name?.trim()}>Create</Button>
        </Modal.Footer>
      </Modal>

      {/* Confirm archive all */}
      <Modal show={confirmArchiveAll} onHide={() => setConfirmArchiveAll(false)} centered contentClassName="modal-matte">
        <Modal.Header closeButton className="border-0 pt-4 px-4">
          <Modal.Title>Archive all campaigns?</Modal.Title>
        </Modal.Header>
        <Modal.Body className="px-4 pt-2 pb-4">
          This will archive all campaigns that are not currently running. Scheduled campaigns will also be archived.
        </Modal.Body>
        <Modal.Footer className="border-0 pt-0 px-4 pb-4">
          <Button variant="secondary" onClick={() => setConfirmArchiveAll(false)}>Cancel</Button>
          <Button
            variant="rose"
            onClick={async () => {
              try {
                const res = await api.post(`/api/campaigns/archive_all`)
                toast.info(`Archived ${res.data?.archived ?? 0} campaigns`)
                setConfirmArchiveAll(false)
                load && load()
              } catch (e) {
                toast.error(e.response?.data?.detail || 'Archive all failed')
              }
            }}
          >
            Yes, archive all
          </Button>
        </Modal.Footer>
      </Modal>

      {/* Confirm delete all archived */}
      <Modal show={confirmDeleteAll} onHide={() => setConfirmDeleteAll(false)} centered contentClassName="modal-matte">
        <Modal.Header closeButton className="border-0 pt-4 px-4">
          <Modal.Title>Delete all archived campaigns?</Modal.Title>
        </Modal.Header>
        <Modal.Body className="px-4 pt-2 pb-4">
          This will permanently delete all <strong>archived</strong> campaigns and their logs. This cannot be undone.
        </Modal.Body>
        <Modal.Footer className="border-0 pt-0 px-4 pb-4">
          <Button variant="secondary" onClick={() => setConfirmDeleteAll(false)}>Cancel</Button>
          <Button
            variant="rose"
            onClick={async () => {
              try {
                const res = await api.post('/api/campaigns/delete_all')
                toast.success(`Deleted ${res.data?.deleted ?? 0} archived campaigns`)
                setConfirmDeleteAll(false)
                load && load()
              } catch (e) {
                toast.error(e?.response?.data?.detail || 'Delete all failed')
              }
            }}
          >
            Yes, delete all
          </Button>
        </Modal.Footer>
      </Modal>

      <style>{`
        .num::-webkit-outer-spin-button, .num::-webkit-inner-spin-button { opacity: .5; }
        .num { -moz-appearance: textfield; }
        .modal-dialog.modal-wide { max-width: 900px; }
      `}</style>


    </div>
  )
}