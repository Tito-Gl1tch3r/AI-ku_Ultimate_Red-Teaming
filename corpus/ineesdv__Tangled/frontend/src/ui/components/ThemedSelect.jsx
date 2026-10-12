import React, { useState, useMemo, useRef, useEffect } from 'react'
import { ChevronDown, Check } from 'lucide-react'

function ThemedSelect({
  options = [],
  value,
  onChange,
  placeholder = 'Select…',
  searchable = true,
}) {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const ref = useRef(null)

  const label = useMemo(
    () => options.find(o => String(o.value) === String(value))?.label || '',
    [options, value]
  )

  const filtered = useMemo(() => {
    if (!searchable) return options // no filtering if not searchable
    const s = q.trim().toLowerCase()
    if (!s) return options
    return options.filter(o => (o.label || '').toLowerCase().includes(s))
  }, [q, options, searchable])

  useEffect(() => {
    const onDoc = (e) => { if (!ref.current?.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  // Close menu resets query so the next open starts fresh
  useEffect(() => { if (!open) setQ('') }, [open])

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="w-full text-left rounded-xl bg-white/70 dark:bg-white/5 px-3 py-2 text-sm
                   text-slate-900 dark:text-slate-100 ring-1 ring-black/10 dark:ring-white/10
                   hover:bg-white/80 dark:hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-primary/70
                   flex items-center justify-between gap-2"
      >
        <span className={`truncate ${label ? '' : 'text-slate-500 dark:text-slate-400'}`}>
          {label || placeholder}
        </span>
        <ChevronDown size={16} className="opacity-70 shrink-0" />
      </button>

      {open && (
        <div
          className="absolute z-50 mt-1 w-full menu-elevated rounded-xl overflow-hidden
                     ring-1 ring-black/10 dark:ring-white/10 bg-white/95 dark:bg-[#0b1220]"
        >
          {searchable && (
            <div className="p-2 border-b border-black/5 dark:border-white/10">
              <input
                className="w-full rounded-lg bg-white/80 dark:bg-white/10 px-3 py-2 text-sm
                           text-slate-900 dark:text-slate-100 ring-1 ring-black/10 dark:ring-white/10
                           placeholder:text-slate-500 dark:placeholder:text-slate-400
                           focus:outline-none focus:ring-2 focus:ring-primary/70"
                placeholder="Search…"
                value={q}
                onChange={(e)=>setQ(e.target.value)}
                autoFocus
              />
            </div>
          )}

          <div className="max-h-56 overflow-auto py-1 scroll-area">
            {filtered.length === 0 && (
              <div className="px-3 py-2 text-sm text-slate-500 dark:text-slate-400">No results</div>
            )}
            {filtered.map(opt => (
              <button
                key={opt.value}
                type="button"
                onClick={() => { onChange(opt.value); setOpen(false) }}
                className="w-full text-left px-3 py-2 text-sm hover:bg-black/5 dark:hover:bg-white/10 flex items-center justify-between"
              >
                <span className="truncate">{opt.label}</span>
                {String(opt.value) === String(value) && <Check size={14} className="opacity-70" />}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
export default ThemedSelect
