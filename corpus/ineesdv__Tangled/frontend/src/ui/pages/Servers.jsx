import React, { useEffect, useMemo, useState, forwardRef } from 'react'
import { client } from '../lib/api'
import DataTable, { createTheme } from 'react-data-table-component'
import { OverlayTrigger, Tooltip, Modal, Button, Dropdown, Form } from 'react-bootstrap'
import { toast } from 'react-toastify'
import { Plus, MoreVertical, Pencil, Trash2, Copy, Search, Shield, Server } from 'lucide-react'
import ThemedSelect from '../components/ThemedSelect'
import '../components/datatableThemes'
import { useTheme } from '../../hooks/useTheme'
import { inputModalCls, inputSearchbarCls } from '../utils/styles'

export default function Servers() {
  const api = client()

  // Theme selector
  const isDark = useTheme()

  // Data
  const [rows, setRows] = useState([])
  const [show, setShow] = useState(false)
  const [edit, setEdit] = useState(null)
  const [form, setForm] = useState({ name: '', host: '', port: 587, use_tls: true })

  const [showDup, setShowDup] = useState(false)
  const [dupRow, setDupRow] = useState(null)
  const [dupName, setDupName] = useState('')

  const [showDel, setShowDel] = useState(false)
  const [delRow, setDelRow] = useState(null)

  // Filters
  const [query, setQuery] = useState('')
  const [tlsFilter, setTlsFilter] = useState('all')

  const load = async () => {
    const { data } = await api.get('/api/servers')
    setRows(data)
  }
  useEffect(() => { load() }, [])

  const openCreate = () => {
    setEdit(null)
    setForm({ name: '', host: '', port: 587, use_tls: true })
    setShow(true)
  }

  const openEdit = (r) => {
    setEdit(r)
    setForm({ ...r })
    setShow(true)
  }

  const save = async () => {
    try {
      if (edit) await api.put(`/api/servers/${edit.id}`, form)
      else await api.post('/api/servers', form)
      toast.success('SMTP server saved')
      setShow(false)
      load()
      
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed to save SMTP server')
    }
  }

  const askDelete = (r) => {
    setDelRow(r)
    setShowDel(true)
  }

  const doDelete = async () => {
    if (!delRow) return
    try {
      await api.delete(`/api/servers/${delRow.id}`)
      toast.success('SMTP server deleted')
      setShowDel(false)
      setDelRow(null)
      load()

    } catch {
      toast.error('Failed to delete SMTP server')
    }
  }

  const openDup = (row) => {
    setDupRow(row);
    setDupName(row.name + ' (copy)')
    setShowDup(true)
  }

  const doDup = async () => {
    try {
      await api.post(`/api/servers/${dupRow.id}/duplicate`, { name: dupName })
      toast.success('Server duplicated')
      setShowDup(false)
      setDupRow(null)
      setDupName('')
      load()

    } catch (e) {
      const msg = e?.response?.data?.detail || 'Could not duplicate'
      toast.error(msg)
    }
  }

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return rows.filter((r) => {
      const matchesQ =
        !q ||
        r.name?.toLowerCase().includes(q) ||
        r.host?.toLowerCase().includes(q) ||
        String(r.port).includes(q)
      const matchesTls =
        tlsFilter === 'all' ? true : tlsFilter === 'tls' ? !!r.use_tls : !r.use_tls
      return matchesQ && matchesTls
    })
  }, [rows, query, tlsFilter])

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

  // Datatables definitions
  const columns = [
    {
      name: 'Name',
      sortable: true,
      grow: 1,
      cell: (r) => (
        <div className="flex items-center gap-2 min-w-0">
          <Server size={16} className="opacity-70 flex-shrink-0" />
          <span title={r.name} className="truncate">{r.name}</span>
        </div>
      )
    },
    {
      name: 'Host',
      selector: r => r.host,
      sortable: true,
      grow: 1,
      cell: (r) => (
        <div className="min-w-0 w-full">
          <span title={r.host} className="truncate block">{r.host}</span>
        </div>
      )
    },
    {
      name: 'Port',
      selector: r => r.port,
      sortable: true,
      grow: 0,
      minWidth: '100px',
      right: true
    },
    {
      name: 'TLS',
      grow: 0,
      minWidth: '100px',
      sortable: true,
      selector: r => (r.use_tls ? 'Yes' : 'No'),
      cell: r => (
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs
          ${r.use_tls
            ? 'bg-emerald-500/10 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300'
            : 'bg-slate-500/10 text-slate-700 dark:bg-slate-500/15 dark:text-slate-300'
          }`}>
          <Shield size={14} /> {r.use_tls ? 'TLS' : 'No'}
        </span>
      ),
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
              <Dropdown.Item onClick={() => openDup(r)}>
                <Copy size={14} className="me-2" /> Duplicate
              </Dropdown.Item>
              <Dropdown.Item onClick={() => askDelete(r)}>
                <Trash2 size={14} className="me-2" /> Delete
              </Dropdown.Item>
            </Dropdown.Menu>
          </Dropdown>
        </div>
      ),
    },
  ]

  const tableStyles = useMemo(() => {
    const headBg = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.035)'
    return {
      table: { style: { backgroundColor: 'transparent' } },
      header: { style: { minHeight: '52px', backgroundColor: 'transparent' } },
      headRow: { style: { backgroundColor: headBg, borderRadius: 12, minHeight: '72px' } },
      headCells: {
        style: {
          fontWeight: 700,
          fontSize: '12px',
          textTransform: 'uppercase',
          letterSpacing: '0.02em',
          paddingTop: '22px',
          paddingBottom: '22px',
          color: isDark ? '#cbd5e1' : '#1f2937',
        },
      },
      rows: {
        style: {
          minHeight: '60px',
          backgroundColor: 'transparent',
          color: isDark ? '#e5e7eb' : '#111827',
        },
        highlightOnHoverStyle: {
          backgroundColor: isDark ? 'rgba(109,113,236,0.18)' : 'rgba(109,113,236,0.10)',
          transitionDuration: '0.15s',
          borderBottomColor: 'transparent',
          outline: 'none',
        },
        stripedStyle: {
          backgroundColor: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)',
        },
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
      <h1 className="text-xl font-semibold text-slate-900 dark:text-white">Sending Servers</h1>
      <div className="rounded-2xl ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-glass/80 shadow-card p-2">
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex flex-1 items-center gap-2 min-w-[280px]">
            <div className="relative flex-1">
              <Search
                size={16}
                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 opacity-70"
              />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search by name, host, or port"
                className={inputSearchbarCls}
                style={{ paddingLeft: '2.75rem' }}
              />
            </div>
            <div className="w-[200px]">
              <ThemedSelect
                options={[
                  { value: 'all', label: 'All TLS states' },
                  { value: 'tls', label: 'TLS only' },
                  { value: 'notls', label: 'No TLS' },
                ]}
                value={tlsFilter}
                onChange={(v) => setTlsFilter(v)}
                searchable={false}
                placeholder="TLS"
              />
            </div>
          </div>
          <OverlayTrigger placement="top" overlay={<Tooltip>Create new server</Tooltip>}>
            <button
              onClick={openCreate}
              className="rail-btn ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-white/5 hover:bg-white/90 dark:hover:bg-white/10 text-[var(--mlf-primary)]"
              aria-label="Create server"
            >
              <Plus size={18} />
            </button>
          </OverlayTrigger>
        </div>
      </div>

      <div className="rounded-2xl ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-glass/80 shadow-card p-2">
        <DataTable
          columns={columns}
          data={filtered}
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
          noDataComponent={<div className="p-4 text-sm text-slate-600 dark:text-slate-300">No servers found.</div>}
        />
      </div>

      <Modal show={show} onHide={() => setShow(false)} centered contentClassName="modal-matte">
        <Modal.Header closeButton className="border-0 pt-4 px-4">
          <Modal.Title>{edit ? 'Edit Server' : 'Create Server'}</Modal.Title>
        </Modal.Header>
        <Modal.Body className="px-4 pt-2 pb-4">
          <div className="vstack gap-3">
            <input className={inputModalCls} placeholder="Name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
            <input className={inputModalCls} placeholder="Host (used as EHLO)" value={form.host} onChange={e => setForm({ ...form, host: e.target.value })} />
            <input className={inputModalCls} type="number" placeholder="Port" value={form.port} onChange={e => setForm({ ...form, port: +e.target.value })} />
            <Form.Check
              type="checkbox"
              className="check-accent m-0"
              label="Use TLS"
              checked={form.use_tls}
              onChange={(e) => setForm({ ...form, use_tls: e.target.checked })}
            />
          </div>
        </Modal.Body>
        <Modal.Footer className="border-0 pt-0 px-4 pb-4">
          <Button variant="secondary" onClick={() => setShow(false)}>Cancel</Button>
          <Button variant="primary" onClick={save} disabled={!form.name.trim()}>Save</Button>
        </Modal.Footer>
      </Modal>

      <Modal show={showDup} onHide={() => setShowDup(false)} centered contentClassName="modal-matte">
        <Modal.Header closeButton className="border-0 pt-4 px-4"><Modal.Title>Duplicate Server</Modal.Title></Modal.Header>
        <Modal.Body className="px-4 pt-2 pb-4">
          <input className={inputModalCls} placeholder="New server name" value={dupName} onChange={e => setDupName(e.target.value)} />
        </Modal.Body>
        <Modal.Footer className="border-0 pt-0 px-4 pb-4">
          <Button variant="secondary" onClick={() => setShowDup(false)}>Cancel</Button>
          <Button variant="primary" onClick={doDup} disabled={!dupName.trim()}>Create Copy</Button>
        </Modal.Footer>
      </Modal>

      <Modal show={showDel} onHide={() => setShowDel(false)} centered contentClassName="modal-matte">
        <Modal.Header closeButton className="border-0 pt-4 px-4"><Modal.Title>Delete Server</Modal.Title></Modal.Header>
        <Modal.Body className="px-4 pt-2 pb-4">
          <div className="text-sm">
            Are you sure you want to <span className="fw-semibold">delete</span> this server?
            {delRow && (
              <div className="mt-3 p-3 rounded-xl bg-red-500/10 ring-1 ring-red-500/20">
                <div className="font-medium truncate" title={delRow.name}>{delRow.name}</div>
                <div className="text-xs opacity-80 mt-1 truncate" title={`${delRow.host}:${delRow.port} · ${delRow.use_tls ? 'TLS' : 'No TLS'}`}>
                  {delRow.host}:{delRow.port} · {delRow.use_tls ? 'TLS' : 'No TLS'}
                </div>
              </div>
            )}
          </div>
        </Modal.Body>
        <Modal.Footer className="border-0 pt-0 px-4 pb-4">
          <Button variant="secondary" onClick={() => setShowDel(false)}>Cancel</Button>
          <Button variant="rose" onClick={doDelete}>Delete</Button>
        </Modal.Footer>
      </Modal>
    </div>
  )
}