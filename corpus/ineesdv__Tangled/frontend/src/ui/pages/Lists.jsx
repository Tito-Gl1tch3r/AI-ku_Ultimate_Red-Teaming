import React, { useEffect, useMemo, useRef, useState, forwardRef } from 'react'
import { client } from '../lib/api'
import { toast } from 'react-toastify'
import Papa from 'papaparse'
import DataTable from 'react-data-table-component'
import { Button, Modal, Form, Dropdown, OverlayTrigger, Tooltip } from 'react-bootstrap'
import { useNavigate } from 'react-router-dom'
import {
  Plus, MoreVertical, Pencil, Trash2, Copy, Eye, Search, Upload, Users2, Mail, ExternalLink, User, FileText, X, Crosshair, FileQuestionMark
} from 'lucide-react'
import '../components/datatableThemes'
import { useTheme } from '../../hooks/useTheme'
import { inputCls, inputSearchCls, inputSearchbarCls } from '../utils/styles'

export default function Lists() {
  const api = client()
  const nav = useNavigate()

  // Theme selector
  const isDark = useTheme()

  // Data
  const [rows, setRows] = useState([])
  const [sel, setSel] = useState(null)
  const [detailsVisible, setDetailsVisible] = useState(false)

  // Filters
  const [q, setQ] = useState('')
  const [tQuery, setTQuery] = useState('')

  // Modals
  const [showListModal, setShowListModal] = useState(false)
  const [edit, setEdit] = useState(null)
  const [listName, setListName] = useState('')

  // Duplicate
  const [showDup, setShowDup] = useState(false)
  const [dupRow, setDupRow] = useState(null)
  const [dupName, setDupName] = useState('')

  // Confirm delete
  const [showDelList, setShowDelList] = useState(false)
  const [delListRow, setDelListRow] = useState(null)

  // Add target
  const [targetForm, setTargetForm] = useState({
    first_name: '', last_name: '', email: '', extra_field: ''
  })

  // User search modal
  const [showUserSearch, setShowUserSearch] = useState(false)
  const [userEmail, setUserEmail] = useState('')
  const [userLoading, setUserLoading] = useState(false)
  const [userCampaigns, setUserCampaigns] = useState([])
  const [userSearched, setUserSearched] = useState(false)
  const [userQuery, setUserQuery] = useState('')

  // Email in lists search modal
  const [showEmailSearch, setShowEmailSearch] = useState(false)
  const [searchEmail, setSearchEmail] = useState('')
  const [emailSearchLoading, setEmailSearchLoading] = useState(false)
  const [emailSearchResults, setEmailSearchResults] = useState([])
  const [emailSearched, setEmailSearched] = useState(false)
  const [emailQuery, setEmailQuery] = useState('')

  // CSV import file input
  const fileRef = useRef(null)

  const load = async () => {
    const { data } = await api.get('/api/lists')
    setRows(data)
    if (sel?.id) view(sel.id) // Refresh targets if a list is selected
  }
  useEffect(() => { load() }, [])

  const view = async (id) => {
    const [{ data: targets }, { data: all }] = await Promise.all([
      api.get(`/api/lists/${id}/targets`),
      api.get('/api/lists'),
    ])
    const list = all.find(l => l.id === id)
    setSel({ id, name: list?.name || `List #${id}`, targets })
    setIsClosing(false)
    setDetailsVisible(false)
    requestAnimationFrame(() => { setDetailsVisible(true) })
  }

  const [isClosing, setIsClosing] = useState(false)

  const closePanel = () => {
    if (!sel) return
    setIsClosing(true)
    setDetailsVisible(false)
    setTimeout(() => {
      setSel(null)
      setIsClosing(false)
    }, 220)
  }

  const openCreate = () => {
    setEdit(null)
    setListName('')
    setShowListModal(true)
  }

  const openRename = (r) => {
    setEdit(r)
    setListName(r.name)
    setShowListModal(true)
  }

  const saveList = async () => {
    try {
      if (edit) await api.put(`/api/lists/${edit.id}`, { name: listName })
      else await api.post('/api/lists', { name: listName })
      toast.success('List saved')
      setShowListModal(false)
      await load()

    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed to save list')
    }
  }

  const askDelList = (row) => { setDelListRow(row); setShowDelList(true) }

  const doDelList = async () => {
    if (!delListRow) return
    try {
      await api.delete(`/api/lists/${delListRow.id}`)
      toast.success('List deleted')
      if (sel?.id === delListRow.id) setSel(null)
      setShowDelList(false); setDelListRow(null)
      await load()
    } catch (e) {
      const status = e?.response?.status
      const msg = e?.response?.data?.detail
      if (status === 409) toast.error(msg || 'Targets are being used by an active campaign.')
      else if (status === 404) toast.error('List not found')
      else toast.error('Error while deleting the target list')
    }
  }

  const openDup = (row) => {
    setDupRow(row)
    setDupName(row.name + ' (copy)')
    setShowDup(true)
  }

  const doDup = async () => {
    try {
      await api.post(`/api/lists/${dupRow.id}/duplicate`, { name: dupName })
      toast.success('List duplicated')
      setShowDup(false)
      setDupRow(null)
      setDupName('')
      await load()

    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Could not duplicate list')
    }
  }

  const addTarget = async (e) => {
    e.preventDefault()
    if (!sel?.id) return
    try {
      await api.post(`/api/lists/${sel.id}/targets`, [targetForm])
      toast.success('Target added')
      setTargetForm({ first_name: '', last_name: '', email: '', extra_field: '' })
      view(sel.id)
      
    } catch (e) {
      const status = e?.response?.status
      const detail = e?.response?.data?.detail
      if (status === 422) {
        let msg = 'Invalid input'
        if (Array.isArray(detail) && detail.length) {
          const first = detail[0]
          const loc = Array.isArray(first.loc) ? first.loc : []
          const field = [...loc].reverse().find(v => typeof v === 'string') || ''
          msg = String(field).toLowerCase().includes('email') ? 'Please enter a valid email address' : (first.msg || msg)
        } else if (typeof detail === 'string') {
          msg = detail
        }
        toast.error(msg)
        return
      }
      toast.error('Error while adding target')
    }
  }

  const deleteTarget = async (tid) => {
    try {
      await api.delete(`/api/targets/${tid}`)
      toast.success('Target deleted')
      view(sel.id)
    } catch (e) {
      const status = e?.response?.status
      const msg = e?.response?.data?.detail
      if (status === 409) toast.error(msg || 'Target is being used by an active campaign.')
      else if (status === 404) toast.error('Target not found')
      else toast.error('Error while deleting the target')
    }
  }

  const importCSV = async (e) => {
    const file = e.target.files?.[0]; if (!file || !sel?.id) return
    Papa.parse(file, {
      header: true, skipEmptyLines: true,
      complete: async (res) => {
        try {
          const payload = res.data
            .map(r => ({
              email: r.email || r.Email || r.EMAIL || '',
              first_name: r.first_name ?? r.firstname ?? r.first ?? r.FirstName ?? r.First ?? '',
              last_name: r.last_name ?? r.lastname ?? r.last ?? r.LastName ?? r.Last ?? '',
              extra_field: r.extra_field ?? r.ExtraField ?? r.extra ?? r.Extra ?? ''
            }))
            .filter(r => r.email)
          await api.post(`/api/lists/${sel.id}/targets`, payload)
          toast.success(`Imported ${payload.length} contacts`)
          view(sel.id)
        } catch {
          toast.error('Failed to import contacts')
        } finally {
          if (fileRef.current) fileRef.current.value = ''
        }
      }
    })
  }

  // User search
  const fetchUserCampaigns = async () => {
    const e = (userEmail || '').trim()
    if (!e) { toast.error('Please enter an email.'); return }
    setUserLoading(true)
    try {
      const { data } = await api.get('/api/user_campaigns', { params: { email: e } })
      setUserCampaigns(Array.isArray(data) ? data : [])
      setUserSearched(true)
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Error fetching campaigns for that email')
    } finally { setUserLoading(false) }
  }

  // Datatables definitions (lists)
  const ActionToggle = forwardRef(({ onClick }, ref) => (
    <button
      ref={ref}
      onClick={(e) => { e.preventDefault(); e.stopPropagation(); onClick(e) }}
      className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-transparent hover:bg-black/5 dark:hover:bg-white/10"
      aria-label="Row actions"
    >
      <MoreVertical size={16} />
    </button>
  ))

const listColumns = [
  {
    name: 'Name',
    sortable: true,
    grow: 2,
    cell: (r) => (
      <div className="flex items-center gap-2 min-w-0">
        <Users2 size={16} className="opacity-70 flex-shrink-0" />
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); view(r.id); }}
          className="truncate text-left hover:opacity-90 focus:outline-none"
          style={{ background: 'none', border: 0, padding: 0, margin: 0, color: 'inherit', textDecoration: 'none', cursor: 'pointer' }}
          aria-label={`Open ${r.name}`}
          title={r.name}
        >
          {r.name}
        </button>
      </div>
    ),
  },
  {
    name: '',
    width: '56px',
    cell: (r) => (
      <div className="position-relative z-20">
        <Dropdown align="end">
          <Dropdown.Toggle as={ActionToggle} />
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
            <Dropdown.Item onClick={() => view(r.id)}>
              <Eye size={14} className="me-2" /> Open
            </Dropdown.Item>
            <Dropdown.Item onClick={() => openRename(r)}>
              <Pencil size={14} className="me-2" /> Rename
            </Dropdown.Item>
            <Dropdown.Item onClick={() => openDup(r)}>
              <Copy size={14} className="me-2" /> Duplicate
            </Dropdown.Item>
            <Dropdown.Item onClick={() => askDelList(r)}>
              <Trash2 size={14} className="me-2" /> Delete
            </Dropdown.Item>
          </Dropdown.Menu>
        </Dropdown>
      </div>
    ),
    ignoreRowClick: true,
    button: true,
  },
]

  const filteredLists = useMemo(() => {
    const s = q.trim().toLowerCase()
    if (!s) return rows
    return rows.filter(r => r.name?.toLowerCase().includes(s))
  }, [rows, q])

  // Datatables definitions (targets)
  const targetColumns = [
    {
      name: 'Name',
      sortable: true,
      grow: 2,
      selector: r => `${r.first_name || ''} ${r.last_name || ''}`.trim(),
      cell: r => {
        const name = `${r.first_name || ''} ${r.last_name || ''}`.trim() || '—';
        return (
          <div className="min-w-0 w-full">
            <span className="truncate block" title={name}>{name}</span>
          </div>
        );
      }
    },
    {
      name: 'Email',
      sortable: true,
      grow: 3,
      selector: r => r.email || '',
      cell: r => {
        const email = r.email || '—';
        return (
          <div className="min-w-0 w-full">
            <span className="truncate block" title={email}>{email}</span>
          </div>
        );
      }
    },
    {
      name: 'Extra',
      sortable: true,
      grow: 3,
      selector: r => r.extra_field || '',
      cell: r => {
        const extra = r.extra_field || '—';
        return (
          <div className="min-w-0 w-full">
            <span className="truncate block" title={extra}>{extra}</span>
          </div>
        );
      }
    },
    {
      name: '',
      width: '56px',
      cell: r => (
        <OverlayTrigger placement="top" overlay={<Tooltip>Delete target</Tooltip>}>
          <button
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg hover:bg-black/5 dark:hover:bg-white/10"
            onClick={() => deleteTarget(r.id)}
            aria-label="Delete target"
          >
            <Trash2 size={15} />
          </button>
        </OverlayTrigger>
      ),
      ignoreRowClick: true,
      button: true,
    }
  ]

  const filteredTargets = useMemo(() => {
    if (!sel?.targets) return []
    const s = tQuery.trim().toLowerCase()
    if (!s) return sel.targets
    return sel.targets.filter(t =>
      (t.first_name || '').toLowerCase().includes(s) ||
      (t.last_name || '').toLowerCase().includes(s) ||
      (t.email || '').toLowerCase().includes(s) ||
      (t.extra_field || '').toLowerCase().includes(s)
    )
  }, [sel, tQuery])

  // Search email in lists
  const searchEmailInLists = async () => {
    const e = (searchEmail || '').trim()
    if (!e) { toast.error('Please enter an email.'); return }
    setEmailSearchLoading(true)
    try {
      const { data } = await api.get('/api/lists/search-by-email', { params: { email: e } })
      setEmailSearchResults(Array.isArray(data) ? data : [])
      setEmailSearched(true)
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Error searching for email in lists')
    } finally { setEmailSearchLoading(false) }
  }

  // Download csv
  const downloadExampleCSV = () => {
    const csvContent = `email,first_name,last_name,extra_field
john.smith@example.com,John,Smith,Marketing & Design
sarah.johnson@example.com,Sarah,Johnson,Senior Developer
michael.wong@example.com,Michael,Wong,HR Director`;

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);

    link.setAttribute('href', url);
    link.setAttribute('download', 'example_targets.csv');
    link.style.visibility = 'hidden';

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-slate-900 dark:text-white">Target Lists</h1>

      <div className={`grid gap-4 ${sel ? 'grid-cols-1 md:grid-cols-5' : 'grid-cols-1'}`}>
        {/* Lists */}
        <div className={`${sel ? 'md:col-span-2' : 'md:col-span-1'} space-y-3`}>
          <div className="rounded-2xl ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-glass/80 shadow-card p-2">
            <div className="flex flex-wrap items-center gap-2">
              <div className="relative flex-1 min-w-[280px]">
                <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 opacity-70" />
                <input
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  placeholder="Search lists…"
                  className={inputSearchCls}
                  style={{ paddingLeft: '2.75rem' }}
                />
              </div>
              <div className="ml-auto flex items-center gap-2">
                <OverlayTrigger placement="top" overlay={<Tooltip>Search email in lists</Tooltip>}>
                  <button
                    onClick={() => {
                      setSearchEmail(''); setEmailSearchResults([]); setEmailQuery(''); setEmailSearched(false); setShowEmailSearch(true)
                    }}
                    className="rail-btn ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-white/5 hover:bg-white/90 dark:hover:bg-white/10 text-[var(--mlf-primary)]"
                    aria-label="Search email in lists"
                  >
                    <Search size={18} />
                  </button>
                </OverlayTrigger>

                <OverlayTrigger placement="top" overlay={<Tooltip>User campaign search</Tooltip>}>
                  <button
                    onClick={() => {
                      setUserEmail(''); setUserCampaigns([]); setUserQuery(''); setUserSearched(false); setShowUserSearch(true)
                    }}
                    className="rail-btn ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-white/5 hover:bg-white/90 dark:hover:bg-white/10 text-[var(--mlf-primary)]"
                    aria-label="User campaign search"
                  >
                    <Crosshair size={18} />
                  </button>
                </OverlayTrigger>

                <OverlayTrigger placement="top" overlay={<Tooltip>Create list</Tooltip>}>
                  <button
                    onClick={openCreate}
                    className="rail-btn ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-white/5 hover:bg-white/90 dark:hover:bg-white/10 text-[var(--mlf-primary)]"
                    aria-label="Create list"
                  >
                    <Plus size={18} />
                  </button>
                </OverlayTrigger>
              </div>
            </div>
          </div>

          <div className="rounded-2xl ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-glass/80 shadow-card p-2">
            <DataTable
              columns={listColumns}
              data={filteredLists}
              theme={isDark ? 'datatablesDark' : 'datatablesLight'}
              customStyles={{
                table: { style: { backgroundColor: 'transparent' } },
                headRow: { style: { backgroundColor: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.035)', minHeight: '56px', borderRadius: 12 } },
                headCells: { style: { fontWeight: 700, fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.02em', color: isDark ? '#cbd5e1' : '#1f2937' } },
                rows: {
                  style: { minHeight: '54px', color: isDark ? '#e5e7eb' : '#111827' },
                  highlightOnHoverStyle: { backgroundColor: isDark ? 'rgba(109,113,236,0.18)' : 'rgba(109,113,236,0.10)' }
                }
              }}
              highlightOnHover
              pointerOnHover
              pagination
              onRowClicked={(row) => view(row.id)}
              noDataComponent={<div className="p-4 text-sm text-slate-600 dark:text-slate-300">No lists found.</div>}
            />
          </div>
        </div>

        {/* Targets */}
        {sel && (
          <div
            className="md:col-span-3 space-y-3"
            style={{
              transform: detailsVisible
                ? 'translateX(0)'
                : (isClosing ? 'translateX(-14px)' : 'translateX(14px)'),
              opacity: detailsVisible ? 1 : 0,
              transition: `transform 220ms ease, opacity 220ms ease`
            }}
          >
            <div className="rounded-2xl ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-glass/80 shadow-card">
              <div className="p-4 md:p-5 space-y-5">
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="text-sm text-slate-600 dark:text-slate-400">Selected list</div>
                    <div className="text-lg font-semibold text-slate-900 dark:text-white truncate">
                      {sel.name}
                    </div>
                    <div className="text-sm text-slate-600 dark:text-slate-400 mt-0.5">
                      {sel.targets?.length || 0} contacts
                    </div>
                  </div>

                 <OverlayTrigger placement="top" overlay={<Tooltip>Close panel</Tooltip>}>
                  <button
                    type="button"
                    onClick={closePanel}
                    className="inline-flex h-9 w-9 items-center justify-center rounded-lg hover:bg-black/5 dark:hover:bg-white/10 opacity-70 hover:opacity-100 transition"
                    aria-label="Close selected list"
                  >
                    <X size={16} />
                  </button>
                </OverlayTrigger>
                </div>

                <div className="flex flex-wrap items-start gap-3">
                  <div className="relative flex-[0_1_50%] min-w-[320px]">
                    <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 opacity-70" />
                    <input
                      value={tQuery}
                      onChange={(e) => setTQuery(e.target.value)}
                      placeholder="Filter targets…"
                      className={inputSearchCls}
                      disabled={!sel}
                    />
                  </div>

                  <div className="ms-auto">
                    <div className="flex items-center justify-end gap-2">
                      <input
                        ref={fileRef}
                        type="file"
                        className="hidden"
                        accept=".csv"
                        onChange={importCSV}
                      />

                      <OverlayTrigger placement="top" overlay={<Tooltip>Download example CSV template</Tooltip>}>
                        <button
                          type="button"
                          onClick={downloadExampleCSV}
                          className="rail-btn ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-white/5 hover:bg-white/90 dark:hover:bg-white/10 text-[var(--mlf-primary)]"
                          disabled={!sel}
                          aria-label="Download example CSV"
                        >
                          <FileQuestionMark size={16} />
                        </button>
                      </OverlayTrigger>

                      <OverlayTrigger placement="top" overlay={<Tooltip>CSV headers: email, first_name, last_name, extra_field</Tooltip>}>
                        <button
                          type="button"
                          onClick={() => fileRef.current?.click()}
                          className="inline-flex items-center gap-2 rounded-xl px-3 py-2 ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-white/5 hover:bg-white/90 dark:hover:bg-white/10 text-[var(--mlf-primary)]"
                          disabled={!sel}
                          aria-label="Import CSV"
                        >
                          <Upload size={16} /> Import
                        </button>
                      </OverlayTrigger>
                    </div>
                  </div>
                </div>

                <form onSubmit={addTarget} className="grid grid-cols-1 md:grid-cols-5 gap-2">
                  <div className="relative">
                    <User size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 opacity-70" />
                    <input
                      className={inputSearchbarCls}
                      placeholder="First name"
                      value={targetForm.first_name}
                      onChange={e => setTargetForm({ ...targetForm, first_name: e.target.value })}
                      disabled={!sel}
                    />
                  </div>
                  <div className="relative">
                    <User size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 opacity-70" />
                    <input
                      className={inputSearchbarCls}
                      placeholder="Last name"
                      value={targetForm.last_name}
                      onChange={e => setTargetForm({ ...targetForm, last_name: e.target.value })}
                      disabled={!sel}
                    />
                  </div>
                  <div className="relative">
                    <Mail size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 opacity-70" />
                    <input
                      className={inputSearchbarCls}
                      placeholder="Email"
                      value={targetForm.email}
                      onChange={e => setTargetForm({ ...targetForm, email: e.target.value })}
                      disabled={!sel}
                    />
                  </div>
                  <div className="relative">
                    <FileText size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 opacity-70" />
                    <input
                      className={inputSearchbarCls}
                      placeholder="Extra field"
                      value={targetForm.extra_field || ''}
                      onChange={e => setTargetForm({ ...targetForm, extra_field: e.target.value })}
                      disabled={!sel}
                    />
                  </div>
                  <OverlayTrigger placement="top" overlay={<Tooltip>Add target</Tooltip>}>
                    <div className="flex">
                      <button
                        type="submit"
                        className="h-9 px-3 rounded-lg bg-[var(--mlf-primary)] text-white hover:brightness-105 transition w-full"
                        disabled={!sel}
                      >
                        Add
                      </button>
                    </div>
                  </OverlayTrigger>
                </form>

                <div className="rounded-xl ring-1 ring-black/10 dark:ring-white/10 overflow-hidden">
                  <DataTable
                    columns={targetColumns}
                    data={filteredTargets}
                    theme={isDark ? 'datatablesDark' : 'datatablesLight'}
                    dense
                    striped
                    highlightOnHover
                    pagination
                    persistTableHead
                    noDataComponent={<div className="p-3 text-sm text-slate-600 dark:text-slate-300">No targets yet.</div>}
                  />
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Create/rename list */}
      <Modal show={showListModal} onHide={() => setShowListModal(false)} centered contentClassName="modal-matte">
        <Modal.Header closeButton className="border-0 pt-4 px-4">
          <Modal.Title>{edit ? 'Rename List' : 'Create List'}</Modal.Title>
        </Modal.Header>
        <Modal.Body className="px-4 pt-2 pb-4">
          <input className={inputCls} placeholder="List name" value={listName} onChange={e => setListName(e.target.value)} />
        </Modal.Body>
        <Modal.Footer className="border-0 pt-0 px-4 pb-4">
          <Button variant="secondary" onClick={() => setShowListModal(false)}>Cancel</Button>
          <Button variant="primary" onClick={saveList} disabled={!listName.trim()}>Save</Button>
        </Modal.Footer>
      </Modal>

      {/* Duplicate list */}
      <Modal show={showDup} onHide={() => setShowDup(false)} centered contentClassName="modal-matte">
        <Modal.Header closeButton className="border-0 pt-4 px-4">
          <Modal.Title>Duplicate List</Modal.Title>
        </Modal.Header>
        <Modal.Body className="px-4 pt-2 pb-4">
          <input className={inputCls} placeholder="New list name" value={dupName} onChange={e => setDupName(e.target.value)} />
        </Modal.Body>
        <Modal.Footer className="border-0 pt-0 px-4 pb-4">
          <Button variant="secondary" onClick={() => setShowDup(false)}>Cancel</Button>
          <Button variant="primary" onClick={doDup} disabled={!dupName.trim()}>Create Copy</Button>
        </Modal.Footer>
      </Modal>

      {/* Confirm delete list */}
      <Modal show={showDelList} onHide={() => setShowDelList(false)} centered contentClassName="modal-matte">
        <Modal.Header closeButton className="border-0 pt-4 px-4">
          <Modal.Title>Delete List</Modal.Title>
        </Modal.Header>
        <Modal.Body className="px-4 pt-2 pb-4">
          <div className="text-sm">
            Are you sure you want to <span className="fw-semibold">delete</span> this list?
            {delListRow && (
              <div className="mt-3 p-3 rounded-xl bg-red-500/10 ring-1 ring-red-500/20">
                <div className="font-medium truncate" title={delListRow.name}>{delListRow.name}</div>
                <div className="text-xs opacity-80 mt-1">All targets in the list will be removed.</div>
              </div>
            )}
          </div>
        </Modal.Body>
        <Modal.Footer className="border-0 pt-0 px-4 pb-4">
          <Button variant="secondary" onClick={() => setShowDelList(false)}>Cancel</Button>
          <Button variant="rose" onClick={doDelList}>Delete</Button>
        </Modal.Footer>
      </Modal>

      {/* User search modal */}
      <Modal show={showUserSearch} onHide={() => setShowUserSearch(false)} centered size="lg" contentClassName="modal-matte">
        <Modal.Header closeButton className="border-0 pt-4 px-4">
          <Modal.Title>User search</Modal.Title>
        </Modal.Header>
        <Modal.Body className="px-4 pt-2 pb-4">
          <Form onSubmit={(e) => { e.preventDefault(); fetchUserCampaigns() }}>
            <div className="mb-3 flex items-center gap-2">
              <div className="relative flex-1">
                <Mail size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 opacity-70" />
                <input
                  type="email"
                  className={inputSearchCls}
                  placeholder="name@example.com"
                  value={userEmail}
                  onChange={e => setUserEmail(e.target.value)}
                  required
                />
              </div>
              <OverlayTrigger placement="top" overlay={<Tooltip>Search</Tooltip>}>
                <button
                  type="submit"
                  className="inline-flex h-10 w-10 items-center justify-center rounded-lg hover:bg-black/5 dark:hover:bg-white/10"
                  aria-label="Search"
                  disabled={userLoading}
                >
                  <Search size={18} />
                </button>
              </OverlayTrigger>
            </div>
          </Form>

          {userSearched && userCampaigns.length === 0 && (
            <div className="text-sm text-slate-600 dark:text-slate-300">No campaigns found</div>
          )}

          {userCampaigns.length > 0 && (
            <>
              <div className="mt-2 mb-2 relative">
                <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 opacity-70" />
                <input
                  className={inputSearchCls}
                  placeholder="Filter results by campaign name…"
                  value={userQuery}
                  onChange={e => setUserQuery(e.target.value)}
                />
              </div>

              <div className="rounded-xl ring-1 ring-black/10 dark:ring-white/10 overflow-hidden">
                <DataTable
                  dense={false}
                  highlightOnHover
                  pagination
                  paginationPerPage={5}
                  paginationRowsPerPageOptions={[5]}
                  noHeader
                  theme={isDark ? 'datatablesDark' : 'datatablesLight'}
                  columns={[
                    { name: 'Campaign', selector: r => r.name, sortable: true, grow: 3 },
                    { name: 'Date', selector: r => new Date(r.date).toLocaleString(), sortable: true, grow: 2 },
                    {
                      name: '',
                      width: '56px',
                      cell: r => (
                        <OverlayTrigger placement="top" overlay={<Tooltip>Open in new tab</Tooltip>}>
                          <a
                            href={`/campaigns/${r.id}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="inline-flex h-9 w-9 items-center justify-center rounded-lg hover:bg-black/5 dark:hover:bg-white/10 text-inherit"
                            style={{ color: 'inherit', textDecoration: 'none' }}
                            aria-label="Open"
                          >
                            <ExternalLink size={16} />
                          </a>
                        </OverlayTrigger>
                      ),
                      ignoreRowClick: true,
                      button: true,
                    },
                  ]}
                  data={userCampaigns
                    .filter(c => !userQuery.trim() || c.name?.toLowerCase().includes(userQuery.trim().toLowerCase()))}
                />
              </div>
            </>
          )}
        </Modal.Body>
        <Modal.Footer className="border-0 pt-0 px-4 pb-4">
          <Button variant="secondary" onClick={() => setShowUserSearch(false)}>Close</Button>
        </Modal.Footer>
      </Modal>

      {/* Email in lists search modal */}
      <Modal show={showEmailSearch} onHide={() => setShowEmailSearch(false)} centered size="lg" contentClassName="modal-matte">
        <Modal.Header closeButton className="border-0 pt-4 px-4">
          <Modal.Title>Search email in lists</Modal.Title>
        </Modal.Header>
        <Modal.Body className="px-4 pt-2 pb-4">
          <Form onSubmit={(e) => { e.preventDefault(); searchEmailInLists() }}>
            <div className="mb-3 flex items-center gap-2">
              <div className="relative flex-1">
                <Mail size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 opacity-70" />
                <input
                  type="email"
                  className={inputSearchCls}
                  placeholder="name@example.com"
                  value={searchEmail}
                  onChange={e => setSearchEmail(e.target.value)}
                  required
                />
              </div>
              <OverlayTrigger placement="top" overlay={<Tooltip>Search</Tooltip>}>
                <button
                  type="submit"
                  className="inline-flex h-10 w-10 items-center justify-center rounded-lg hover:bg-black/5 dark:hover:bg-white/10"
                  aria-label="Search"
                  disabled={emailSearchLoading}
                >
                  <Search size={18} />
                </button>
              </OverlayTrigger>
            </div>
          </Form>

          {emailSearched && emailSearchResults.length === 0 && (
            <div className="text-sm text-slate-600 dark:text-slate-300">Email not found in any lists</div>
          )}

          {emailSearchResults.length > 0 && (
            <>
              <div className="mt-2 mb-2 relative">
                <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 opacity-70" />
                <input
                  className={inputSearchCls}
                  placeholder="Filter results by list name…"
                  value={emailQuery}
                  onChange={e => setEmailQuery(e.target.value)}
                />
              </div>

              <div className="rounded-xl ring-1 ring-black/10 dark:ring-white/10 overflow-hidden">
                <DataTable
                  dense={false}
                  highlightOnHover
                  pagination
                  paginationPerPage={5}
                  paginationRowsPerPageOptions={[5]}
                  noHeader
                  theme={isDark ? 'datatablesDark' : 'datatablesLight'}
                  columns={[
                    {
                      name: 'List Name',
                      selector: r => r.name,
                      sortable: true,
                      grow: 3,
                      cell: r => (
                        <div className="flex items-center gap-2">
                          <Users2 size={16} className="opacity-70" />
                          <span>{r.name}</span>
                        </div>
                      )
                    },
                    {
                      name: 'Matches',
                      selector: r => r.matching_targets,
                      sortable: true,
                      width: '100px',
                      center: true,
                      cell: r => (
                        <span className="text-sm opacity-70">{r.matching_targets}</span>
                      )
                    },
                    {
                      name: '',
                      width: '56px',
                      cell: r => (
                        <OverlayTrigger placement="top" overlay={<Tooltip>Open list</Tooltip>}>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              view(r.id);
                              setShowEmailSearch(false);
                            }}
                            className="inline-flex h-9 w-9 items-center justify-center rounded-lg hover:bg-black/5 dark:hover:bg-white/10 text-inherit"
                            aria-label="Open list"
                          >
                            <Eye size={16} />
                          </button>
                        </OverlayTrigger>
                      ),
                      ignoreRowClick: true,
                      button: true,
                    },
                  ]}
                  data={emailSearchResults
                    .filter(l => !emailQuery.trim() || l.name?.toLowerCase().includes(emailQuery.trim().toLowerCase()))}
                  onRowClicked={(row) => {
                    view(row.id);
                    setShowEmailSearch(false);
                  }}
                />
              </div>
            </>
          )}
        </Modal.Body>
        <Modal.Footer className="border-0 pt-0 px-4 pb-4">
          <Button variant="secondary" onClick={() => setShowEmailSearch(false)}>Close</Button>
        </Modal.Footer>
      </Modal>
    </div>
  )
}