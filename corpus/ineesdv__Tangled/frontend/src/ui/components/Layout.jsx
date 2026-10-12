import React, { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { OverlayTrigger, Tooltip } from 'react-bootstrap'
import { client } from '../lib/api'

import {
  Mail,
  LayoutDashboard,
  Server,
  UserSquare2,
  FileText,
  Users,
  Megaphone,
  Settings,
  LogOut,
  Sun,
  Moon,
  Menu,
  ChevronsLeft,
  ChevronsRight,
  UserCog,
  CircleUserRound
} from 'lucide-react'

export default function Layout({ children, onThemeToggle, dark }) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(false)
  const [userOpen, setUserOpen] = useState(false)

  const navigate = useNavigate()
  const api = client()

  const logout = async () => {
    try {
      const token = localStorage.getItem('token')
      await api.post('/auth/logout', null, {
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      })
    } catch (_) {
      /* ignore */
    } finally {
      localStorage.removeItem('token')
      navigate('/login')
    }
  }

  const NavItem = ({ to, label, Icon }) => {
    return (
      <NavLink
        to={to}
        end={to === '/'}
        className={({ isActive }) =>
          [
            collapsed
              ? 'group rail-btn mx-auto'
              : 'group flex items-center gap-3 px-3 py-2 rounded-xl w-full',
            'text-slate-700 dark:text-slate-200 hover:bg-black/5 dark:hover:bg-white/10 no-underline transition-colors',
            isActive ? 'bg-primary/15 text-[var(--mlf-primary)] ring-1 ring-primary/25' : ''
          ].join(' ')
        }
        onClick={() => setMobileOpen(false)}
      >
        {({ isActive }) => (
          <>
            <Icon
              size={18}
              className={isActive ? 'text-[var(--mlf-primary)]' : 'text-[var(--mlf-primary)] opacity-70'}
            />
            {!collapsed && <span className="truncate ml-1.5">{label}</span>}
          </>
        )}
      </NavLink>
    )
  }


  const Sidebar = (
    <aside
      className={[
        'sidebar nav-bg z-50 flex flex-col',
        collapsed ? 'w-16' : 'w-72 md:w-64',
        (collapsed ? 'px-2' : 'px-3') + ' py-4',
        'backdrop-blur-xl bg-white/65 dark:bg-white/5',
        'border-r border-black/5 dark:border-white/10 shadow-card',
        'md:static md:translate-x-0 fixed inset-y-0 left-0 transform transition-transform',
        mobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0',
        'md:h-dvh'
      ].join(' ')}
      role="navigation"
    >
      {/* Logo */}
      <div className={`flex items-center ${collapsed ? 'justify-center gap-0 px-0' : 'gap-3 px-1'}`}>
        <button
          onClick={() => setCollapsed(v => !v)}
          className={`flex items-center justify-center
                      transition-all duration-200 hover:scale-105
                      ${collapsed ? 'h-10 w-10' : 'h-12 w-12'}`}
          style={{
            filter: 'drop-shadow(0 4px 6px rgba(0, 0, 0, 0.1)) drop-shadow(0 2px 4px rgba(0, 0, 0, 0.06))'
          }}
          aria-label="Logo"
        >
          <img
            src="/logo.svg"
            alt="Tangled Logo"
            className="h-full w-full object-contain -ml-1"
          />
        </button>

        {!collapsed && (
          <>
            <div className="flex-1">
              <img src="/tangled-text.svg" alt="Tangled" className="h-5 w-auto mb-0.5 -ml-1"/>
              <div className="text-xs text-slate-500 dark:text-slate-400">Phishing platform</div>
            </div>
            <button
              className="ml-auto hidden md:inline-flex h-9 w-9 items-center justify-center rounded-xl hover:bg-black/5 dark:hover:bg-white/10"
              onClick={() => setCollapsed(true)}
              aria-label="Collapse sidebar"
            >
              <ChevronsLeft size={18} />
            </button>
          </>
        )}
      </div>

      {/* Nav links */}
      <div className="mt-4 space-y-1">
        <NavItem to="/" label="Overview" Icon={LayoutDashboard} />
        <NavItem to="/campaigns" label="Campaigns" Icon={Megaphone} />
        <NavItem to="/servers" label="Servers" Icon={Server} />
        <NavItem to="/profiles" label="Sender Profiles" Icon={UserSquare2} />
        <NavItem to="/templates" label="Templates" Icon={FileText} />
        <NavItem to="/lists" label="Target Lists" Icon={Users} />
        <NavItem to="/config" label="Settings" Icon={Settings} />
      </div>

      <div className="mt-auto pt-4 relative">
        <button
          onClick={() => setUserOpen(o => !o)}
          className={`w-full inline-flex items-center rounded-xl transition
             ${collapsed ? 'justify-center px-0 py-0 hover:bg-transparent' : 'px-2 py-2 hover:bg-black/5 dark:hover:bg-white/10'}`}
          aria-haspopup="menu"
          aria-expanded={userOpen ? 'true' : 'false'}
        >
          <div className="rail-btn rail-1 flex items-center justify-center">
            <CircleUserRound size={20} />
          </div>
          {!collapsed && (
            <div className="ml-3 text-left">
              <div className="text-sm font-medium text-slate-900 dark:text-white">Admin</div>
              <div className="text-xs text-slate-500 dark:text-slate-400">Administrator</div>
            </div>
          )}
        </button>

        {userOpen && !collapsed && (
          <div
            className="absolute left-0 right-0 bottom-full mb-2 z-50 rounded-xl p-2
                       bg-white/95 dark:bg-glass/90 backdrop-blur-xl
                       ring-1 ring-black/10 dark:ring-0 shadow-card"
            role="menu"
          >
            <NavLink
              to="/account"
              onClick={() => { setUserOpen(false); setMobileOpen(false) }}
              className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm
                         text-slate-800 dark:text-slate-100 no-underline
                         hover:bg-black/5 dark:hover:bg-white/10"
            >
              <UserCog size={16} /> <span>Manage account</span>
            </NavLink>
            <button
              onClick={() => { setUserOpen(false); logout() }}
              className="mt-1 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm
                         text-slate-800 dark:text-slate-100
                         hover:bg-black/5 dark:hover:bg-white/10"
            >
              <LogOut size={16} /> <span>Logout</span>
            </button>
          </div>
        )}

        {userOpen && collapsed && (
          <div
            className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 z-50 rounded-xl p-2
                      bg-white/95 dark:bg-glass/90 backdrop-blur-xl
                      ring-1 ring-black/10 dark:ring-0 shadow-card
                      flex flex-col items-center gap-2"
            role="menu"
          >
            <OverlayTrigger placement="right" overlay={<Tooltip id="tt-account">Manage account</Tooltip>}>
              <NavLink
                to="/account"
                onClick={() => { setUserOpen(false); setMobileOpen(false) }}
                className="inline-flex h-10 w-10 items-center justify-center rounded-xl
                          text-slate-800 dark:text-slate-100 no-underline
                          hover:bg-black/5 dark:hover:bg-white/10"
              >
                <UserCog size={16} />
              </NavLink>
            </OverlayTrigger>

            <OverlayTrigger placement="right" overlay={<Tooltip id="tt-logout">Logout</Tooltip>}>
              <button
                onClick={() => { setUserOpen(false); logout() }}
                className="inline-flex h-10 w-10 items-center justify-center rounded-xl
                          text-slate-800 dark:text-slate-100
                          hover:bg-black/5 dark:hover:bg-white/10"
              >
                <LogOut size={16} />
              </button>
            </OverlayTrigger>
          </div>
        )}


      </div>
    </aside>
  )

  return (
    <div className="h-dvh w-full bg-gray-50 dark:bg-surface flex overflow-hidden">
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/40 md:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden
        />
      )}

      {Sidebar}

      {/* Content */}
      <main className="flex-1 h-dvh overflow-auto overscroll-contain scroll-area">
        {/* Header row */}
        <div className="px-4 pt-4 pb-2 md:px-6 flex items-center justify-between">
          <button
            className="md:hidden inline-flex h-10 w-10 items-center justify-center rounded-xl hover:bg-black/5 dark:hover:bg-white/10"
            onClick={() => setMobileOpen(true)}
            aria-label="Open navigation"
          >
            <Menu size={18} />
          </button>

          <div className="ml-auto">
            <OverlayTrigger placement="bottom" overlay={<Tooltip id="tt-theme-top">Toggle theme</Tooltip>}>
              <button
                onClick={() => onThemeToggle && onThemeToggle()}
                aria-label="Toggle theme"
                className="inline-flex h-10 w-10 items-center justify-center rounded-xl
                          ring-1 ring-black/10 dark:ring-0 ring-offset-0
                          bg-white/80 dark:bg-white/5 hover:bg-white/90 dark:hover:bg-white/10
                          transition"
              >
                {dark ? <Sun size={18} /> : <Moon size={18} />}
              </button>
            </OverlayTrigger>
          </div>
        </div>

        {/* Page content */}
        <div className="px-4 pb-4 md:px-6 md:pb-6">
          {children}
        </div>
      </main>

    </div>
  )
}
