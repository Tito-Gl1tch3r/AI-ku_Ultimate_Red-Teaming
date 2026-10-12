import React, { useEffect, useMemo, useState, forwardRef } from 'react'
import { client } from '../lib/api'
import DataTable, { createTheme } from 'react-data-table-component'
import { OverlayTrigger, Tooltip, Modal, Button, Dropdown, Form } from 'react-bootstrap'
import { toast } from 'react-toastify'
import { Plus, MoreVertical, Pencil, Trash2, Copy, Search, SquareUserRound } from 'lucide-react'
import '../components/datatableThemes'
import { useTheme } from '../../hooks/useTheme'
import { inputModalCls, inputSearchbarCls} from '../utils/styles'

export default function Profiles() {
  const api = client()

  // Theme selector
  const isDark = useTheme()

  // Data
  const [rows, setRows] = useState([])
  const [show, setShow] = useState(false)
  const [edit, setEdit] = useState(null)
  const [form, setForm] = useState({ profile_name: '', display_name: '', email: '', password: '' })

  const [showDup, setShowDup] = useState(false)
  const [dupRow, setDupRow] = useState(null)
  const [dupName, setDupName] = useState('')

  const [showDel, setShowDel] = useState(false)
  const [delRow, setDelRow] = useState(null)

  // Filters
  const [query, setQuery] = useState('')

  const load = async () => {
    const { data } = await api.get('/api/profiles')
    setRows(data)
  }

  useEffect(() => { load() }, [])

  const validEmail = (v) => /\S+@\S+\.\S+/.test(v || '')

  const prettyErr = (e) => {
    const d = e?.response?.data?.detail
    if (!d) return 'Failed to save profile'
    if (typeof d === 'string') return d
    if (Array.isArray(d) && d.length && d[0]?.msg) return d[0].msg
    return 'Failed to save profile'
  }

  const openCreate = () => {
    setEdit(null);
    setForm({ profile_name: '', display_name: '', email: '', password: '' });
    setShow(true)
  }

  const openEdit = (r) => {
    setEdit(r);
    setForm({ ...r, password: '' });
    setShow(true)
  }

  const save = async () => {
    try {
      if (edit) await api.put(`/api/profiles/${edit.id}`, form)
      else await api.post('/api/profiles', form)
      toast.success('Sender profile saved')
      setShow(false)
      load()

    } catch (e) {
      toast.error(prettyErr(e))
    }
  }

  const askDelete = (r) => {
    setDelRow(r);
    setShowDel(true)
  }

  const doDelete = async () => {
    if (!delRow) return
    try {
      await api.delete(`/api/profiles/${delRow.id}`)
      toast.success('Sender profile deleted')
      setShowDel(false)
      setDelRow(null)
      load()

    } catch {
      toast.error('Failed to delete sender profile')
    }
  }

  const openDup = (row) => {
    setDupRow(row)
    setDupName(row.profile_name + ' (copy)')
    setShowDup(true)
  }

  const doDup = async () => {
    try {
      await api.post(`/api/profiles/${dupRow.id}/duplicate`, { profile_name: dupName })
      toast.success('Profile duplicated')
      setShowDup(false)
      setDupRow(null)
      setDupName('')
      load()

    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Could not duplicate')
    }
  }

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return rows.filter(r =>
      !q ||
      r.profile_name?.toLowerCase().includes(q) ||
      r.display_name?.toLowerCase().includes(q) ||
      r.email?.toLowerCase().includes(q)
    )
  }, [rows, query])

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
      name: 'Profile',
      sortable: true,
      grow: 2,
      cell: (r) => (
        <div className="flex items-center gap-2 min-w-0">
          <SquareUserRound size={16} className="opacity-70 flex-shrink-0" />
          <span title={r.profile_name} className="truncate">{r.profile_name}</span>
        </div>
      )
    },
    {
      name: 'Display',
      selector: r => r.display_name,
      sortable: true,
      grow: 2,
      cell: (r) => (
        <div className="min-w-0 w-full">
          <span title={r.display_name} className="truncate block">{r.display_name}</span>
        </div>
      )
    },
    {
      name: 'Email',
      selector: r => r.email,
      sortable: true,
      grow: 3,
      cell: (r) => (
        <div className="min-w-0 w-full">
          <span title={r.email} className="truncate block">{r.email}</span>
        </div>
      )
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
      <h1 className="text-xl font-semibold text-slate-900 dark:text-white">Sender Profiles</h1>

      <div className="rounded-2xl ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-glass/80 shadow-card p-2">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative flex-1 min-w-[280px]">
            <Search
              size={16}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 opacity-70"
            />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by profile, display, or email"
              className={inputSearchbarCls}
            />
          </div>

          <div className="ml-auto">
            <OverlayTrigger placement="top" overlay={<Tooltip>Create new sending profile</Tooltip>}>
              <button
                onClick={openCreate}
                className="rail-btn ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-white/5 hover:bg-white/90 dark:hover:bg-white/10 text-[var(--mlf-primary)]"
                aria-label="Create profile"
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
          noDataComponent={<div className="p-4 text-sm text-slate-600 dark:text-slate-300">No profiles found.</div>}
        />
      </div>

      <Modal show={show} onHide={() => setShow(false)} centered contentClassName="modal-matte">
        <Modal.Header closeButton className="border-0 pt-4 px-4">
          <Modal.Title>{edit ? 'Edit Profile' : 'Create Profile'}</Modal.Title>
        </Modal.Header>
        <Modal.Body className="px-4 pt-2 pb-4">
          <div className="vstack gap-3">
            <input
              className={inputModalCls}
              placeholder="Profile Name"
              value={form.profile_name}
              onChange={e => setForm({ ...form, profile_name: e.target.value })}
            />
            <input
              className={inputModalCls}
              placeholder="Display Name"
              value={form.display_name}
              onChange={e => setForm({ ...form, display_name: e.target.value })}
            />
            <input
              className={inputModalCls}
              placeholder="Email"
              value={form.email}
              onChange={e => setForm({ ...form, email: e.target.value })}
            />
            <input
              className={inputModalCls}
              type="password"
              placeholder={edit ? 'SMTP Password (leave blank to keep current)' : 'SMTP Password'}
              value={form.password || ''}
              onChange={e => setForm({ ...form, password: e.target.value })}
            />
          </div>
        </Modal.Body>
        <Modal.Footer className="border-0 pt-0 px-4 pb-4">
          <Button variant="secondary" onClick={() => setShow(false)}>Cancel</Button>
          <Button variant="primary" onClick={save} disabled={!form.profile_name.trim() || !validEmail(form.email)}>Save</Button>
        </Modal.Footer>
      </Modal>

      <Modal show={showDup} onHide={() => setShowDup(false)} centered contentClassName="modal-matte">
        <Modal.Header closeButton className="border-0 pt-4 px-4"><Modal.Title>Duplicate Profile</Modal.Title></Modal.Header>
        <Modal.Body className="px-4 pt-2 pb-4">
          <input
            className={inputModalCls}
            placeholder="New profile name"
            value={dupName}
            onChange={e => setDupName(e.target.value)}
          />
        </Modal.Body>
        <Modal.Footer className="border-0 pt-0 px-4 pb-4">
          <Button variant="secondary" onClick={() => setShowDup(false)}>Cancel</Button>
          <Button variant="primary" onClick={doDup} disabled={!dupName.trim()}>Create Copy</Button>
        </Modal.Footer>
      </Modal>

      <Modal show={showDel} onHide={() => setShowDel(false)} centered contentClassName="modal-matte">
        <Modal.Header closeButton className="border-0 pt-4 px-4"><Modal.Title>Delete Profile</Modal.Title></Modal.Header>
        <Modal.Body className="px-4 pt-2 pb-4">
          <div className="text-sm">
            Are you sure you want to <span className="fw-semibold">delete</span> this profile?
            {delRow && (
              <div className="mt-3 p-3 rounded-xl bg-red-500/10 ring-1 ring-red-500/20">
                <div className="font-medium truncate" title={delRow.profile_name}>{delRow.profile_name}</div>
                <div className="text-xs opacity-80 mt-1 truncate" title={`${delRow.display_name} · ${delRow.email}`}>
                  {delRow.display_name} · {delRow.email}
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