import React, { useEffect, useState } from 'react'
import { client } from '../lib/api'
import { Button, Modal, OverlayTrigger, Tooltip } from 'react-bootstrap'
import { toast } from 'react-toastify'
import DataTable from 'react-data-table-component'
import { LogOut, MonitorSmartphone, Globe2, CalendarClock, Key, Copy, Trash2, Plus, HelpCircle, Shield, UserRoundX } from 'lucide-react'
import '../components/datatableThemes'
import { useTheme } from '../../hooks/useTheme'
import { copyToClipboard } from '../utils/common'
import { inputModalCls, inputCls2 } from '../utils/styles'

export default function Account() {
  const api = client()

  // Active tab
  const [activeTab, setActiveTab] = useState('password')

  // Theme selector
  const isDark = useTheme()

  // Change password
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [newPasswordConfirm, setNewPasswordConfirm] = useState('')
  const [busyPwd, setBusyPwd] = useState(false)

  // Sessions
  const [sessions, setSessions] = useState([])
  const [busyRows, setBusyRows] = useState({})
  const [busyRevokeAll, setBusyRevokeAll] = useState(false)
  const [showRevokeAllModal, setShowRevokeAllModal] = useState(false)

  // API Keys
  const [apiKeys, setApiKeys] = useState([])
  const [busyApiKeys, setBusyApiKeys] = useState({})
  const [showCreateKeyModal, setShowCreateKeyModal] = useState(false)
  const [newKeyName, setNewKeyName] = useState('')
  const [creatingKey, setCreatingKey] = useState(false)
  const [newlyCreatedKey, setNewlyCreatedKey] = useState(null)
  const [showDeleteKeyModal, setShowDeleteKeyModal] = useState(false)
  const [keyToDelete, setKeyToDelete] = useState(null)

  const loadSessions = async () => {
    try {
      const { data } = await api.get('/auth/sessions')
      setSessions(data)
    } catch {
      toast.error('Failed to load sessions')
    }
  }

  const loadApiKeys = async () => {
    try {
      const { data } = await api.get('/auth/api-keys')
      setApiKeys(data)
    } catch {
      toast.error('Failed to load API keys')
    }
  }

  useEffect(() => {
    loadSessions()
    loadApiKeys()
  }, [])

  const changePassword = async (e) => {
    e.preventDefault()
    if (!currentPassword || !newPassword) return toast.error('Fill both fields')
    if (newPassword.length < 8) return toast.error('New password must be at least 8 characters')
    if (newPassword !== newPasswordConfirm) return toast.error('Passwords do not match')
    try {
      setBusyPwd(true)
      await api.post('/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
        new_password_confirm: newPasswordConfirm,
      })
      setCurrentPassword('')
      setNewPassword('')
      setNewPasswordConfirm('')
      toast.success('Password changed')
    } catch (e) {
      const msg = e?.response?.data?.detail || 'Could not change password'
      toast.error(msg)
    } finally {
      setBusyPwd(false)
    }
  }

  const revoke = async (id, isCurrent) => {
    if (isCurrent) return
    try {
      setBusyRows(r => ({ ...r, [id]: true }))
      await api.post(`/auth/sessions/${id}/revoke`)
      toast.success('Session signed out')
      await loadSessions()
    } catch {
      toast.error('Failed to sign out session')
    } finally {
      setBusyRows(r => ({ ...r, [id]: false }))
    }
  }

  const revokeAllSessions = async () => {
    try {
      setBusyRevokeAll(true)
      const { data } = await api.post('/auth/sessions/revoke-all')
      toast.success(`Signed out ${data.revoked_count} session${data.revoked_count !== 1 ? 's' : ''}`)
      setShowRevokeAllModal(false)
      await loadSessions()
    } catch (e) {
      const msg = e?.response?.data?.detail || 'Failed to sign out sessions'
      toast.error(msg)
    } finally {
      setBusyRevokeAll(false)
    }
  }

  const handleCreateApiKey = async () => {
    if (!newKeyName.trim()) {
      toast.error('Please enter a key name')
      return
    }
    try {
      setCreatingKey(true)
      const { data } = await api.post('/auth/api-keys', { name: newKeyName.trim() })
      setNewlyCreatedKey({ key: data.key, name: data.name })
      setNewKeyName('')
      setShowCreateKeyModal(false)
      await loadApiKeys()
    } catch (e) {
      const msg = e?.response?.data?.detail || 'Failed to create API key'
      toast.error(msg)
    } finally {
      setCreatingKey(false)
    }
  }

  const askDeleteApiKey = (key) => {
    setKeyToDelete(key)
    setShowDeleteKeyModal(true)
  }

  const handleDeleteApiKey = async () => {
    if (!keyToDelete) return
    try {
      setBusyApiKeys(r => ({ ...r, [keyToDelete.id]: true }))
      await api.delete(`/auth/api-keys/${keyToDelete.id}`)
      toast.success('API key revoked')
      setShowDeleteKeyModal(false)
      setKeyToDelete(null)
      await loadApiKeys()
    } catch {
      toast.error('Failed to revoke API key')
    } finally {
      setBusyApiKeys(r => ({ ...r, [keyToDelete.id]: false }))
    }
  }

  // Datatables definitions
  const sessionColumns = [
    {
      name: 'Device',
      grow: 2,
      cell: (s) => {
        const ua = s.user_agent || 'Unknown'
        const displayUA = ua.length > 70 ? ua.substring(0, 70) + '...' : ua
        return (
          <div className="flex items-center gap-2">
            <MonitorSmartphone size={18} className="opacity-70 flex-shrink-0" />
            <OverlayTrigger
              placement="top"
              overlay={<Tooltip className="error-tooltip">{ua}</Tooltip>}
            >
              <span className="truncate" style={{ maxWidth: '100%' }}>
                {ua === 'Unknown' ? <span className="text-slate-500 dark:text-slate-300">Unknown</span> : displayUA}
              </span>
            </OverlayTrigger>
            {s.current && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs
                bg-emerald-500/10 text-emerald-700 ring-1 ring-emerald-500/20
                dark:bg-emerald-500/15 dark:text-emerald-300 dark:ring-emerald-500/25 flex-shrink-0 whitespace-nowrap">
                Current
              </span>
            )}
          </div>
        )
      }
    },
    {
      name: 'IP',
      width: '140px',
      cell: (s) => (
        <div className="flex items-center gap-2">
          <Globe2 size={14} className="opacity-70" />
          {s.ip_address || '—'}
        </div>
      )
    },
    {
      name: 'Created',
      width: '160px',
      selector: r => r.created_at,
      cell: (s) => new Date(s.created_at).toLocaleString()
    },
    {
      name: 'Last seen',
      width: '160px',
      selector: r => r.last_seen,
      cell: (s) => s.last_seen ? new Date(s.last_seen).toLocaleString() : '—'
    },
    {
      name: '',
      width: '56px',
      cell: (s) => (
        <OverlayTrigger placement="top" overlay={<Tooltip>Sign out this session</Tooltip>}>
          <span>
            <button
              className={[
                'inline-flex h-9 w-9 items-center justify-center rounded-lg',
                s.current || busyRows[s.id]
                  ? 'opacity-40 cursor-not-allowed'
                  : 'hover:bg-black/5 dark:hover:bg-white/10'
              ].join(' ')}
              onClick={() => revoke(s.id, s.current)}
              disabled={s.current || busyRows[s.id]}
              aria-label="Sign out session"
            >
              <LogOut size={16} />
            </button>
          </span>
        </OverlayTrigger>
      )
    }
  ]

  const apiKeyColumns = [
    {
      name: 'Name',
      grow: 2,
      cell: (k) => {
        const name = k.name || 'Unnamed'
        const displayName = name.length > 50 ? name.substring(0, 50) + '...' : name
        return (
          <div className="flex items-center gap-2">
            <Key size={16} className="opacity-70 flex-shrink-0" />
            <OverlayTrigger
              placement="top"
              overlay={<Tooltip>{name}</Tooltip>}
            >
              <span className="font-medium truncate" style={{ maxWidth: '100%' }}>
                {displayName}
              </span>
            </OverlayTrigger>
          </div>
        )
      }
    },
    {
      name: 'Key',
      width: '180px',
      cell: (k) => (
        <code className="text-xs px-2 py-1 rounded bg-slate-100 dark:bg-slate-800">
          {k.key_prefix}********
        </code>
      )
    },
    {
      name: 'Created',
      width: '160px',
      selector: r => r.created_at,
      cell: (k) => new Date(k.created_at).toLocaleString()
    },
    {
      name: 'Last used',
      width: '160px',
      selector: r => r.last_used_at,
      cell: (k) => k.last_used_at ? new Date(k.last_used_at).toLocaleString() :
        <span className="text-slate-500 dark:text-slate-400">Never</span>
    },
    {
      name: '',
      width: '56px',
      cell: (k) => (
        <OverlayTrigger placement="top" overlay={<Tooltip>Revoke this API key</Tooltip>}>
          <span>
            <button
              className={[
                'inline-flex h-9 w-9 items-center justify-center rounded-lg',
                busyApiKeys[k.id]
                  ? 'opacity-40 cursor-not-allowed'
                  : 'hover:bg-black/5 dark:hover:bg-white/10'
              ].join(' ')}
              onClick={() => askDeleteApiKey(k)}
              disabled={busyApiKeys[k.id]}
              aria-label="Revoke API key"
            >
              <Trash2 size={16} />
            </button>
          </span>
        </OverlayTrigger>
      )
    }
  ]

  const tableStyles = {
    table: { style: { backgroundColor: 'transparent' } },
    header: { style: { minHeight: '52px', backgroundColor: 'transparent' } },
    headRow: { style: { backgroundColor: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.035)', borderRadius: 12, minHeight: '60px' } },
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
    },
    pagination: {
      style: { backgroundColor: 'transparent', color: isDark ? '#e5e7eb' : '#0f172a' },
      pageButtonsStyle: {
        borderRadius: '10px', height: '32px', width: '32px', padding: 0, margin: '0 2px',
        color: isDark ? '#e5e7eb' : '#334155',
      },
    },
  }

  // Sidebar navigation
  const navItems = [
    { id: 'password', label: 'Password', icon: Shield },
    { id: 'api-keys', label: 'API Keys', icon: Key },
    { id: 'sessions', label: 'Active Sessions', icon: MonitorSmartphone },
  ]

  // Tooltip style for UA
  useEffect(() => {
    const styleEl = document.createElement('style')
    styleEl.textContent = `
      .error-tooltip .tooltip-inner {
        max-width: 500px !important;
        text-align: center;
      }
    `
    document.head.appendChild(styleEl)
    return () => document.head.removeChild(styleEl)
  }, [])

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-slate-900 dark:text-white">Account</h1>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Sidebar */}
        <div className="lg:col-span-3">
          <div className="rounded-2xl ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-glass/80 shadow-card p-3">
            <nav className="space-y-1">
              {navItems.map(item => {
                const Icon = item.icon
                const isActive = activeTab === item.id
                return (
                  <button
                    key={item.id}
                    onClick={() => setActiveTab(item.id)}
                    className={[
                      'w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-colors text-left',
                      isActive
                        ? 'bg-[var(--mlf-primary)]/10 text-[var(--mlf-primary)] dark:bg-[var(--mlf-primary)]/20'
                        : 'text-slate-700 dark:text-slate-300 hover:bg-black/5 dark:hover:bg-white/5'
                    ].join(' ')}
                  >
                    <Icon size={18} className="flex-shrink-0" />
                    {item.label}
                  </button>
                )
              })}
            </nav>
          </div>
        </div>

        <div className="lg:col-span-9">
          <div className={`rounded-2xl ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-glass/80 shadow-card ${activeTab === 'password' ? 'max-w-2xl' : ''}`}>
            {/* Password Tab */}
            {activeTab === 'password' && (
              <div className="p-8">
                <div className="mb-8">
                  <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-1">
                    Password
                  </h2>
                  <p className="text-sm text-slate-600 dark:text-slate-400">
                    Set a strong password to protect your account.
                  </p>
                </div>
                <form onSubmit={changePassword} className="space-y-5">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                      Current password
                    </label>
                    <input
                      type="password"
                      className={inputCls2}
                      placeholder="Enter current password"
                      value={currentPassword}
                      onChange={e => setCurrentPassword(e.target.value)}
                      autoComplete="current-password"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                      New password
                    </label>
                    <input
                      type="password"
                      className={inputCls2}
                      placeholder="Enter new password"
                      value={newPassword}
                      onChange={e => setNewPassword(e.target.value)}
                      autoComplete="new-password"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                      Confirm new password
                    </label>
                    <input
                      type="password"
                      className={inputCls2}
                      placeholder="Confirm new password"
                      value={newPasswordConfirm}
                      onChange={e => setNewPasswordConfirm(e.target.value)}
                      autoComplete="new-password"
                    />
                  </div>

                  <div className="flex justify-end pt-3">
                    <Button type="submit" variant="primary" disabled={busyPwd}>
                      {busyPwd ? 'Updating…' : 'Change password'}
                    </Button>
                  </div>
                </form>
              </div>
            )}

            {/* API Keys Tab */}
            {activeTab === 'api-keys' && (
              <div className="p-8">
                <div className="mb-6 flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-1">
                        API Keys
                      </h2>
                      <OverlayTrigger 
                          placement="right" 
                          overlay={
                            <Tooltip>
                              Use with the Authorization header
                            </Tooltip>
                          }
                        >
                          <button className="mb-3 inline-flex items-center justify-center opacity-60 hover:opacity-100 transition-opacity">
                            <HelpCircle size={16} />
                          </button>
                        </OverlayTrigger>
                    </div>
                    <p className="text-sm text-slate-600 dark:text-slate-400">
                      Manage API keys for programmatic access to your account.
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <OverlayTrigger placement="top" overlay={<Tooltip>Create new API key</Tooltip>}>
                      <button
                        onClick={() => setShowCreateKeyModal(true)}
                        className="rail-btn ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-white/5 hover:bg-white/90 dark:hover:bg-white/10 flex-shrink-0"
                        aria-label="Create API key"
                      >
                        <Plus size={18} />
                      </button>
                    </OverlayTrigger>
                  </div>
                </div>

                <DataTable
                  columns={apiKeyColumns}
                  data={apiKeys}
                  theme={isDark ? 'datatablesDark' : 'datatablesLight'}
                  customStyles={tableStyles}
                  highlightOnHover
                  responsive
                  pagination
                  paginationPerPage={10}
                  paginationRowsPerPageOptions={[10, 20, 50]}
                  persistTableHead
                  dense
                  noDataComponent={<div className="p-4 text-sm text-slate-600 dark:text-slate-300">No API keys created yet</div>}
                />
              </div>
            )}

            {/* Active Sessions Tab */}
            {activeTab === 'sessions' && (
              <div className="p-8">
                <div className="mb-6 flex items-start justify-between">
                  <div className="flex-1">
                    <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-1">
                      Active Sessions
                    </h2>
                    <p className="text-sm text-slate-600 dark:text-slate-400">
                      Manage your active login sessions across devices.
                    </p>
                    <div className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-2">
                      <CalendarClock size={14} />
                      {new Date().toLocaleString()}
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {sessions.length > 1 && (
                      <OverlayTrigger placement="top" overlay={<Tooltip>Sign out all other sessions</Tooltip>}>
                        <button
                          onClick={() => setShowRevokeAllModal(true)}
                          className="rail-btn ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-white/5 hover:bg-white/90 dark:hover:bg-white/10 flex-shrink-0"
                          aria-label="Sign out all other sessions"
                        >
                          <UserRoundX size={18} />
                        </button>
                      </OverlayTrigger>
                    )}
                  </div>
                </div>

                <DataTable
                  columns={sessionColumns}
                  data={sessions}
                  theme={isDark ? 'datatablesDark' : 'datatablesLight'}
                  customStyles={tableStyles}
                  highlightOnHover
                  responsive
                  pagination
                  paginationPerPage={10}
                  paginationRowsPerPageOptions={[10, 20, 50]}
                  persistTableHead
                  dense
                  noDataComponent={<div className="p-4 text-sm text-slate-600 dark:text-slate-300">No active sessions</div>}
                />
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Create API key modal */}
      <Modal show={showCreateKeyModal} onHide={() => !creatingKey && setShowCreateKeyModal(false)} centered contentClassName="modal-matte">
        <Modal.Header closeButton className="border-0 pt-4 px-4">
          <Modal.Title>Create API Key</Modal.Title>
        </Modal.Header>
        <Modal.Body className="px-4 pt-2 pb-4">
          <input
            type="text"
            className={inputModalCls}
            placeholder="Description"
            value={newKeyName}
            onChange={e => setNewKeyName(e.target.value)}
            disabled={creatingKey}
            autoFocus
          />
          <div className="text-xs text-slate-600 dark:text-slate-400 mt-2">
            Give your API key a descriptive name to help you remember what it's used for.
          </div>
        </Modal.Body>
        <Modal.Footer className="border-0 pt-0 px-4 pb-4">
          <Button variant="secondary" onClick={() => setShowCreateKeyModal(false)} disabled={creatingKey}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleCreateApiKey} disabled={creatingKey || !newKeyName.trim()}>
            {creatingKey ? 'Creating…' : 'Create Key'}
          </Button>
        </Modal.Footer>
      </Modal>

      {/* New key modal */}
      <Modal show={!!newlyCreatedKey} onHide={() => setNewlyCreatedKey(null)} centered backdrop="static" keyboard={false} contentClassName="modal-matte">
        <Modal.Header className="border-0 pt-4 px-4">
          <Modal.Title>API Key Created</Modal.Title>
        </Modal.Header>
        <Modal.Body className="px-4 pt-2 pb-4">
          <div className="p-3 rounded-xl ring-1 ring-rose-500/25 bg-rose-50/90 dark:bg-rose-500/10 mb-3 text-sm">
            <strong>Important:</strong> This is the only time you'll see this key.
            Make sure to copy it now and store it securely.
          </div>

          <div className="mb-2">
            <div className="text-sm font-semibold mb-1 text-slate-700 dark:text-slate-200">
              {newlyCreatedKey?.name}
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={newlyCreatedKey?.key || ''}
                readOnly
                className={`${inputModalCls} font-mono text-xs flex-1`}
              />
              <Button
                variant="outline-secondary"
                onClick={() => copyToClipboard(newlyCreatedKey?.key)}
                className="flex-shrink-0"
              >
                <Copy size={16} />
              </Button>
            </div>
          </div>

          <div className="mt-3 text-xs text-slate-600 dark:text-slate-400">
            <div className="font-semibold mb-1">Usage example:</div>
            <pre className="bg-slate-100 dark:bg-slate-800 p-2 rounded text-[11px] overflow-x-auto">
              {`curl -X POST '${window.location.origin}/api/campaigns/45/opened' \\
  -H 'Content-Type: application/json' \\
  -H 'Authorization: ApiKey ${newlyCreatedKey?.key || 'your-api-key-here'}' \\
  --data-raw '{
    "var_name": "randomID",
    "var_value": "JGenwyyo",
    "opened": true
  }'`}
            </pre>
          </div>
        </Modal.Body>
        <Modal.Footer className="border-0 pt-0 px-4 pb-4">
          <Button variant="primary" onClick={() => setNewlyCreatedKey(null)}>
            Close
          </Button>
        </Modal.Footer>
      </Modal>

      {/* Delete API key confirmation modal */}
      <Modal show={showDeleteKeyModal} onHide={() => setShowDeleteKeyModal(false)} centered contentClassName="modal-matte">
        <Modal.Header closeButton className="border-0 pt-4 px-4">
          <Modal.Title>Revoke API Key</Modal.Title>
        </Modal.Header>
        <Modal.Body className="px-4 pt-2 pb-4">
          <div className="text-sm">
            Are you sure you want to <span className="font-semibold">revoke</span> this API key?
            {keyToDelete && (
              <div className="mt-3 p-3 rounded-xl bg-red-500/10 ring-1 ring-red-500/20">
                <div className="font-medium truncate" title={keyToDelete.name}>
                  {keyToDelete.name.length > 50 ? keyToDelete.name.substring(0, 50) + '...' : keyToDelete.name}
                </div>
                <div className="text-xs opacity-80 mt-1">
                  <code className="px-2 py-0.5 rounded bg-red-500/15 text-red-700 dark:bg-red-500/30 dark:text-red-100">{keyToDelete.key_prefix}********</code>
                  <span className="mx-2"> · </span>
                  Created {new Date(keyToDelete.created_at).toLocaleDateString()}
                </div>
              </div>
            )}
          </div>
          <div className="text-xs text-slate-600 dark:text-slate-400 mt-3">
            This action cannot be undone. All requests using this key will immediately fail.
          </div>
        </Modal.Body>
        <Modal.Footer className="border-0 pt-0 px-4 pb-4">
          <Button variant="secondary" onClick={() => setShowDeleteKeyModal(false)}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleDeleteApiKey}>
            Revoke
          </Button>
        </Modal.Footer>
      </Modal>

      {/* Revoke all sessions confirmation modal */}
      <Modal show={showRevokeAllModal} onHide={() => setShowRevokeAllModal(false)} centered contentClassName="modal-matte">
        <Modal.Header closeButton className="border-0 pt-4 px-4">
          <Modal.Title>Sign Out All Sessions</Modal.Title>
        </Modal.Header>
        <Modal.Body className="px-4 pt-2 pb-4">
          <div className="text-sm">
            Are you sure you want to <span className="font-semibold">sign out</span> all other sessions?
            <div className="mt-3 p-3 rounded-xl bg-red-500/10 ring-1 ring-red-500/20">
              <div className="font-medium">This will sign out {sessions.filter(s => !s.current).length} session{sessions.filter(s => !s.current).length !== 1 ? 's' : ''}</div>
              <div className="text-xs opacity-80 mt-1">Your current session will remain active</div>
            </div>
          </div>
          <div className="text-xs text-slate-600 dark:text-slate-400 mt-3">
            This action cannot be undone. All other devices will need to sign in again.
          </div>
        </Modal.Body>
        <Modal.Footer className="border-0 pt-0 px-4 pb-4">
          <Button variant="secondary" onClick={() => setShowRevokeAllModal(false)} disabled={busyRevokeAll}>
            Cancel
          </Button>
          <Button variant="rose" onClick={revokeAllSessions} disabled={busyRevokeAll}>
            {busyRevokeAll ? 'Signing out...' : 'Sign out all'}
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  )
}