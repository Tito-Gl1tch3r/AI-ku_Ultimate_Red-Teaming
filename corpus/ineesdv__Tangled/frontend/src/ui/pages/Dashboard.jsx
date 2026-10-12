import React, { useEffect, useMemo, useRef, useState } from 'react'
import { client } from '../lib/api'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { CalendarDays, PauseCircle, PlayCircle, Send, ArrowBigRightDash } from 'lucide-react'
import { OverlayTrigger, Tooltip } from 'react-bootstrap'
import { lazy, Suspense } from 'react'
import StatusPill from '../components/StatusPill'

const CalendarSection = lazy(() => import('../components/CalendarSection'))

function StatCard({ icon: Icon, label, value, delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="rounded-2xl bg-white/80 dark:bg-glass/80 ring-1 ring-black/10 dark:ring-0 shadow-card p-4 flex items-center gap-3"
    >
      <div className="rail-btn bg-primary/90 text-white shadow"><Icon size={18} /></div>
      <div className="min-w-0">
        <div className="text-xs text-slate-600 dark:text-slate-300/90">{label}</div>
        <div className="text-2xl font-semibold">{value}</div>
      </div>
    </motion.div>
  )
}

export default function Dashboard() {
  const api = client()
  const [stats, setStats] = useState(null)
  const [campaigns, setCampaigns] = useState([])
  const [calendar, setCalendar] = useState([])

  useEffect(() => {
    const load = async () => {
      const [s, c, cal] = await Promise.all([
        api.get('/api/stats'),
        api.get('/api/campaigns'),
        api.get('/api/campaigns_calendar'),
      ])
      setStats(s.data)
      setCampaigns(c.data)
      setCalendar(cal.data)
    }
    load()
  }, [])

  const events = useMemo(() => {
    return (calendar || []).map((e, i) => ({
      id: e.id || String(i + 1),
      title: e.title || e.name || 'Campaign',
      start: e.start,
      end: e.end || e.start,
      backgroundColor: 'rgba(109,113,236,0.18)',
      borderColor: 'rgba(109,113,236,0.35)',
      textColor: 'var(--mlf-primary)',
      extendedProps: { status: e.status }
    }))
  }, [calendar])

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-slate-900 dark:text-white">Overview</h1>

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard icon={PlayCircle} label="Active Campaigns" value={stats.active_campaigns} delay={0} />
          <StatCard icon={PauseCircle} label="Paused" value={stats.paused_campaigns} delay={0.05} />
          <StatCard icon={CalendarDays} label="Scheduled" value={stats.scheduled_campaigns} delay={0.1} />
          <StatCard icon={Send} label="Sent Today" value={stats.emails_sent_today} delay={0.15} />
        </div>
      )}

      {/* Recent campaigns */}
      <div className="rounded-2xl ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-glass/80 shadow-card">
        <div className="px-4 pt-3 pb-2 flex items-center justify-between">
          <h2 className="text-sm font-medium">Recent Campaigns</h2>
          <OverlayTrigger placement="top" overlay={<Tooltip>See all campaigns</Tooltip>}>
            <Link to="/campaigns" 
              className="text-[var(--mlf-primary)] hover:text-[var(--mlf-primary)]/80 transition-colors"
            >
              <ArrowBigRightDash size={20} />
            </Link>
          </OverlayTrigger>
        </div>
        <div className="px-3 pb-3">
          {campaigns.length === 0 ? (
            <div className="p-4 text-sm text-slate-500 dark:text-slate-300">No campaigns yet.</div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
              {campaigns.slice(0, 4).map((c, i) => (
                <motion.div
                  key={c.id}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.04 }}
                  className="rounded-xl ring-1 ring-black/10 dark:ring-white/10 bg-white/70 dark:bg-white/5 p-3"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-medium text-slate-900 dark:text-white truncate max-w-[180px]">{c.name}</div>
                      <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                        <span className="opacity-75">Created at:</span> {new Date(c.created_at).toLocaleString()}
                      </div>
                    </div>
                    <StatusPill status={c.status} />
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Calendar */}
      <Suspense fallback={
        <div className="rounded-2xl ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-glass/80 shadow-card p-3">
          <div className="flex items-center justify-center h-[560px]">
            <div className="text-slate-600 dark:text-slate-400">Loading calendar...</div>
          </div>
        </div>
      }>
        <CalendarSection events={events} />
      </Suspense>
    </div>
  )
}
