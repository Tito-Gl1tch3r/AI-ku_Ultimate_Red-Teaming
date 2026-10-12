import React, { useEffect, useMemo, useRef, useState, forwardRef } from 'react'
import { client } from '../lib/api'
import { toast } from 'react-toastify'
import Editor from '@monaco-editor/react'
import DataTable, { createTheme } from 'react-data-table-component'
import { Button, Modal, OverlayTrigger, Tooltip, Dropdown, Form } from 'react-bootstrap'
import VarAutocomplete from '../components/VarAutocomplete'
import ThemedSelect from '../components/ThemedSelect'
import {
  Plus, MoreVertical, Pencil, Trash2, Copy, Search, Braces, CalendarClock,
  FileCode, Paperclip, Info, ExternalLink, Users, PlusCircle, Clock, User,
  Globe, Settings, FileText, Code, Video, CalendarX2, File as FileIcon, FileImage,
  FileAudio, FileVideo, FileArchive, FileSpreadsheet, Upload, CalendarSync, FileCog
} from 'lucide-react'
import { Columns } from 'lucide-react'
import { Layout } from 'lucide-react'
import DOMPurify from 'dompurify'
import '../components/datatableThemes'
import { useTheme } from '../../hooks/useTheme'
import { inputCls, inputClsSearchbar } from '../utils/styles'

const FieldLabel = ({ children, required, acceptsVars, tooltip }) => (
  <div className="flex items-center gap-2 mb-1">
    <span className="text-sm font-medium inline-flex items-center gap-1">
      {children}

      {required && (
        <sup className="ms-1 text-[var(--mlf-primary)]">
          <OverlayTrigger placement="top" overlay={<Tooltip>This field is required</Tooltip>}>
            <span>*</span>
          </OverlayTrigger>
        </sup>
      )}

      {acceptsVars && (
        <sup>
          <OverlayTrigger placement="top" overlay={<Tooltip>This field accepts variables</Tooltip>}>
            <span className="inline-flex items-center justify-center h-5 w-5 rounded text-[var(--mlf-primary)]">
              <Braces size={12} />
            </span>
          </OverlayTrigger>
        </sup>
      )}
    </span>

    {tooltip && (
      <OverlayTrigger placement="top" overlay={<Tooltip>{tooltip}</Tooltip>}>
        <span className="inline-flex items-center justify-center h-5 w-5 rounded text-slate-500 dark:text-slate-300">
          <Info size={14} />
        </span>
      </OverlayTrigger>
    )}
  </div>
)

const TitleWithLabel = ({ title, icon: Icon, required, acceptsVars, tooltip }) => (
  <div className="flex items-center gap-2 mb-3">
    <Icon size={16} />
    <span className="text-sm font-semibold">
      {title}
      {required && (
        <>
          <sup className="ms-1 text-[var(--mlf-primary)]">
            <OverlayTrigger placement="top" overlay={<Tooltip>This field is required</Tooltip>}>
              <span>*</span>
            </OverlayTrigger>
          </sup>
        </>
      )}
      {acceptsVars && (
        <sup>
          <OverlayTrigger
            placement="top"
            overlay={<Tooltip>This field accepts variables like {'{{firstName}}'}</Tooltip>}
          >
            <span className="inline-flex items-center justify-center h-5 w-5 rounded text-[var(--mlf-primary)]">
              <Braces size={12} />
            </span>
          </OverlayTrigger>
        </sup>
      )}
    </span>
    {tooltip && (
      <OverlayTrigger placement="top" overlay={<Tooltip>{tooltip}</Tooltip>}>
        <span className="inline-flex items-center justify-center h-5 w-5 rounded text-slate-500 dark:text-slate-300">
          <Info size={14} />
        </span>
      </OverlayTrigger>
    )}
  </div>
);

function TemplateIconBtn({ icon: Icon, onClick, title, ariaLabel }) {
  return (
    <OverlayTrigger placement="top" overlay={<Tooltip>{title}</Tooltip>}>
      <button
        type="button"
        onClick={onClick}
        title={title}
        aria-label={ariaLabel || title}
        className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-white/80 dark:bg-white/5 hover:bg-white/90 dark:hover:bg-white/10 ring-1 ring-black/10 dark:ring-white/10 focus:outline-none focus:ring-2 focus:ring-primary/70 transition-colors"
      >
        <Icon size={16} />
      </button>
    </OverlayTrigger>
  )
}

const ActionToggle = forwardRef(({ onClick }, ref) => (
  <button
    ref={ref}
    onClick={(e) => { e.preventDefault(); onClick(e) }}
    className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-transparent hover:bg-black/5 dark:hover:bg-white/10"
    aria-label="Row actions"
  >
    <MoreVertical size={16} />
  </button>
))

// Badges
function KindPill({ tone, icon: Icon, children }) {
  const tones = {
    purple:
      'bg-indigo-500/5 text-indigo-700 ring-1 ring-inset ring-indigo-500/25 ' +
      'dark:bg-indigo-400/25 dark:text-indigo-200 dark:ring-indigo-400/35',
    amber:
      'bg-amber-500/5 text-amber-700 ring-1 ring-inset ring-amber-500/25 ' +
      'dark:bg-amber-500/15 dark:text-amber-300 dark:ring-amber-500/30',
    sky:
      'bg-sky-500/5 text-sky-700 ring-1 ring-inset ring-sky-500/25 ' +
      'dark:bg-sky-500/15 dark:text-sky-300 dark:ring-sky-500/30',
    fuchsia:
      'bg-fuchsia-500/5 text-fuchsia-700 ring-1 ring-inset ring-fuchsia-500/25 ' +
      'dark:bg-fuchsia-500/15 dark:text-fuchsia-300 dark:ring-fuchsia-500/30',
    slate:
      'bg-slate-500/5 text-slate-700 ring-1 ring-inset ring-slate-500/25 ' +
      'dark:bg-slate-500/15 dark:text-slate-300 dark:ring-slate-500/30',
    emerald:
      'bg-emerald-500/5 text-emerald-700 ring-1 ring-inset ring-emerald-500/25 ' +
      'dark:bg-emerald-500/15 dark:text-emerald-300 dark:ring-emerald-500/30',
    rose:
      'bg-rose-500/5 text-rose-700 ring-1 ring-inset ring-rose-500/25 ' +
      'dark:bg-rose-500/15 dark:text-rose-300 dark:ring-rose-500/30',
  }

  return (
    <span
      className={[
        'inline-flex items-center gap-1.5',
        'px-2.5 py-1',
        'rounded-md text-[11px] font-semibold leading-none',
        tones[tone],
      ].join(' ')}
    >
      {Icon && <Icon size={12} />} {children}
    </span>
  )
}

// Attachment helpers and elements
const formatBytes = (bytes) => {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  const val = bytes / Math.pow(1024, i)
  return `${val.toFixed(val >= 100 || i === 0 ? 0 : 2)} ${units[i]}`
}

const fileKind = (name = '', mime = '') => {
  const n = name.toLowerCase()
  const m = (mime || '').toLowerCase()

  const is = (ext) => n.endsWith(`.${ext}`)
  const has = (s) => m.includes(s)

  if (is('png') || is('jpg') || is('jpeg') || is('gif') || is('webp') || has('image/'))
    return { Icon: FileImage, type: 'image' }

  if (is('mp3') || is('wav') || is('ogg') || has('audio/'))
    return { Icon: FileAudio, type: 'audio' }

  if (is('mp4') || is('mov') || is('avi') || is('mkv') || is('webm') || has('video/'))
    return { Icon: FileVideo, type: 'video' }

  if (is('zip') || is('rar') || is('7z') || is('tar') || is('gz') || has('zip') || has('archive'))
    return { Icon: FileArchive, type: 'archive' }

  if (is('xls') || is('xlsx') || is('csv') || has('spreadsheet'))
    return { Icon: FileSpreadsheet, type: 'spreadsheet' }

  if (is('pdf') || has('pdf'))
    return { Icon: FileText, type: 'pdf' }

  if (is('doc') || is('docx') || has('word'))
    return { Icon: FileText, type: 'document' }

  if (is('ppt') || is('pptx') || has('presentation'))
    return { Icon: FileText, type: 'presentation' }

  if (
    is('js') || is('ts') || is('json') || is('html') || is('css') ||
    is('jsx') || is('tsx') || is('py') || is('java') || is('c') || is('cpp') ||
    is('cs') || is('php') || is('rb') || is('go') || is('xml') || is('yml') || is('yaml') ||
    has('javascript') || has('json') || has('html') || has('text/x-script')
  )
    return { Icon: FileCode, type: 'code' }

  if (is('ics') || has('calendar'))
    return { Icon: CalendarClock, type: 'calendar' }

  if (is('exe') || is('msi') || is('bat') || is('sh') || is('dll') || has('executable'))
    return { Icon: FileCog, type: 'executable' }

  if (is('psd') || is('ai') || is('fig') || is('sketch'))
    return { Icon: FileImage, type: 'design' }

  // Default
  return { Icon: FileIcon, type: 'file' }
}

function FilePicker({ id, multiple, accept, onChange, disabled, label = 'Choose files' }) {
  const inputRef = useRef(null)
  return (
    <div className="inline-flex items-center gap-2">
      <input
        id={id}
        ref={inputRef}
        type="file"
        className="hidden"
        multiple={!!multiple}
        accept={accept}
        onChange={(e) => {
          const fs = e.target.files ? Array.from(e.target.files) : []
          onChange(fs)
          e.target.value = ''
        }}
        disabled={disabled}
      />
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={disabled}
        className="inline-flex items-center gap-2 px-3 py-2 rounded-xl
                   bg-white/80 dark:bg-white/5 hover:bg-white/90 dark:hover:bg-white/10
                   ring-1 ring-black/10 dark:ring-white/10 text-sm"
        title={label}
      >
        <Upload size={16} />
        <span className="font-medium">{label}</span>
      </button>
    </div>
  )
}

function Badge({ children, tone = 'slate' }) {
  const tones = {
    slate: 'bg-slate-500/10 text-slate-700 dark:bg-slate-500/20 dark:text-slate-200',
    purple:
      'text-[var(--mlf-primary)] bg-[color-mix(in_oklab,var(--mlf-primary)_12%,transparent)] ' +
      'dark:bg-[color-mix(in_oklab,var(--mlf-primary)_20%,transparent)] ring-1 ring-inset ring-[color-mix(in_oklab,var(--mlf-primary)_22%,transparent)]',
    red: 'bg-red-500/15 text-red-600 dark:text-red-300',
    green:
      'bg-emerald-500/15 text-emerald-700 ring-1 ring-inset ring-emerald-600/20 ' +
      'dark:bg-emerald-500/20 dark:text-emerald-300 dark:ring-emerald-400/20',
  }
  return (
    <span className={`px-2 py-0.5 rounded-md text-[10px] font-semibold ${tones[tone]}`}>{children}</span>
  )
}

function AttachmentPill({
  icon: Icon, title, subtitle,
  badge, badgeTone = 'slate',
  action,
}) {
  const removed = action?.removed
  return (
    <div className={`flex items-center justify-between gap-3 px-3 py-2 rounded-2xl
                     bg-white/70 dark:bg-white/5 ring-1 ring-black/10 dark:ring-white/10 shadow-sm
                     ${removed ? 'opacity-70' : ''}`}>
      <div className="flex items-center gap-3 min-w-0">
        <div className="inline-flex items-center justify-center h-9 w-9 rounded-xl
                        bg-black/[.04] dark:bg-white/[.06] ring-1 ring-black/10 dark:ring-white/10 shrink-0">
          <Icon size={18} />
        </div>
        <div className="min-w-0">
          <div className="text-sm font-semibold truncate flex items-center gap-2">
            <span className="truncate">{title}</span>
            {badge && <Badge tone={badgeTone}>{badge}</Badge>}
            {removed && <Badge tone="red">Removed</Badge>}
          </div>
          {subtitle && <div className="text-xs text-slate-600 dark:text-slate-300 truncate">{subtitle}</div>}
        </div>
      </div>

      {action?.mode === 'toggle' && (
        <OverlayTrigger placement="top" overlay={<Tooltip>{removed ? 'Undo remove' : 'Remove'}</Tooltip>}>
          <button
            type="button"
            className="inline-flex px-2 h-8 w-8 items-center justify-center rounded-lg
                       hover:bg-black/[.06] dark:hover:bg-white/[.08]"
            title={removed ? 'Undo remove' : 'Remove'}
            aria-label={removed ? 'Undo remove' : 'Remove'}
            onClick={action.onToggle}
          >
            {removed ? <PlusCircle size={16} /> : <Trash2 size={16} />}
          </button>
        </OverlayTrigger>
      )}

      {action?.mode === 'delete' && (
        <OverlayTrigger placement="top" overlay={<Tooltip>Remove</Tooltip>}>
          <button
            type="button"
            className="inline-flex h-8 w-8 items-center justify-center rounded-lg
                       hover:bg-black/[.06] dark:hover:bg-white/[.08]"
            title="Remove"
            aria-label="Remove"
            onClick={action.onDelete}
          >
            <Trash2 size={16} />
          </button>
        </OverlayTrigger>
      )}
    </div>
  )
}

function UnifiedAttachments({
  existing = [],
  newFiles = [],
  removedExistingIds = [],
  onToggleExisting,
  onRemoveNew,
}) {
  const items = [
    ...existing.map(a => ({
      kind: 'existing',
      key: `ex-${a.id}`,
      title: a.filename,
      subtitle: `${formatBytes(a.size || 0)} • ${(a.mime_type || 'file').replace(/^.*\//, '').toUpperCase()}`,
      Icon: fileKind(a.filename, a.mime_type).Icon,
      removed: removedExistingIds.includes(a.id),
      id: a.id,
    })),
    ...newFiles.map((f, i) => ({
      kind: 'new',
      key: `new-${i}-${f.name}`,
      title: f.name,
      subtitle: `${formatBytes(f.size || 0)} • ${(f.type || 'file').replace(/^.*\//, '').toUpperCase()}`,
      Icon: fileKind(f.name, f.type).Icon,
      index: i,
    })),
  ]

  if (!items.length) return <div className="text-sm text-slate-500 dark:text-slate-300">None</div>

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
      {items.map(it => (
        <AttachmentPill
          key={it.key}
          icon={it.Icon}
          title={it.title}
          subtitle={it.subtitle}
          badge={it.kind === 'new' ? 'New' : undefined}
          badgeTone={it.kind === 'new' ? 'green' : 'slate'}
          action={
            it.kind === 'existing'
              ? { mode: 'toggle', removed: it.removed, onToggle: () => onToggleExisting?.(it.id) }
              : { mode: 'delete', onDelete: () => onRemoveNew?.(it.index) }
          }
        />
      ))}
    </div>
  )
}


// Categories input
function CategoriesInput({ categories, setCategories, inputCls }) {
  const clean = (s) => (s ?? '').replace(/\r|\n/g, ' ').trim()
  const [draft, setDraft] = useState('')
  const chipRef = useRef(null)

  const addMany = (arr) => {
    const dedup = new Set(categories || [])
    for (const raw of arr) { const c = clean(raw); if (c) dedup.add(c) }
    setCategories(Array.from(dedup))
  }

  const commit = () => {
    const c = clean(draft)
    if (!c) { setDraft(''); return }
    if (!(categories || []).includes(c)) setCategories([...(categories || []), c])
    setDraft('')
  }

  return (
    <div className="md:col-span-4">
      <FieldLabel>Categories</FieldLabel>

      <div
        className={`${inputCls} pl-2 pr-2 flex flex-wrap items-center gap-1.5 min-h-[32px] cursor-text`}
        onClick={() => chipRef?.current?.focus()}
        role="group"
        aria-label="Categories"
      >
        {(categories || []).map((cat, i) => (
          <span
            key={i}
            className="d-inline-flex align-items-center rounded-xl pl-3 pr-2 py-0.5 text-xs
                       bg-slate-500/10 text-slate-700 dark:bg-slate-500/20 dark:text-slate-200"
            title={cat}
            style={{ lineHeight: 1 }}
          >
            <span className="truncate max-w-[240px]">{cat}</span>
            <button
              type="button"
              className="btn-close ms-2"
              aria-label={`Remove ${cat}`}
              onClick={(e) => {
                e.stopPropagation()
                const next = [...categories]; next.splice(i, 1); setCategories(next)
              }}
              style={{ transform: 'scale(0.6)' }}
            />
          </span>
        ))}

        <input
          ref={chipRef}
          type="text"
          className="bg-transparent border-0 outline-none ring-0 shadow-none
                     focus:outline-none focus:ring-0 focus:shadow-none
                     self-stretch h-[32px] leading-[32px]
                     flex-1 min-w-[80px] text-sm p-0 m-0 caret-current"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commit}
          onPaste={(e) => {
            e.stopPropagation()
            const text = e.clipboardData?.getData('text') || ''
            const parts = text.split(',').map(s => clean(s)).filter(Boolean)
            if (parts.length) addMany(parts)
            e.preventDefault()
          }}
          onKeyDown={(e) => {
            if (['Enter', ',', ' ', 'Backspace'].includes(e.key)) e.stopPropagation()
            if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); commit(); return }
            if (e.key === 'Backspace' && draft === '' && (categories || []).length) {
              e.preventDefault(); const next = [...categories]; next.pop(); setCategories(next)
            }
          }}
          autoComplete="off"
          inputMode="text"
        />
      </div>
    </div>
  )
}

// Preview security
const PREVIEW_CSP = [
  "default-src 'none'",
  "img-src https: data:",
  "style-src 'unsafe-inline'",
  "font-src https: data:",
  "script-src 'none'",
  "connect-src 'none'",
  "frame-ancestors 'none'",
  "form-action 'none'",
  "base-uri 'none'",
  "frame-src 'none'",
  "object-src 'none'",
].join('; ')

function isFullDocument(html = '') {
  const s = html.trim()
  return /<!doctype/i.test(s) || /<html[\s>]/i.test(s)
}

function sanitizeEmailHtml(dirty) {
  const FORBID_TAGS = ['script', 'iframe', 'embed', 'object', 'link', 'base']
  const FORBID_ATTR = ['srcset']

  return DOMPurify.sanitize(dirty, {
    USE_PROFILES: { html: true, svg: false, mathMl: false },
    FORBID_TAGS,
    FORBID_ATTR,
    ALLOW_UNKNOWN_PROTOCOLS: false,
    KEEP_CONTENT: false,
  })
}

function makePreviewShell(fragmentHtml) {
  return `<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <meta http-equiv="Content-Security-Policy" content="${PREVIEW_CSP}">
    <meta name="referrer" content="no-referrer">
    <meta name="color-scheme" content="light dark">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Preview</title>
    <style>
      html,body{margin:0;padding:0}
      body{background:#fff;color:#111}
      img{max-width:100%;height:auto}
      table{border-collapse:collapse}
    </style>
  </head>
  <body>
    ${fragmentHtml}
  </body>
</html>`
}
function injectCspIntoDocument(safeFullDoc) {
  const rmExisting = safeFullDoc.replace(
    /<meta[^>]+http-equiv=["']content-security-policy["'][^>]*>/gi,
    ''
  )
  if (/<head[\s>]/i.test(rmExisting)) {
    return rmExisting.replace(
      /<head([^>]*)>/i,
      `<head$1><meta http-equiv="Content-Security-Policy" content="${PREVIEW_CSP}">`
    )
  }
  if (/<html[\s>]/i.test(rmExisting)) {
    return rmExisting.replace(
      /<html([^>]*)>/i,
      `<html$1><head><meta http-equiv="Content-Security-Policy" content="${PREVIEW_CSP}"></head>`
    )
  }
  return makePreviewShell(rmExisting)
}

function WindowChrome({ title, right }) {
  return (
    <div className="relative flex items-center justify-between h-10 px-3
                    bg-gradient-to-b from-black/[.04] to-black/[.02] dark:from-white/[.08] dark:to-white/[.04]
                    border-b border-black/10 dark:border-white/10">
      <div className="flex items-center gap-1.5">
        <span className="inline-block h-3 w-3 rounded-full bg-red-400/85" />
        <span className="inline-block h-3 w-3 rounded-full bg-amber-400/85" />
        <span className="inline-block h-3 w-3 rounded-full bg-emerald-400/85" />
      </div>
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div className="px-2 py-1 rounded-md text-[11px] font-semibold
                        bg-slate-700/5 dark:bg-white/10
                        ring-1 ring-inset ring-black/10 dark:ring-white/10
                        text-slate-700 dark:text-slate-200">
          {title}
        </div>
      </div>
      <div className="flex items-center gap-1.5">{right}</div>
    </div>
  )
}

// Editor styles
function IconChromeButton({ onClick, title, children }) {
  return (
    <OverlayTrigger placement="top" overlay={<Tooltip>{title}</Tooltip>}>
      <button
        type="button"
        onClick={onClick}
        className="inline-flex items-center justify-center h-7 w-8 rounded-lg
                   bg-white/80 dark:bg-white/10 hover:bg-white/90 dark:hover:bg-white/15
                   ring-1 ring-black/10 dark:ring-white/10"
        aria-label={title}
        title={title}
      >
        {children}
      </button>
    </OverlayTrigger>
  )
}

function VSTabs({ active, showPreviewTab, onSelect, splitView, htmlBanner = true }) {
  const compact = !splitView;

  const base =
    (compact ? 'px-2 ' : 'px-3 ') +
    'group relative py-1.5 rounded-t-lg text-xs font-medium select-none ' +
    'hover:bg-white/60 dark:hover:bg-white/10 transition-colors';

  const activeCls =
    'bg-white dark:bg-[#0b1220]/85 ring-1 ring-black/10 dark:ring-white/10 border-b border-transparent';
  const inactiveCls =
    'text-slate-600 dark:text-slate-300/80 border-b border-black/10 dark:border-white/10';

  const editorLooksActive = splitView || active === 'editor';
  const previewLooksActive = splitView || active === 'preview';

  return (
    <div className="px-2 pt-1 border-b border-black/10 dark:border-white/10">
      <div className={`flex items-end ${compact ? 'gap-1' : 'gap-2'} -mb-[1px]`}>
        {/* template.html */}
        <button
          type="button"
          onClick={() => onSelect('editor')}
          className={`${base} ${editorLooksActive ? activeCls : inactiveCls}`}
        >
          <span className="inline-flex items-center gap-2">
            <FileCode size={14} className="opacity-80" />
            {htmlBanner ? 'template.html' : 'template.txt'}
          </span>
          {editorLooksActive && (
            <span className="absolute -bottom-[1px] left-0 right-0 h-[2px] bg-[var(--mlf-primary)] rounded-t" />
          )}
        </button>

        {/* preview.html */}
        {showPreviewTab && (
          <button
            type="button"
            onClick={() => onSelect('preview')}
            className={`${base} ${previewLooksActive ? activeCls : inactiveCls}`}
          >
            <span className="inline-flex items-center gap-2">
              <Layout size={14} className="opacity-80" />
              preview.html
            </span>
            {previewLooksActive && (
              <span className="absolute -bottom-[1px] left-0 right-0 h-[2px] bg-[var(--mlf-primary)] rounded-t" />
            )}
          </button>
        )}
      </div>
    </div>
  )
}

export default function Templates() {
  const api = client()

  // Theme selector
  const isDark = useTheme()

  // Data
  const [rows, setRows] = useState([])
  const [q, setQ] = useState('')

  const load = async () => { setRows((await api.get('/api/templates')).data) }
  useEffect(() => { load() }, [])

  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase()
    if (!s) return rows
    return rows.filter(r =>
      r.name?.toLowerCase().includes(s) ||
      r.subject?.toLowerCase().includes(s)
    )
  }, [rows, q])

  // Confirm delete
  const [showDel, setShowDel] = useState(false)
  const [delRow, setDelRow] = useState(null)

  const askDel = (r) => {
    setDelRow(r)
    setShowDel(true)
  }

  const doDel = async () => {
    if (!delRow) return
    try {
      await api.delete(`/api/templates/${delRow.id}`)
      toast.success('Template deleted')
      setShowDel(false)
      setDelRow(null)
      load()

    } catch {
      toast.error('Failed to delete template')
    }
  }

  // Duplicate template
  const [showDup, setShowDup] = useState(false)
  const [dupRow, setDupRow] = useState(null)
  const [dupName, setDupName] = useState('')

  const openDup = (row) => {
    setDupRow(row)
    setDupName(row.name + ' (copy)')
    setShowDup(true)
  }

  const doDup = async () => {
    try {
      await api.post(`/api/templates/${dupRow.id}/duplicate`, { name: dupName })
      toast.success('Template duplicated')
      setShowDup(false)
      setDupRow(null)
      setDupName('')
      load()
    }
    catch (e) {
      toast.error(e?.response?.data?.detail || 'Could not duplicate')
    }
  }

  // Edit/create modal
  const [show, setShow] = useState(false)
  const [edit, setEdit] = useState(null)

  // Main attributes
  const [name, setName] = useState('')
  const [subject, setSubject] = useState('')

  // Body
  const [mode, setMode] = useState('both')
  const [bodyHtml, setBodyHtml] = useState('<h1>Hello {{firstName}}</h1>')
  const [bodyText, setBodyText] = useState('Hello {{firstName}}')
  const [showPreview, setShowPreview] = useState(false)
  const previewRef = useRef(null)

  // Attachments
  const [files, setFiles] = useState([])
  const [existingAtts, setExistingAtts] = useState([])
  const [removeIds, setRemoveIds] = useState([])

  // Calendar
  const [calendarEnabled, setCalendarEnabled] = useState(false)
  const [calMode, setCalMode] = useState('off') // off|invite|reschedule|cancel

  // Cancellation-only fields
  const [isCancellation, setIsCancellation] = useState(false)
  const [meetingUid, setMeetingUid] = useState('')
  const [meetingSequence, setMeetingSequence] = useState('')

  // Calendar mode helpers
  const setModeInvite = () => {
    setCalMode('invite')
    setCalendarEnabled(true)
    setIsCancellation(false)
    setMeetingUid('')
    setMeetingSequence('')
  }

  const setModeCancel = () => {
    setCalMode('cancel')
    setCalendarEnabled(false)
    setIsCancellation(true)
  }

  const setModeOff = () => {
    setCalMode('off')
    setCalendarEnabled(false)
    setIsCancellation(false)
  }

  const setModeReschedule = () => {
    setCalMode('reschedule')
    setCalendarEnabled(false)
    setIsCancellation(false)
  }

  const [meetingSummary, setMeetingSummary] = useState('')
  const [organizerCn, setOrganizerCn] = useState('')
  const [organizerEmail, setOrganizerEmail] = useState('')
  const [attendees, setAttendees] = useState([])
  const [newAttCN, setNewAttCN] = useState('')
  const [newAttEmail, setNewAttEmail] = useState('')

  const addAtt = () => {
    const cn = (newAttCN || '').trim()
    const email = (newAttEmail || '').trim()
    if (!cn && !email) return
    setAttendees([...(attendees || []), { cn, email }])
    setNewAttCN('')
    setNewAttEmail('')
  }
  const delAtt = (i) => setAttendees(attendees.filter((_, idx) => idx !== i))

  const [disableForwarding, setDisableForwarding] = useState(false)
  const [calendarPriority, setCalendarPriority] = useState(2)
  const [categories, setCategories] = useState([])
  const [isPrivate, setIsPrivate] = useState(null)
  const [location, setLocation] = useState('')
  const [allowResponses, setAllowResponses] = useState(false)
  const [includeAllTargets, setIncludeAllTargets] = useState(false)

  const browserTz = (Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC')
  const [meetingTz, setMeetingTz] = useState(browserTz)
  const [meetingBeginLocal, setMeetingBeginLocal] = useState('')
  const [meetingEndLocal, setMeetingEndLocal] = useState('')

  const [existingCalAtt, setExistingCalAtt] = useState([])
  const [calFiles, setCalFiles] = useState([])
  const [removeCalIds, setRemoveCalIds] = useState([])

  const [meetingProvider, setMeetingProvider] = useState('none') // none|teams|gmeet
  const [meetingUrl, setMeetingUrl] = useState('')

  const [varExamples, setVarExamples] = useState({})

  // Calendar utils
  const icsToInput = (s) => {
    if (!s || s.length < 15) return ''
    const yyyy = s.slice(0, 4), mm = s.slice(4, 6), dd = s.slice(6, 8)
    const HH = s.slice(9, 11), MM = s.slice(11, 13)
    return `${yyyy}-${mm}-${dd}T${HH}:${MM}`
  }
  const inputToIcs = (s) => {
    if (!s) return ''
    const [datePart, timePart] = s.split('T'); if (!datePart || !timePart) return ''
    const [y, m, d] = datePart.split('-'); const [H, Mi, Se] = timePart.split(':')
    const ss = (Se && Se.length > 0) ? Se.padStart(2, '0') : '00'
    return `${y}${m}${d}T${H.padStart(2, '0')}${Mi.padStart(2, '0')}${ss}`
  }

  // Attachments
  const fetchAttachments = async (id) => {
    const { data } = await api.get(`/api/templates/${id}/attachments`)
    setExistingAtts(data)
    setRemoveIds([])
  }

  const fetchCalAttachment = async (id) => {
    const { data } = await api.get(`/api/templates/${id}/calendar_attachments`)
    setExistingCalAtt(data || [])
    setRemoveCalIds([])
    setCalFiles([])
  }

  // Editor
  const [activePane, setActivePane] = useState('editor') // editor|preview
  const [splitView, setSplitView] = useState(false)

  const safeSetEditorValue = (v = '') => {
    try { editorRef.current?.setValue(v) } catch { }
  };

  // Clear inactive body
  useEffect(() => {
    if (mode === 'html') {
      setBodyText('')
      setShowPreview(true)
    } else if (mode === 'text') {
      setBodyHtml('')
      safeSetEditorValue('')
      setShowPreview(false)
    }
  }, [mode]);


  const openCreate = () => {
    setEdit(null)
    setName('')
    setSubject('')
    setBodyHtml('')
    setBodyText('')
    setMode('both')
    setShowPreview(false)
    setFiles([])
    setExistingAtts([])
    setRemoveIds([])
    setCalendarEnabled(false)
    setCalMode('off')
    setIsCancellation(false)
    setMeetingUid('')
    setMeetingSequence('')
    setMeetingSummary('')
    setOrganizerCn('')
    setOrganizerEmail('')
    setAttendees([])
    setNewAttCN('')
    setNewAttEmail('')
    setDisableForwarding(false)
    setCalendarPriority(2)
    setCategories([])
    setIsPrivate(null)
    setLocation('')
    setAllowResponses(false)
    setIncludeAllTargets(false)
    setMeetingTz(browserTz)
    setMeetingBeginLocal('')
    setMeetingEndLocal('')
    setExistingCalAtt([])
    setCalFiles([])
    setRemoveCalIds([])
    setMeetingProvider('none')
    setMeetingUrl('')
    loadVars()
    setActiveStep(1)
    setShow(true)
  }
  const openEdit = (r) => {
    setEdit(r)
    setName(r.name)
    setSubject(r.subject)
    const hasHtml = !!(r.body_html && r.body_html.trim())
    const hasText = !!(r.body_text && r.body_text.trim())
    setMode(hasHtml && hasText ? 'both' : (hasHtml ? 'html' : 'text'))
    setBodyHtml(r.body_html || '')
    setBodyText(r.body_text || '')
    setShowPreview(false)

    setFiles([])
    setRemoveIds([])

    const isCancel = !!r.is_calendar_cancellation
    const isReschedule = !!r.is_calendar_reschedule
    const isInvite = !!r.calendar_enabled && !isCancel && !isReschedule

    setCalMode(
      isCancel ? 'cancel' :
        isReschedule ? 'reschedule' :
          isInvite ? 'invite' : 'off'
    )
    setCalendarEnabled(isInvite)
    setIsCancellation(isCancel)

    setMeetingSummary(r.meeting_summary || '')
    setOrganizerCn(r.organizer_cn || '')
    setOrganizerEmail(r.organizer_email || '')
    setAttendees(r.attendees || [])
    setNewAttCN('')
    setNewAttEmail('')
    setDisableForwarding(!!r.disable_forwarding)
    setCalendarPriority(r.calendar_priority || 2)
    setCategories(r.calendar_categories || [])
    setIsPrivate(r.calendar_private ? true : null)

    setMeetingTz(r.meeting_tz || browserTz)
    setMeetingBeginLocal(icsToInput(r.meeting_begin || ''))
    setMeetingEndLocal(icsToInput(r.meeting_end || ''))
    setLocation(r.location || '')
    setAllowResponses(!!(r.allow_responses ?? true))
    setIncludeAllTargets(!!r.include_all_targets_as_attendees)

    // Cancellation-only fields
    setMeetingUid(r.meeting_uid || '')
    setMeetingSequence(
      typeof r.meeting_sequence === 'number' ? String(r.meeting_sequence) : (r.meeting_sequence || '')
    )

    // Provider + URL (disable for cancellations)
    const provider = isCancel ? 'none' : (r.meeting_provider || 'none')
    setMeetingProvider(provider)
    setMeetingUrl(provider === 'none' ? '' : (r.meeting_url || ''))

    setShow(true)
    fetchAttachments(r.id)

    // Skip calendar-attachment fetch for cancellations
    if (!isCancel) fetchCalAttachment(r.id)
    else {
      setExistingCalAtt([])
      setCalFiles([])
      setRemoveCalIds([])
    }

    loadVars()
    setActiveStep(1)
  }

  const prettyErr = (e) => {
    const d = e?.response?.data?.detail
    if (!d) return 'Failed to save template'
    if (typeof d === 'string') return d
    if (Array.isArray(d) && d.length && d[0]?.msg) return d[0].msg
    return 'Failed to save template'
  }
  const onFiles = (e) => setFiles(Array.from(e.target.files || []))
  const toggleRemove = (id) => setRemoveIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])

  const save = async () => {
    try {

      // Normalize bodies according to the current mode
      let html = (bodyHtml || '').trim();
      let text = (bodyText || '').trim();

      if (mode === 'html') text = '';
      if (mode === 'text') html = '';

      // Base calendar properties
      const sharedCal = {
        meeting_summary: meetingSummary || null,
        organizer_cn: organizerCn || null,
        organizer_email: organizerEmail || null,
        attendees,
        disable_forwarding: disableForwarding,
        calendar_priority: calendarPriority,
        calendar_categories: categories && categories.length ? categories : null,
        calendar_private: (isPrivate === null ? null : !!isPrivate),
        meeting_begin: inputToIcs(meetingBeginLocal) || null,
        meeting_end: inputToIcs(meetingEndLocal) || null,
        meeting_tz: meetingTz || null,
        location: location || null,
        allow_responses: !!allowResponses,
      }

      const isInvite = calMode === 'invite'
      const isReschedule = calMode === 'reschedule'
      const isCancel = calMode === 'cancel'

      // Client side validations
      if (isInvite) {
        if (!organizerEmail) return toast.error('Organizer email is required for invites')
        if (!sharedCal.meeting_begin || !sharedCal.meeting_end) return toast.error('Start and End time are required for invites')
        if (meetingProvider !== 'none' && !(meetingUrl || '').trim()) {
          return toast.error('Meeting URL is required when a provider is selected')
        }
      }
      if (isCancel) {
        if (!organizerEmail) return toast.error('Organizer email is required for cancellations')
        if (!sharedCal.meeting_begin || !sharedCal.meeting_end) return toast.error('Start and End time are required for cancellations')
        if (!meetingUid?.trim()) return toast.error('Meeting UID is required for cancellations')
        if (meetingSequence === '' || Number.isNaN(Number(meetingSequence)) || Number(meetingSequence) < 0) {
          return toast.error('Sequence must be a non-negative integer')
        }
      }
      if (isReschedule) {
        if (!organizerEmail) return toast.error('Organizer email is required for reschedules')
        if (!sharedCal.meeting_begin || !sharedCal.meeting_end) {
          return toast.error('Start and End time are required for reschedules')
        }
        if (!meetingUid?.trim()) return toast.error('Meeting UID is required for reschedules')
        if (meetingSequence === '' || Number.isNaN(Number(meetingSequence)) || Number(meetingSequence) < 0) {
          return toast.error('Sequence must be a non-negative integer')
        }
      }

      const base = {
        name, subject,
        body_html: html || null,
        body_text: text || null,

        calendar_enabled: isInvite,
        is_calendar_cancellation: isCancel,
        is_calendar_reschedule: isReschedule,

        meeting_uid: (isCancel || isReschedule) ? meetingUid.trim() : null,
        meeting_sequence: (isCancel || isReschedule) ? Number(meetingSequence) : null,

        // Shared calendar properties
        ...sharedCal,

        meeting_provider: (isInvite || isReschedule) ? meetingProvider : 'none',
        meeting_url: (isInvite || isReschedule) && meetingProvider !== 'none' ? ((meetingUrl || '').trim() || null) : null,
        include_all_targets_as_attendees:
          (calMode === 'invite' || calMode === 'reschedule') ? !!includeAllTargets : false,
      }

      let t
      if (edit) t = (await api.put(`/api/templates/${edit.id}`, base)).data
      else t = (await api.post('/api/templates', base)).data

      if (files.length > 0) {
        const fd = new FormData()
        files.forEach((f) => fd.append('files', f))
        await api.post(`/api/templates/${t.id}/attachments`, fd)
        await fetchAttachments(t.id)
        setFiles([])
      }

      for (const id of removeIds) {
        await api.delete(`/api/templates/${t.id}/attachments/${id}`)
      }

      // Upload new selected calendar files
      if (!isCancel && calFiles.length > 0) {
        const fd = new FormData()
        calFiles.forEach(f => fd.append('files', f))
        await api.post(`/api/templates/${t.id}/calendar_attachments`, fd)
        await fetchCalAttachment(t.id)
        setCalFiles([])
        setRemoveCalIds([])
      }

      // Delete marked calendar attachments
      for (const id of removeCalIds) {
        await api.delete(`/api/templates/${t.id}/calendar_attachments/${id}`)
      }

      toast.success('Template saved')
      setShow(false)
      load()
    
    } catch (e) {
      toast.error(prettyErr(e))
    }
  }

  // Variables & completions + Monaco styles
  const VAR_HINTS = ['email', 'firstName', 'lastName', 'extraField', 'randomID']
  const [varNames, setVarNames] = useState(VAR_HINTS)
  const [varMeta, setVarMeta] = useState({})
  const subjectRef = useRef(null)
  const bodyTextRef = useRef(null)
  const locationRef = useRef(null)
  const meetingUrlRef = useRef(null)
  const editorRef = useRef(null)
  const monacoRef = useRef(null)
  const completionDispRef = useRef(null)

  const installHtmlVarCompletions = (monaco, names) => {
    if (completionDispRef.current) { completionDispRef.current.dispose(); completionDispRef.current = null }
    completionDispRef.current = monaco.languages.registerCompletionItemProvider('html', {
      triggerCharacters: ['{', '_', ...'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'.split('')],
      provideCompletionItems: (model, position) => {
        const line = model.getLineContent(position.lineNumber).slice(0, position.column - 1)
        const m = line.match(/\{\{([A-Za-z0-9_]*)$/)
        if (!m) return { suggestions: [] }
        const partial = m[1] || ''
        const startCol = Math.max(1, position.column - partial.length - 2)
        const range = new monaco.Range(position.lineNumber, startCol, position.lineNumber, position.column)
        const suggestions = (names || []).map(name => ({
          label: `{{${name}}}`, kind: monaco.languages.CompletionItemKind.Variable, insertText: `{{${name}}}`, range
        }))
        return { suggestions }
      }
    })
  }

  const loadVars = async () => {
    try {
      const r = await api.get('/api/config/vars')
      const cfgNames = (r.data || []).map(v => v.name).filter(Boolean)
      const cfgMeta = Object.fromEntries(
        (r.data || [])
          .filter(v => v && v.name)
          .map(v => [v.name, { kind: v.kind, per_recipient: !!v.per_recipient }])
      )
      const merged = Array.from(new Set([...VAR_HINTS, ...cfgNames]))
      setVarNames(merged); setVarMeta(cfgMeta)

      const examplesResponse = await api.get('/api/config/vars/preview')
      setVarExamples(examplesResponse.data || {})

    } catch (err) {
      console.error('Failed to load variables', err)
    }
  }

  const replaceVarsInHtml = (html, examples) => {
    if (!html) return ''
    return html.replace(/{{(\w+)}}/g, (match, varName) => {
      return examples[varName] || match
    })
  }

  useEffect(() => { loadVars() }, [])
  useEffect(() => {
    if (monacoRef.current) installHtmlVarCompletions(monacoRef.current, varNames)
    return () => { completionDispRef.current?.dispose(); completionDispRef.current = null }
  }, [varNames])

  const handleEditorDidMount = (editor, monaco) => {
    editorRef.current = editor;
    monacoRef.current = monaco;

    monaco.editor.defineTheme('editor-dark', {
      base: 'vs-dark',
      inherit: true,
      rules: [
        { token: '', foreground: 'E7E7EE' },
        { token: 'comment', foreground: '9AA3B2', fontStyle: 'italic' },

        // HTML
        { token: 'tag', foreground: 'C4B5FD' },
        { token: 'metatag', foreground: 'A78BFA' },
        { token: 'delimiter', foreground: 'A78BFA' },
        { token: 'attribute.name', foreground: '93C5FD' },
        { token: 'attribute.value', foreground: '7DD3FC' },
        { token: 'keyword', foreground: 'A78BFA' },
        { token: 'number', foreground: 'FCA5A5' },
        { token: 'string', foreground: '7DD3FC' },
      ],
      colors: {
        'editor.background': '#00000000',
        'editor.foreground': '#E7E7EE',

        'editor.lineHighlightBackground': '#7C3AED12',
        'editor.selectionBackground': '#7C3AED26',
        'editor.inactiveSelectionBackground': '#7C3AED1A',
        'editor.selectionHighlightBackground': '#7C3AED22',
        'editor.wordHighlightBackground': '#7C3AED22',
        'editor.wordHighlightStrongBackground': '#7C3AED33',

        'editorWarning.foreground': '#A78BFAAA',
        'editorWarning.border': '#0000',
        'editorInfo.foreground': '#93C5FDAA',
        'editorInfo.border': '#0000',
        'editor.findMatchBackground': '#7C3AED44',
        'editor.findMatchHighlightBackground': '#7C3AED26',
        'editorOverviewRuler.findMatchForeground': '#A78BFAAA',

        'editorCursor.foreground': '#EDE9FE',
        'editorWhitespace.foreground': '#A78BFA33',
        'editorIndentGuide.background': '#A78BFA26',
        'editorIndentGuide.activeBackground': '#A78BFA66',
        'editorLineNumber.foreground': '#8B93A6',
        'editorLineNumber.activeForeground': '#E7E7EE',
        'editorGutter.background': '#00000000',
        'editorBracketMatch.background': '#A78BFA33',
        'editorBracketMatch.border': '#A78BFA80',
        'minimap.selectionHighlight': '#7C3AED66',
        'minimap.findMatchHighlight': '#A78BFA99',
        'scrollbarSlider.background': '#A78BFA33',
        'scrollbarSlider.hoverBackground': '#A78BFA55',
        'scrollbarSlider.activeBackground': '#A78BFA77',
      },
    })

    monaco.editor.defineTheme('editor-light', {
      base: 'vs',
      inherit: true,
      rules: [
        { token: '', foreground: '0F172A' },
        { token: 'comment', foreground: '6B7280', fontStyle: 'italic' },

        { token: 'tag', foreground: '7C3AED' },
        { token: 'metatag', foreground: '8B5CF6' },
        { token: 'delimiter', foreground: '8B5CF6' },
        { token: 'attribute.name', foreground: '2563EB' },
        { token: 'attribute.value', foreground: '0EA5E9' },
        { token: 'attribute.value.html', foreground: '0EA5E9' },
        { token: 'keyword', foreground: '7C3AED' },
        { token: 'number', foreground: 'DC2626' },
        { token: 'string', foreground: '0EA5E9' },
      ],
      colors: {
        'editor.background': '#00000000',
        'editor.foreground': '#0F172A',
        'editor.lineHighlightBackground': '#7C3AED0F',
        'editor.selectionBackground': '#7C3AED22',
        'editor.inactiveSelectionBackground': '#7C3AED14',
        'editor.selectionHighlightBackground': '#7C3AED18',
        'editor.wordHighlightBackground': '#7C3AED18',
        'editor.wordHighlightStrongBackground': '#7C3AED26',

        'editorWarning.foreground': '#7C3AEDAA',
        'editorWarning.border': '#0000',
        'editorInfo.foreground': '#2563EB99',
        'editorInfo.border': '#0000',
        'editor.findMatchBackground': '#7C3AED33',
        'editor.findMatchHighlightBackground': '#7C3AED22',
        'editorOverviewRuler.findMatchForeground': '#7C3AED88',

        'editorCursor.foreground': '#6D28D9',
        'editorWhitespace.foreground': '#7C3AED33',
        'editorIndentGuide.background': '#7C3AED26',
        'editorIndentGuide.activeBackground': '#7C3AED66',
        'editorLineNumber.foreground': '#94A3B8',
        'editorLineNumber.activeForeground': '#0F172A',
        'editorGutter.background': '#00000000',
        'editorBracketMatch.background': '#7C3AED26',
        'editorBracketMatch.border': '#7C3AED66',
        'minimap.selectionHighlight': '#7C3AED55',
        'minimap.findMatchHighlight': '#7C3AED88',
        'scrollbarSlider.background': '#7C3AED22',
        'scrollbarSlider.hoverBackground': '#7C3AED44',
        'scrollbarSlider.activeBackground': '#7C3AED66',
      },
    })


    monaco.editor.setTheme(isDark ? 'editor-dark' : 'editor-light');

    monaco.languages.setLanguageConfiguration('html', {
      autoClosingPairs: [
        { open: '<', close: '>' }, { open: '"', close: '"' }, { open: "'", close: "'" },
        { open: '(', close: ')' }, { open: '[', close: ']' }
      ]
    });

    installHtmlVarCompletions(monaco, varNames);
    editor.onDidChangeModelContent((e) => {
      const text = e.changes?.[0]?.text || '';
      if (text.includes('{')) editor.trigger('any', 'editor.action.triggerSuggest', {});
    });
  };

  useEffect(() => {
    if (!editorRef.current || !monacoRef.current) return;
    monacoRef.current.editor.setTheme(isDark ? 'editor-dark' : 'editor-light');
  }, [isDark]);


  const openPreviewNewTab = () => {
    const raw = bodyHtml || ''
    const withVars = replaceVarsInHtml(raw, varExamples)
    const safe = sanitizeEmailHtml(withVars)
    const doc = isFullDocument(withVars) ? injectCspIntoDocument(safe) : makePreviewShell(safe)

    const blob = new Blob([doc], { type: 'text/html' })
    const url = URL.createObjectURL(blob)

    const win = window.open(url, '_blank')
    if (!win) return;

    try { win.opener = null } catch { }

    setTimeout(() => URL.revokeObjectURL(url), 10_000)
  }

  // Template modal stepper
  const [activeStep, setActiveStep] = useState(1)
  const steps = [
    { id: 1, label: 'Main', icon: Info },
    { id: 2, label: 'Calendar', icon: CalendarClock },
    { id: 3, label: 'Body', icon: FileCode },
    { id: 4, label: 'Attachments', icon: Paperclip },
  ]
  const StepBtn = ({ s }) => {
    const Icon = s.icon
    const selected = activeStep === s.id
    const passed = s.id < activeStep
    return (
      <button
        type="button"
        className={[
          'relative flex items-center gap-2 px-3 py-2 rounded-lg transition',
          selected
            ? 'bg-primary/15 text-[var(--mlf-primary)] ring-1 ring-primary/25'
            : 'text-slate-700 dark:text-slate-200 hover:bg-black/5 dark:hover:bg-white/10'
        ].join(' ')}
        onClick={() => setActiveStep(s.id)}
      >
        <Icon size={16} className={selected ? '' : 'opacity-80'} />
        <span className="text-sm font-medium">{s.label}</span>
        {passed && <span className="absolute -bottom-1 left-2 right-2 h-[2px] bg-[var(--mlf-primary)] rounded-full" />}
      </button>
    )
  }

  // Styles
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

  // Select options
  const tzOptions = useMemo(() => {
    const zones = Intl.supportedValuesOf
      ? Intl.supportedValuesOf('timeZone')
      : [browserTz, 'UTC'];
    return zones.map(tz => ({ value: tz, label: tz }));
  }, [browserTz]);

  const priorityOptions = useMemo(
    () => [
      { value: 1, label: '1 (HIGH)' },
      { value: 2, label: '2 (REGULAR)' },
      { value: 3, label: '3 (LOW)' },
    ],
    []
  );

  const providerOptions = useMemo(
    () => [
      { value: 'none', label: 'None' },
      { value: 'teams', label: 'Microsoft Teams' },
      { value: 'gmeet', label: 'Google Meet' },
    ],
    []
  );


  // Attachment helper
  const hasAnyAttachments = (r, { includeCalendarForCancellations = true } = {}) => {
    const norm = (v) => {
      const n = Number(v);
      return Number.isFinite(n) && n > 0 ? n : 0;
    };

    let regular = norm(r?.attachments_count);
    let calendar = norm(r?.calendar_attachments_count);

    // Ignore calendar files on cancellations
    if (r?.is_calendar_cancellation && !includeCalendarForCancellations) {
      calendar = 0;
    }

    return regular + calendar > 0;
  };

  const ProviderPill = ({ provider }) => {
    const p = (provider || 'none').toLowerCase()
    if (p === 'teams') return <KindPill tone="fuchsia" icon={Video}>Teams</KindPill>
    if (p === 'gmeet') return <KindPill tone="fuchsia" icon={Video}>Google Meet</KindPill>
    return null
  }

  // Datatable definitions
  const listColumns = [
    {
      name: 'Name',
      selector: r => r.name,
      sortable: true,
      grow: 3,
      cell: (r) => (
        <div className="flex items-center gap-2 min-w-0">
          <FileText size={16} className="opacity-70 flex-shrink-0" />
          <span title={r.name} className="truncate">{r.name}</span>
        </div>
      )
    },
    {
      name: 'Subject',
      selector: r => r.subject,
      grow: 3,
      cell: (r) => (
        <div className="min-w-0 w-full">
          <span title={r.subject} className="truncate block">{r.subject}</span>
        </div>
      )
    },
    {
      name: 'Attributes',
      grow: 3,
      sortable: false,
      cell: (r) => {
        const hasHtml = !!(r.body_html && r.body_html.trim());
        const hasText = !!(r.body_text && r.body_text.trim());
        const isCancel = !!r.is_calendar_cancellation;
        const isInvite = !!r.calendar_enabled && !isCancel;
        const isReschedule = !!r.is_calendar_reschedule;
        const hasMeetingLink = isInvite && (r.meeting_provider && r.meeting_provider !== 'none');
        const hasAtts = hasAnyAttachments(r);

        return (
          <div className="flex flex-wrap gap-1.5">
            {hasText && <KindPill tone="slate" icon={FileText}>Plain text</KindPill>}
            {hasHtml && <KindPill tone="emerald" icon={Code}>HTML</KindPill>}
            {isInvite && !isReschedule && <KindPill tone="sky" icon={CalendarClock}>Calendar</KindPill>}
            {isReschedule && <KindPill tone="amber" icon={CalendarSync}>Reschedule</KindPill>}
            {isCancel && <KindPill tone="rose" icon={CalendarX2}>Cancellation</KindPill>}
            {hasMeetingLink && <ProviderPill provider={r.meeting_provider} />}
            {hasAtts && <KindPill tone="purple" icon={Paperclip}>Attachments</KindPill>}
          </div>
        );
      }
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
              <Dropdown.Item onClick={() => openEdit(r)}>
                <Pencil size={14} className="me-2" /> Edit
              </Dropdown.Item>
              <Dropdown.Item onClick={() => openDup(r)}>
                <Copy size={14} className="me-2" /> Duplicate
              </Dropdown.Item>
              <Dropdown.Item onClick={() => askDel(r)}>
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

  // Clean body on change
  const setModeClean = (next) => {
    setMode(next);

    if (next === 'html') {
      setBodyText('');
      setShowPreview(true);
    } else if (next === 'text') {
      setBodyHtml('');
      setShowPreview(false);
      try { editorRef.current?.setValue(''); } catch { }
    }
  };

  // Import helpers
  function decodeMimeWord(str = '') {
    return str.replace(/=\?([^?]+)\?([BQbq])\?([^?]+)\?=/g, (_, charset, enc, text) => {
      try {
        const cs = (charset || 'utf-8').toLowerCase();
        const bytes =
          String(enc).toUpperCase() === 'B'
            ? Uint8Array.from(atob(text.replace(/\s/g, '')), c => c.charCodeAt(0))
            : Uint8Array.from(
              (text || '')
                .replace(/_/g, ' ')
                .replace(/=([0-9A-Fa-f]{2})/g, (_, h) => String.fromCharCode(parseInt(h, 16))),
              c => c.charCodeAt(0)
            );
        const td = new TextDecoder(cs, { fatal: false });
        return td.decode(bytes);
      } catch {
        return str;
      }
    });
  }

  function decodeMimeBody(raw = '', headers = {}) {
    const ct = (headers['content-type'] || '').toLowerCase();
    const charsetMatch = ct.match(/charset="?([^";]+)"?/i);
    const charset = charsetMatch ? charsetMatch[1] : 'utf-8';
    const cte = (headers['content-transfer-encoding'] || '').toLowerCase();

    try {
      let bytes;
      if (cte === 'base64') {
        const cleaned = raw.replace(/\s/g, '');
        bytes = Uint8Array.from(atob(cleaned), c => c.charCodeAt(0));
      } else if (cte === 'quoted-printable') {
        const qp = raw.replace(/=\r?\n/g, '').replace(/=([0-9A-Fa-f]{2})/g, (_, h) => String.fromCharCode(parseInt(h, 16)));
        bytes = Uint8Array.from(qp, c => c.charCodeAt(0));
      } else {
        // 7bit/8bit/binary
        bytes = Uint8Array.from(raw, c => c.charCodeAt(0));
      }
      const td = new TextDecoder(charset || 'utf-8', { fatal: false });
      return td.decode(bytes);
    } catch {
      return raw;
    }
  }

  function splitHeadersBody(s = '') {
    const m = s.indexOf('\r\n\r\n');
    const cut = m >= 0 ? m : s.indexOf('\n\n');
    const head = s.slice(0, cut >= 0 ? cut : s.length);
    const body = cut >= 0 ? s.slice(cut + (s[cut] === '\r' ? 4 : 2)) : '';
    const unfolded = head.replace(/\r?\n([ \t]+)/g, ' ');
    const headers = {};
    unfolded.split(/\r?\n/).forEach(line => {
      const i = line.indexOf(':');
      if (i > -1) {
        const key = line.slice(0, i).trim().toLowerCase();
        const val = decodeMimeWord(line.slice(i + 1).trim());
        headers[key] = val;
      }
    });
    return { headers, body };
  }

  function parseMimePart(raw, parentHeaders = {}) {
    const { headers, body } = splitHeadersBody(raw);
    const allHeaders = { ...parentHeaders, ...headers };
    const ctOriginal = allHeaders['content-type'] || '';
    const ct = ctOriginal.toLowerCase();

    if (ct.startsWith('multipart/')) {
      // Extract boundary from ORIGINAL case-sensitive header
      const boundaryMatch = ctOriginal.match(/boundary="?([^";]+)"?/i);
      const boundary = boundaryMatch ? boundaryMatch[1] : null;
      if (!boundary) return { headers: allHeaders, parts: [] };
      
      // Split by boundary delimiters
      const parts = [];
      const lines = body.split(/\r?\n/);
      let currentPart = [];
      let inPart = false;
      
      for (const line of lines) {
        if (line === `--${boundary}` || line.startsWith(`--${boundary} `) || line.startsWith(`--${boundary}\t`)) {
          // Start of a new part
          if (inPart && currentPart.length > 0) {
            parts.push(currentPart.join('\n').trim());
          }
          currentPart = [];
          inPart = true;
        } else if (line === `--${boundary}--` || line.startsWith(`--${boundary}-- `)) {
          // End marker
          if (inPart && currentPart.length > 0) {
            parts.push(currentPart.join('\n').trim());
          }
          break;
        } else if (inPart) {
          currentPart.push(line);
        }
      }
      
      // Don't forget the last part if we didn't hit an end marker
      if (inPart && currentPart.length > 0) {
        parts.push(currentPart.join('\n').trim());
      }
      
      return { headers: allHeaders, parts: parts.filter(p => p).map(p => parseMimePart(p, {})) };
    }

    return {
      headers: allHeaders,
      content: decodeMimeBody(body, allHeaders),
      rawContent: body,
    };
  }

  function collectEmailParts(node, acc = { html: null, text: null, calendars: [], attachments: [] }) {
    if (!node) return acc;
    if (node.parts && node.parts.length) {
      node.parts.forEach(p => collectEmailParts(p, acc));
      return acc;
    }
    const h = node.headers || {};
    const ct = (h['content-type'] || '').toLowerCase();
    const disp = (h['content-disposition'] || '').toLowerCase();
    const nameMatch = h['content-type']?.match(/name="?([^";]+)"?/i);
    const cdNameMatch = h['content-disposition']?.match(/filename="?([^";]+)"?/i);
    const filename = decodeMimeWord(cdNameMatch?.[1] || nameMatch?.[1] || '');

    // Handle text/html body (only if not an attachment)
    if (ct.includes('text/html') && !disp.startsWith('attachment') && !acc.html) {
      acc.html = node.content || '';
      return acc;
    }
    
    // Handle text/plain body (only if not an attachment)
    if (ct.includes('text/plain') && !disp.startsWith('attachment') && !acc.text) {
      acc.text = node.content || '';
      return acc;
    }
    
    // Handle calendar items
    if (ct.includes('text/calendar') || filename.toLowerCase().endsWith('.ics')) {
      acc.calendars.push({ filename: filename || 'invite.ics', content: node.content || '' });
      return acc; // Don't process as attachment
    }
    
    // Handle attachments (including inline images)
    // Attachment if: has disposition (attachment OR inline), or has a filename and is not text body
    const hasDisposition = disp.startsWith('attachment') || disp.startsWith('inline');
    const isLikelyAttachment = !!filename && !ct.includes('text/plain') && !ct.includes('text/html') && !ct.includes('text/calendar');
    
    if (hasDisposition || isLikelyAttachment) {
      acc.attachments.push({
        filename: filename || 'file',
        mime: h['content-type']?.split(';')[0]?.trim() || 'application/octet-stream',
        content: node.rawContent,
        headers: h,
      });
    }
    
    return acc;
  }

  function parseIcs(ics = '') {
    const lines = ics.replace(/\r/g, '').split('\n').reduce((arr, l) => {
      if (/^[ \t]/.test(l) && arr.length) arr[arr.length - 1] += l.slice(1);
      else arr.push(l);
      return arr;
    }, []);

    const data = {};
    const attendees = [];
    let inVevent = false;

    for (const ln of lines) {
      const [left, ...rest] = ln.split(':');
      const value = rest.join(':');
      const [prop, ...paramPairs] = (left || '').split(';');
      const name = (prop || '').toUpperCase();

      if (name === 'BEGIN' && value.toUpperCase() === 'VEVENT') inVevent = true;
      if (name === 'END' && value.toUpperCase() === 'VEVENT') inVevent = false;

      const params = {};
      paramPairs.forEach(p => {
        const [k, v] = p.split('=');
        params[k?.toUpperCase()] = v;
      });

      if (name === 'METHOD') data.METHOD = value.toUpperCase();
      if (name === 'STATUS') {
        if (inVevent) data.VEVENT_STATUS = value.toUpperCase();
        else data.STATUS = value.toUpperCase();
      }
      if (name === 'DTSTART' || name === 'DTEND') {
        const tzid = params['TZID'];
        data[name] = value;
        if (tzid) data.TZID = tzid;
      } else if (name === 'SUMMARY') data.SUMMARY = value;
      else if (name === 'LOCATION') data.LOCATION = value;
      else if (name === 'UID') data.UID = value;
      else if (name === 'SEQUENCE') data.SEQUENCE = value;
      else if (name === 'ORGANIZER') {
        const m = value.match(/mailto:([^;]+)/i);
        data.ORGANIZER_EMAIL = (m && m[1]) || value;
        if (params.CN) data.ORGANIZER_CN = params.CN.replace(/^"|"$/g, '');
      } else if (name === 'ATTENDEE') {
        const m = value.match(/mailto:([^;]+)/i);
        attendees.push({
          email: (m && m[1]) || value,
          cn: (params.CN || '').replace(/^"|"$/g, ''),
        });
      }

      // Extra properties
      else if (name === 'X-MICROSOFT-ISRESPONSEREQUESTED') data.ISRESP = value.toUpperCase()
      else if (name === 'X-MICROSOFT-DONOTFORWARDMEETING') data.DONOTFWD = value.toUpperCase()
      else if (name === 'CLASS') data.CLASS = value.toUpperCase()
      else if (name === 'X-MICROSOFT-SKYPETEAMSMEETINGURL') data.TEAMS = value
      else if (name === 'X-GOOGLE-CONFERENCE') data.GMEET = value
      else if (name === 'CATEGORIES') {
        data.CATEGORIES = (value || '')
          .split(',')
          .map(s => s.trim())
          .filter(Boolean)
      }
      else if (name === 'PRIORITY') data.PRIORITY = value
    }

    data.ATTENDEES = attendees;
    return data;
  }

  function applyIcsToState(data) {
    const method = (data.METHOD || '').toUpperCase()
    const status = (data.VEVENT_STATUS || data.STATUS || '').toUpperCase()
    const seq = Number(data.SEQUENCE ?? '0')

    if (method === 'CANCEL' || status === 'CANCELLED') {
      setModeCancel()
    } else if ((method === 'REQUEST' || !method) && Number.isFinite(seq) && seq > 0) {
      setModeReschedule()
    } else {
      setModeInvite()
    }

    setMeetingSummary(data.SUMMARY || '')
    setOrganizerCn(data.ORGANIZER_CN || '')
    setOrganizerEmail(data.ORGANIZER_EMAIL || '')
    setMeetingBeginLocal(icsStampToLocalInput(data.DTSTART || ''))
    setMeetingEndLocal(icsStampToLocalInput(data.DTEND || ''))
    setMeetingTz(
      data.TZID || (/(Z)$/.test(data.DTSTART || '') ? 'UTC' : meetingTz)
    );
    setLocation(data.LOCATION || '')

    if (Array.isArray(data.ATTENDEES) && data.ATTENDEES.length) {
      setAttendees(data.ATTENDEES.map(a => ({ cn: a.cn || '', email: a.email || '' })))
    }
    if (data.UID) setMeetingUid(String(data.UID))
    if (data.SEQUENCE != null) setMeetingSequence(String(data.SEQUENCE))

    // Allow responses
    if (typeof data.ISRESP === 'string') {
      const v = data.ISRESP === 'TRUE' ? true : data.ISRESP === 'FALSE' ? false : undefined;
      if (v !== undefined) setAllowResponses(v)
    }

    // Disable forwarding
    if (typeof data.DONOTFWD === 'string') {
      setDisableForwarding(data.DONOTFWD === 'TRUE')
    }

    // Private meeting
    if ((data.CLASS || '') === 'PRIVATE') {
      setIsPrivate(true)
    }

    // Meeting provider & url
    if (data.TEAMS) {
      setMeetingProvider('teams')
      setMeetingUrl(data.TEAMS)
    } else if (data.GMEET) {
      setMeetingProvider('gmeet')
      setMeetingUrl(data.GMEET)
    } else {
      setMeetingProvider('none')
      setMeetingUrl('')
    }

    // Categories
    if (Array.isArray(data.CATEGORIES)) {
      const dedup = Array.from(new Set(data.CATEGORIES));
      setCategories(dedup);
    }

    // Priority mapping
    const pNum = Number(data.PRIORITY);
    if (Number.isFinite(pNum)) {
      if (pNum <= 2) {
        setCalendarPriority(3) // LOW
      } else if (pNum >= 6) {
        setCalendarPriority(1) // HIGH
      } else if (pNum > 2 && pNum < 6) {
        setCalendarPriority(2) // REGULAR
      }
    }
  }

  function icsStampToLocalInput(s = '') {
    if (!s) return '';
    if (/\d{8}T\d{6}Z$/.test(s)) {
      // UTC to local input
      const d = new Date(s.replace(/Z$/, 'Z'));
      const y = d.getFullYear();
      const m = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      const H = String(d.getHours()).padStart(2, '0');
      const Mi = String(d.getMinutes()).padStart(2, '0');
      return `${y}-${m}-${day}T${H}:${Mi}`;
    }

    const m = s.match(/^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})/);
    if (!m) return '';
    return `${m[1]}-${m[2]}-${m[3]}T${m[4]}:${m[5]}`;
  }

  function attachmentToFile(att) {
    try {
      const cte = (att.headers['content-transfer-encoding'] || '').toLowerCase().trim();
      const ct = (att.headers['content-type'] || '').toLowerCase();
      
      let bytes;
      
      if (cte === 'base64') {
        // For base64 encoded attachments, decode directly to binary
        const cleaned = att.content.replace(/\s/g, '');
        const binaryString = atob(cleaned);
        bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
          bytes[i] = binaryString.charCodeAt(i);
        }
      } else if (cte === 'quoted-printable') {
        // For quoted-printable, decode to text first then to bytes
        const decoded = decodeMimeBody(att.content, att.headers);
        bytes = new Uint8Array(decoded.length);
        for (let i = 0; i < decoded.length; i++) {
          bytes[i] = decoded.charCodeAt(i);
        }
      } else {
        // For 7bit, 8bit, binary or no encoding
        // If it looks like text, decode with charset, otherwise use raw bytes
        if (ct.includes('text/')) {
          const decoded = decodeMimeBody(att.content, att.headers);
          bytes = new Uint8Array(decoded.length);
          for (let i = 0; i < decoded.length; i++) {
            bytes[i] = decoded.charCodeAt(i);
          }
        } else {
          // Binary content without encoding
          bytes = new Uint8Array(att.content.length);
          for (let i = 0; i < att.content.length; i++) {
            bytes[i] = att.content.charCodeAt(i) & 0xff;
          }
        }
      }
      
      return new File([bytes], att.filename, { type: att.mime || 'application/octet-stream' });
    } catch (err) {
      console.error('Failed to convert attachment:', err);
      return null;
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-slate-900 dark:text-white">Templates</h1>

      <div className="rounded-2xl ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-glass/80 shadow-card p-2">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative flex-1 min-w-[280px]">
            <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 opacity-70" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search templates by name or subject"
              className={inputClsSearchbar}
              style={{ paddingLeft: '2.75rem' }}
            />
          </div>
          <div className="ml-auto">
            <OverlayTrigger placement="top" overlay={<Tooltip>Create template</Tooltip>}>
              <button
                onClick={openCreate}
                className="rail-btn ring-1 ring-black/10 dark:ring-0 bg-white/80 dark:bg-white/5 hover:bg-white/90 dark:hover:bg-white/10 text-[var(--mlf-primary)]"
                aria-label="Create template"
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
          noDataComponent={<div className="p-4 text-sm text-slate-600 dark:text-slate-300">No templates found.</div>}
        />
      </div>

      {/* Create/edit modal */}
      <Modal show={show} onHide={() => setShow(false)} centered size="xl" contentClassName="modal-matte" backdrop="static" keyboard={false}>
        <Modal.Header closeButton className="border-0 pt-4 px-4">
          <Modal.Title>{edit ? 'Edit Template' : 'Create Template'}</Modal.Title>
        </Modal.Header>

        <Modal.Body className="px-4 pt-2 pb-4">
          {/* Stepper */}
          <div className="mb-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap gap-2">
                {[
                  { id: 1, label: 'Main', icon: Info },
                  { id: 2, label: 'Calendar', icon: CalendarClock },
                  { id: 3, label: 'Body', icon: FileCode },
                  { id: 4, label: 'Attachments', icon: Paperclip },
                ].map(s => {
                  const Icon = s.icon
                  const selected = activeStep === s.id
                  const passed = s.id < activeStep
                  return (
                    <button
                      key={s.id}
                      type="button"
                      className={[
                        'relative flex items-center gap-2 px-3 py-2 rounded-lg transition',
                        selected
                          ? 'bg-primary/15 text-[var(--mlf-primary)] ring-1 ring-primary/25'
                          : 'text-slate-700 dark:text-slate-200 hover:bg-black/5 dark:hover:bg-white/10'
                      ].join(' ')}
                      onClick={() => setActiveStep(s.id)}
                    >
                      <Icon size={16} className={selected ? '' : 'opacity-80'} />
                      <span className="text-sm font-medium">{s.label}</span>
                      {passed && <span className="absolute -bottom-1 left-2 right-2 h-[2px] bg-[var(--mlf-primary)] rounded-full" />}
                    </button>
                  )
                })}
              </div>

              {/* Import template */}
              <div className="ml-auto">
                <input
                  id="import-eml"
                  type="file"
                  accept=".eml,.ics"
                  className="hidden"
                  onChange={async (e) => {
                    const file = e.target.files?.[0]
                    e.target.value = ''
                    if (!file) return
                    try {
                      if (file.name.toLowerCase().endsWith('.ics')) {
                        const ics = await file.text()
                        const data = parseIcs(ics)
                        applyIcsToState(data)
                        toast.success('Imported calendar from ICS')
                        setActiveStep(2); // Jump to calendar step
                        return;
                      }

                      // Eml
                      const raw = await file.text()
                      const root = parseMimePart(raw)
                      const acc = collectEmailParts(root)

                      // Extract Subject from email headers
                      if (root.headers && root.headers['subject']) {
                        setSubject(root.headers['subject'])
                      }

                      // Bodies
                      const html = (acc.html || '').trim()
                      const text = (acc.text || '').trim()
                      
                      if (html && text) {
                        setMode('both')
                        setBodyHtml(html)
                        setBodyText(text)

                      } else if (html) {
                        setMode('html')
                        setBodyHtml(html)
                        setBodyText('')
                      
                      } else if (text) {
                        setMode('text')
                        setBodyHtml('')
                        setBodyText(text)
                      }

                      // Calendar fields
                      if (acc.calendars && acc.calendars.length) {
                        const first = acc.calendars[0]
                        const data = parseIcs(first.content || '')
                        applyIcsToState(data)
                      }

                      // Reg attachments
                      if (acc.attachments && acc.attachments.length) {
                        const asFiles = acc.attachments
                          .filter(a => !(a.filename || '').toLowerCase().endsWith('.ics') && !(a.headers['content-type'] || '').toLowerCase().includes('text/calendar'))
                          .map(attachmentToFile)
                          .filter(Boolean)
                        if (asFiles.length) setFiles(prev => [...prev, ...asFiles])
                      }

                      toast.success('Imported from EML')
                      setActiveStep(3) // Jump to body
                    } catch (err) {
                      console.error(err);
                      toast.error('Could not import template')
                    }
                  }}
                />
                <OverlayTrigger placement="top" overlay={<Tooltip>Import template</Tooltip>}>
                  <button
                    type="button"
                    onClick={() => document.getElementById('import-eml')?.click()}
                    className="inline-flex items-center gap-2 px-3 py-2 rounded-xl
                              bg-white/80 dark:bg-white/5 hover:bg-white/90 dark:hover:bg-white/10
                              ring-1 ring-black/10 dark:ring-white/10 text-sm"
                  >
                    <Upload size={16} />
                    <span className="font-medium">Import</span>
                  </button>
                </OverlayTrigger>
              </div>
            </div>
          </div>


          {/* Step 1: Main */}
          {activeStep === 1 && (
            <div className="space-y-4">
              <div>
                <FieldLabel required>Template name</FieldLabel>
                <input className={inputCls} placeholder="Name" value={name} onChange={e => setName(e.target.value)} />
              </div>
              <div>
                <FieldLabel required acceptsVars>Subject</FieldLabel>
                <div className="relative">
                  <input
                    ref={subjectRef}
                    className={inputCls}
                    placeholder="Email subject"
                    value={subject}
                    onChange={e => setSubject(e.target.value)}
                  />
                  <VarAutocomplete targetRef={subjectRef} variables={varNames} onInsert={setSubject} />
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Calendar */}
          {activeStep === 2 && (
            <div className="space-y-5">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold">Calendar meeting</span>

                <div className="inline-flex rounded-xl bg-white/80 dark:bg-white/5 ring-1 ring-black/10 dark:ring-white/10 p-1">
                  <button
                    type="button"
                    onClick={setModeOff}
                    className={[
                      'px-3 py-1.5 rounded-lg text-sm transition',
                      calMode === 'off'
                        ? 'bg-primary/15 text-[var(--mlf-primary)] ring-1 ring-primary/25'
                        : 'text-slate-700 dark:text-slate-200 hover:bg-black/5 dark:hover:bg-white/10'
                    ].join(' ')}
                  >
                    Off
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      // Prefill times (start +30mins from current time, end +1h)
                      if (!meetingBeginLocal) {
                        const now = new Date(); now.setSeconds(0, 0)
                        const d = new Date(now.getTime() + 30 * 60 * 1000)
                        const y = d.getFullYear(), m = String(d.getMonth() + 1).padStart(2, '0'), day = String(d.getDate()).padStart(2, '0')
                        const H = String(d.getHours()).padStart(2, '0'), Mi = String(d.getMinutes()).padStart(2, '0')
                        setMeetingBeginLocal(`${y}-${m}-${day}T${H}:${Mi}`)
                      }
                      if (!meetingEndLocal) {
                        const now2 = new Date(); now2.setSeconds(0, 0)
                        const d2 = new Date(now2.getTime() + 60 * 60 * 1000)
                        const y2 = d2.getFullYear(), m2 = String(d2.getMonth() + 1).padStart(2, '0'), day2 = String(d2.getDate()).padStart(2, '0')
                        const H2 = String(d2.getHours()).padStart(2, '0'), Mi2 = String(d2.getMinutes()).padStart(2, '0')
                        setMeetingEndLocal(`${y2}-${m2}-${day2}T${H2}:${Mi2}`)
                      }
                      setModeInvite()
                    }}
                    className={[
                      'px-3 py-1.5 rounded-lg text-sm transition',
                      calMode === 'invite'
                        ? 'bg-primary/15 text-[var(--mlf-primary)] ring-1 ring-primary/25'
                        : 'text-slate-700 dark:text-slate-200 hover:bg-black/5 dark:hover:bg-white/10'
                    ].join(' ')}
                  >
                    Invite
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      // Prefill times if empty
                      if (!meetingBeginLocal || !meetingEndLocal) {
                        const now = new Date(); now.setSeconds(0, 0)
                        const d1 = new Date(now.getTime() + 30 * 60 * 1000)
                        const d2 = new Date(now.getTime() + 60 * 60 * 1000)
                        const toInput = (d) => {
                          const y = d.getFullYear(), m = String(d.getMonth() + 1).padStart(2, '0'), day = String(d.getDate()).padStart(2, '0')
                          const H = String(d.getHours()).padStart(2, '0'), Mi = String(d.getMinutes()).padStart(2, '0')
                          return `${y}-${m}-${day}T${H}:${Mi}`
                        };
                        if (!meetingBeginLocal) setMeetingBeginLocal(toInput(d1))
                        if (!meetingEndLocal) setMeetingEndLocal(toInput(d2))
                      }
                      setModeReschedule();
                    }}
                    className={[
                      'px-3 py-1.5 rounded-lg text-sm transition',
                      calMode === 'reschedule'
                        ? 'bg-primary/15 text-[var(--mlf-primary)] ring-1 ring-primary/25'
                        : 'text-slate-700 dark:text-slate-200 hover:bg-black/5 dark:hover:bg-white/10'
                    ].join(' ')}
                  >
                    Reschedule
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      if (!meetingBeginLocal || !meetingEndLocal) {
                        const now = new Date(); now.setSeconds(0, 0)
                        const d1 = new Date(now.getTime() + 30 * 60 * 1000)
                        const d2 = new Date(now.getTime() + 60 * 60 * 1000)
                        const toInput = (d) => {
                          const y = d.getFullYear(), m = String(d.getMonth() + 1).padStart(2, '0'), day = String(d.getDate()).padStart(2, '0')
                          const H = String(d.getHours()).padStart(2, '0'), Mi = String(d.getMinutes()).padStart(2, '0')
                          return `${y}-${m}-${day}T${H}:${Mi}`
                        }
                        if (!meetingBeginLocal) setMeetingBeginLocal(toInput(d1))
                        if (!meetingEndLocal) setMeetingEndLocal(toInput(d2))
                      }
                      setModeCancel()
                    }}
                    className={[
                      'px-3 py-1.5 rounded-lg text-sm transition',
                      calMode === 'cancel'
                        ? 'bg-primary/15 text-[var(--mlf-primary)] ring-1 ring-primary/25'
                        : 'text-slate-700 dark:text-slate-200 hover:bg-black/5 dark:hover:bg-white/10'
                    ].join(' ')}
                  >
                    Cancellation
                  </button>
                </div>
              </div>

              {calMode !== 'off' && (
                <>
                  <div className="rounded-xl ring-1 ring-black/10 dark:ring-white/10 bg-white/70 dark:bg-white/5 p-3">
                    <TitleWithLabel title="Meeting summary" icon={FileText} required={true} acceptsVars={false} />
                    <input className={inputCls} value={meetingSummary} placeholder="Summary" onChange={e => setMeetingSummary(e.target.value)} />
                  </div>

                  {calMode === 'cancel' && (
                    <div className="rounded-xl ring-1 ring-black/10 dark:ring-white/10 bg-white/70 dark:bg-white/5 p-3">
                      <TitleWithLabel title="Cancellation details" icon={Clock} required={true} />
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        <div className="md:col-span-2">
                          <FieldLabel>Meeting UID</FieldLabel>
                          <input
                            className={inputCls}
                            placeholder="UID of the original meeting"
                            value={meetingUid}
                            onChange={(e) => setMeetingUid(e.target.value)}
                          />
                        </div>
                        <div>
                          <FieldLabel>Sequence</FieldLabel>
                          <input
                            className={inputCls}
                            type="number"
                            min={0}
                            step={1}
                            placeholder="e.g. 1"
                            value={meetingSequence}
                            onChange={(e) => setMeetingSequence(e.target.value)}
                          />
                        </div>
                      </div>
                      <div className="form-text mt-2">
                        Use the same <code>UID</code> as the original meeting and a higher <code>SEQUENCE</code>.
                      </div>
                    </div>
                  )}

                  {calMode === 'reschedule' && (
                    <div className="rounded-xl ring-1 ring-black/10 dark:ring-white/10 bg-white/70 dark:bg-white/5 p-3">
                      <TitleWithLabel title="Reschedule details" icon={Clock} required={true} />
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        <div className="md:col-span-2">
                          <FieldLabel>Meeting UID</FieldLabel>
                          <input
                            className={inputCls}
                            placeholder="UID of the original meeting"
                            value={meetingUid}
                            onChange={(e) => setMeetingUid(e.target.value)}
                          />
                        </div>
                        <div>
                          <FieldLabel>Sequence</FieldLabel>
                          <input
                            className={inputCls}
                            type="number"
                            min={0}
                            step={1}
                            placeholder="e.g. 2"
                            value={meetingSequence}
                            onChange={(e) => setMeetingSequence(e.target.value)}
                          />
                        </div>
                      </div>
                      <div className="form-text mt-2">
                        Use the same <code>UID</code> as the original meeting and a higher <code>SEQUENCE</code>.
                      </div>
                    </div>
                  )}

                  <div className="rounded-xl ring-1 ring-black/10 dark:ring-white/10 bg-white/70 dark:bg-white/5 p-3">
                    <TitleWithLabel title="Timezone & Time" icon={Globe} required={true} acceptsVars={false} />
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      <div>
                        <FieldLabel>Timezone</FieldLabel>
                        <ThemedSelect options={tzOptions} value={meetingTz} onChange={setMeetingTz} placeholder="Timezone" />
                        <div className="form-text">Your machine's timezone is <code>{browserTz || '—'}</code></div>
                      </div>
                      <div>
                        <FieldLabel><Clock size={14} className="inline -mt-0.5 me-1" /> Start</FieldLabel>
                        <input type="datetime-local" className={inputCls} value={meetingBeginLocal} onChange={e => setMeetingBeginLocal(e.target.value)} />
                        <div className="form-text">Sends as <code>{inputToIcs(meetingBeginLocal) || '—'}</code> in <code>{meetingTz}</code></div>
                      </div>
                      <div>
                        <FieldLabel><Clock size={14} className="inline -mt-0.5 me-1" /> End</FieldLabel>
                        <input type="datetime-local" className={inputCls} value={meetingEndLocal} onChange={e => setMeetingEndLocal(e.target.value)} />
                        <div className="form-text">Sends as <code>{inputToIcs(meetingEndLocal) || '—'}</code> in <code>{meetingTz}</code></div>
                      </div>
                    </div>
                  </div>

                  <div className="rounded-xl ring-1 ring-black/10 dark:ring-white/10 bg-white/70 dark:bg-white/5 p-3">
                    <TitleWithLabel title="Organizer" icon={User} required={true} acceptsVars={false} />
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <input className={inputCls} placeholder="Organizer CN" value={organizerCn} onChange={e => setOrganizerCn(e.target.value)} />
                      <input className={inputCls} placeholder="Organizer email" value={organizerEmail} onChange={e => setOrganizerEmail(e.target.value)} />
                    </div>
                  </div>

                  <div className="rounded-xl ring-1 ring-black/10 dark:ring-white/10 bg-white/70 dark:bg-white/5 p-3">
                    <div className="flex items-center justify-between mb-2">
                      <TitleWithLabel title="Attendees" icon={Users} required={false} acceptsVars={false} />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-[1fr_1fr_auto] gap-3 items-center mb-3">
                      <input className={inputCls} placeholder="Attendee CN" value={newAttCN} onChange={e => setNewAttCN(e.target.value)} />
                      <input className={inputCls} placeholder="Attendee Email" value={newAttEmail} onChange={e => setNewAttEmail(e.target.value)} />
                      <TemplateIconBtn icon={Plus} title="Add attendee" onClick={addAtt} className="w-10 h-10 rounded-lg flex items-center justify-center bg-slate-100 hover:bg-slate-200 dark:bg-slate-700 dark:hover:bg-slate-600" />
                    </div>

                    {attendees.length === 0 ? (
                      <div className="text-sm text-slate-500 dark:text-slate-300">No attendees added.</div>
                    ) : (
                      <div className="space-y-2" style={{ marginRight: '3.25rem' }}>
                        {attendees.map((a, i) => (
                          <div key={i} className="flex items-center justify-between rounded-lg px-3 py-2 ring-1 ring-black/10 dark:ring-white/10 bg-white/60 dark:bg-white/5">
                            <div className="min-w-0">
                              <div className="text-sm font-medium truncate">{a.cn || '—'}</div>
                              <div className="text-xs text-slate-600 dark:text-slate-300 truncate">{a.email || '—'}</div>
                            </div>
                            <TemplateIconBtn icon={Trash2} title="Remove attendee" onClick={() => delAtt(i)} />
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Other settings */}
                  <div className="rounded-xl ring-1 ring-black/10 dark:ring-white/10 bg-white/70 dark:bg-white/5 p-3">
                    <div className="flex items-center gap-2 mb-3">
                      <TitleWithLabel title="Other settings" icon={Settings} required={false} acceptsVars={false} />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                      <div className="md:col-span-2">
                        <FieldLabel acceptsVars>Location</FieldLabel>
                        <input ref={locationRef} className={inputCls} value={location} onChange={e => setLocation(e.target.value)} placeholder="e.g. Boardroom A or 123 Main St." />
                        <VarAutocomplete targetRef={locationRef} variables={varNames} onInsert={setLocation} />
                      </div>

                      <div className="md:col-span-2">
                        <FieldLabel>Priority</FieldLabel>
                        <ThemedSelect options={priorityOptions} value={calendarPriority} searchable={false} onChange={(v) => setCalendarPriority(Number(v))} placeholder="Priority" />
                      </div>

                      <CategoriesInput categories={categories} setCategories={setCategories} inputCls={inputCls} />
                      {(calMode === 'invite' || calMode === 'reschedule') && (
                        <div className="col-span-full">
                          <FieldLabel>Meeting options</FieldLabel>

                          <div className="w-full grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-1">
                            <div className="check-accent form-check m-0 flex items-center w-full">
                              <input
                                className="form-check-input me-2"
                                type="checkbox"
                                id="allowResponses"
                                checked={allowResponses}
                                onChange={e => setAllowResponses(e.target.checked)}
                              />
                              <label className="form-check-label" htmlFor="allowResponses">Allow responses</label>
                            </div>

                            <div className="check-accent form-check m-0 flex items-center w-full">
                              <input
                                className="form-check-input me-2"
                                type="checkbox"
                                id="dfw"
                                checked={disableForwarding}
                                onChange={e => setDisableForwarding(e.target.checked)}
                              />
                              <label className="form-check-label" htmlFor="dfw">Disable forwarding</label>
                            </div>

                            <div className="check-accent form-check m-0 flex items-center w-full">
                              <input
                                id="privateCheck"
                                type="checkbox"
                                className="form-check-input me-2"
                                checked={!!isPrivate}
                                onChange={(e) => setIsPrivate(e.target.checked ? true : null)}
                              />
                              <label htmlFor="privateCheck" className="form-check-label">Private meeting</label>
                            </div>

                            <div className="check-accent form-check m-0 flex items-center w-full">
                              <input
                                className="form-check-input me-2"
                                type="checkbox"
                                id="includeAllTargets"
                                checked={includeAllTargets}
                                onChange={(e) => setIncludeAllTargets(e.target.checked)}
                              />
                              <label className="form-check-label" htmlFor="includeAllTargets">
                                Include all campaign targets as attendees
                              </label>
                            </div>

                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Meeting provider & URL */}
                  {(calMode === 'invite' || calMode === 'reschedule') && (
                  <div className="rounded-xl ring-1 ring-black/10 dark:ring-white/10 bg-white/70 dark:bg-white/5 p-3">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <TitleWithLabel title="Meeting link" icon={Video} required={false} acceptsVars={false} />
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      <div>
                        <FieldLabel>Provider</FieldLabel>
                        <ThemedSelect options={providerOptions} searchable={false} value={meetingProvider} onChange={setMeetingProvider} />
                      </div>

                      {/* URL only when provider selected */}
                      <div className="md:col-span-2">
                        <FieldLabel acceptsVars>Meeting URL</FieldLabel>
                        <div className="relative">
                          <input
                            className={inputCls}
                            ref={meetingUrlRef}
                            value={meetingUrl}
                            onChange={e => setMeetingUrl(e.target.value)}
                            placeholder={
                              meetingProvider === 'teams'
                                ? 'https://teams.microsoft.com/l/meetup-join/...'
                                : meetingProvider === 'gmeet'
                                  ? 'https://meet.google.com/xxx-xxxx-xxx'
                                  : 'Disabled'
                            }
                            disabled={meetingProvider === 'none'}
                          />
                          {meetingProvider !== 'none' && (
                            <VarAutocomplete targetRef={meetingUrlRef} variables={varNames} onInsert={setMeetingUrl} />
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                  )}

                  {/* Calendar attachments */}
                  {(calMode === 'invite' || calMode === 'reschedule') && (
                    <div className="rounded-xl ring-1 ring-black/10 dark:ring-white/10 bg-white/70 dark:bg-white/5 p-3">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-semibold flex items-center gap-2">
                          <Paperclip size={16} /> Calendar attachments
                        </span>
                        <FilePicker id="cal-files" multiple accept="*/*" onChange={(arr) => setCalFiles(arr)} label="Choose files" />
                      </div>

                      <UnifiedAttachments
                        existing={existingCalAtt}
                        newFiles={calFiles}
                        removedExistingIds={removeCalIds}
                        onToggleExisting={(id) =>
                          setRemoveCalIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])
                        }
                        onRemoveNew={(i) => {
                          const next = [...calFiles]; next.splice(i, 1); setCalFiles(next)
                        }}
                      />
                    </div>
                  )}

                </>
              )}
            </div>
          )}

          {/* Step 3: Body */}
          {activeStep === 3 && (
            <div className="space-y-4">
              <div className="inline-flex rounded-xl bg-white/80 dark:bg-white/5 ring-1 ring-black/10 dark:ring-white/10 p-1">
                <button
                  onClick={() => setModeClean('both')}
                  className={[
                    'px-3 py-2 rounded-lg text-sm transition',
                    mode === 'both'
                      ? 'bg-primary/15 text-[var(--mlf-primary)] ring-1 ring-primary/25'
                      : 'text-slate-700 dark:text-slate-200 hover:bg-black/5 dark:hover:bg-white/10'
                  ].join(' ')}
                >
                  Both
                </button>
                <button
                  onClick={() => setModeClean('html')}
                  className={[
                    'px-3 py-2 rounded-lg text-sm transition',
                    mode === 'html'
                      ? 'bg-primary/15 text-[var(--mlf-primary)] ring-1 ring-primary/25'
                      : 'text-slate-700 dark:text-slate-200 hover:bg-black/5 dark:hover:bg-white/10'
                  ].join(' ')}
                >
                  HTML only
                </button>
                <button
                  onClick={() => setModeClean('text')}
                  className={[
                    'px-3 py-2 rounded-lg text-sm transition',
                    mode === 'text'
                      ? 'bg-primary/15 text-[var(--mlf-primary)] ring-1 ring-primary/25'
                      : 'text-slate-700 dark:text-slate-200 hover:bg-black/5 dark:hover:bg-white/10'
                  ].join(' ')}
                >
                  Text only
                </button>
              </div>

              {/* HTML editor */}
              {mode !== 'text' && (
                <div className="rounded-2xl ring-1 ring-black/10 dark:ring-white/10 bg-white/80 dark:bg-white/5 overflow-hidden">
                  <WindowChrome
                    title="HTML Body"
                    right={
                      <>
                        <IconChromeButton
                          title={splitView ? 'Single view' : 'Split view'}
                          onClick={() => {
                            setSplitView(v => !v)
                            setActivePane('editor')
                          }}
                        >
                          <Columns size={15} />
                        </IconChromeButton>
                        <IconChromeButton
                          title="Open preview in a new tab"
                          onClick={openPreviewNewTab}
                        >
                          <ExternalLink size={15} />
                        </IconChromeButton>
                      </>
                    }
                  />

                  <VSTabs
                    active={activePane}
                    showPreviewTab={true}
                    splitView={splitView}
                    onSelect={(which) => setActivePane(which)}
                  />

                  <div className={splitView ? 'flex gap-0 transition-all duration-300' : 'block transition-all duration-300'}>
                    {/* Editor */}
                    <div
                      className={[
                        splitView ? 'w-1/2' : 'w-full',
                        splitView ? 'p-2' : (activePane === 'editor' ? 'p-2' : 'p-0'),
                        'transition-all duration-300',
                        !splitView && activePane !== 'editor'
                          ? 'opacity-0 scale-[.98] pointer-events-none h-0 overflow-hidden'
                          : 'opacity-100 scale-100'
                      ].join(' ')}
                    >
                      <div className="rounded-xl overflow-hidden ring-1 ring-black/10 dark:ring-white/10 bg-white/95 dark:bg-[#0b1220]/85">
                        <Editor
                          onMount={handleEditorDidMount}
                          height={splitView ? '520px' : '560px'}
                          defaultLanguage="html"
                          value={bodyHtml}
                          onChange={(v) => setBodyHtml(v ?? '')}
                          theme={isDark ? 'editor-dark' : 'editor-light'}
                          options={{
                            automaticLayout: true,
                            minimap: { enabled: false },
                            scrollBeyondLastLine: false,
                            fontSize: 13,
                            roundedSelection: true,
                            wordWrap: 'on',
                            padding: { top: 14, bottom: 14 },
                            lineDecorationsWidth: 8,
                            lineNumbersMinChars: 3,
                            bracketPairColorization: { enabled: true },
                            guides: { indentation: true, bracketPairs: true },
                            renderLineHighlight: 'all',
                            tabSize: 2,
                          }}
                        />
                      </div>
                    </div>

                    {/* Preview */}
                    <div
                      className={[
                        splitView ? 'w-1/2' : 'w-full',
                        splitView ? 'p-2' : (activePane === 'preview' ? 'p-2' : 'p-0'),
                        splitView ? 'md:border-l' : '',
                        'border-black/10 dark:border-white/10 transition-all duration-300',
                        !splitView && activePane !== 'preview'
                          ? 'opacity-0 scale-[.98] pointer-events-none h-0 overflow-hidden'
                          : 'opacity-100 scale-100'
                      ].join(' ')}
                    >
                      <div className="rounded-xl overflow-hidden ring-1 ring-black/10 dark:ring-white/10 bg-white">
                        {(() => {
                          const raw = bodyHtml || ''
                          const withVars = replaceVarsInHtml(raw, varExamples)
                          const safe = sanitizeEmailHtml(withVars)
                          const srcDoc = isFullDocument(withVars) ? injectCspIntoDocument(safe) : makePreviewShell(safe)
                          return (
                            <iframe
                              ref={previewRef}
                              key={bodyHtml + JSON.stringify(varExamples)}
                              title="preview"
                              className="w-100"
                              style={{ height: splitView ? 520 : 560, background: '#fff', border: 0 }}
                              sandbox="allow-popups allow-popups-to-escape-sandbox"
                              referrerPolicy="no-referrer"
                              srcDoc={srcDoc}
                            />
                          )
                        })()}
                      </div>
                    </div>
                  </div>

                </div>
              )}

              {/* Plain-text editor */}
              {mode !== 'html' && (
                <div className="rounded-2xl ring-1 ring-black/10 dark:ring-white/10 bg-white/80 dark:bg-white/5 overflow-hidden">
                  <WindowChrome title="Plain-text Body" right={null} />
                  <VSTabs active="editor" showPreviewTab={false} htmlBanner={false} onSelect={() => { }} />
                  <div className="p-2">
                    <div className="relative">
                      <textarea
                        ref={bodyTextRef}
                        className={`${inputCls} !py-3 rounded-xl ring-1 ring-black/10 dark:ring-white/10
                                    bg-white/95 dark:bg-[#0b1220]/85`}
                        rows={12}
                        value={bodyText}
                        onChange={e => setBodyText(e.target.value)}
                      />
                      <VarAutocomplete targetRef={bodyTextRef} variables={varNames} onInsert={setBodyText} />
                    </div>
                  </div>
                </div>
              )}

            </div>
          )}

          {/* Step 4: Attachments */}
          {activeStep === 4 && (
            <div className="space-y-5">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold">Attachments</span>
                <FilePicker id="att-files" multiple onChange={(arr) => setFiles(arr)} label="Choose files" />
              </div>

              <UnifiedAttachments
                existing={existingAtts}
                newFiles={files}
                removedExistingIds={removeIds}
                onToggleExisting={(id) => toggleRemove(id)}
                onRemoveNew={(i) => {
                  const next = [...files]; next.splice(i, 1); setFiles(next)
                }}
              />
            </div>
          )}

          {/* Legend */}
          <div className="mt-5 text-xs text-slate-500 dark:text-slate-400">
            <span className="me-4"><sup className="text-[var(--mlf-primary)]">*</sup> Required</span>
            <span className="inline-flex items-center gap-1"><sup><Braces size={12} className="text-[var(--mlf-primary)]" /></sup> Accepts variables</span>
          </div>
        </Modal.Body>

        {/* Footer */}
        <Modal.Footer className="border-0 pt-0 px-4 pb-4 justify-end">
          <Button variant="secondary" onClick={() => setShow(false)} className="me-2">Cancel</Button>
          {activeStep > 1 && (
            <Button variant="secondary" onClick={() => setActiveStep(s => Math.max(1, s - 1))} className="me-2">
              Back
            </Button>
          )}
          {activeStep < 4 ? (
            <Button variant="primary" onClick={() => setActiveStep(s => Math.min(4, s + 1))}>
              Next
            </Button>
          ) : (
            <OverlayTrigger placement="top" overlay={<Tooltip>Save template</Tooltip>}>
              <span>
                <Button variant="primary" onClick={save} disabled={!name.trim() || !subject.trim()}>
                  Save
                </Button>
              </span>
            </OverlayTrigger>
          )}
        </Modal.Footer>
      </Modal>

      {/* Duplicate modal */}
      <Modal show={showDup} onHide={() => setShowDup(false)} centered contentClassName="modal-matte">
        <Modal.Header closeButton><Modal.Title>Duplicate Template</Modal.Title></Modal.Header>
        <Modal.Body>
          <Form.Control placeholder="New template name" value={dupName} onChange={e => setDupName(e.target.value)} />
        </Modal.Body>
        <Modal.Footer className="border-0 pt-0">
          <Button variant="secondary" onClick={() => setShowDup(false)}>Cancel</Button>
          <Button variant="primary" onClick={doDup} disabled={!dupName.trim()}>Create Copy</Button>
        </Modal.Footer>
      </Modal>

      {/* Confirm delete */}
      <Modal show={showDel} onHide={() => setShowDel(false)} centered contentClassName="modal-matte">
        <Modal.Header closeButton className="border-0 pb-0"><Modal.Title>Delete Template</Modal.Title></Modal.Header>
        <Modal.Body>
          <div className="text-sm">
            Are you sure you want to <span className="fw-semibold">delete</span> this template?
            {delRow && (
              <div className="mt-3 p-3 rounded-xl bg-red-500/10 ring-1 ring-red-500/20">
                <div className="font-medium truncate" title={delRow.name}>{delRow.name}</div>
                <div className="text-xs opacity-80 mt-1 truncate" title={delRow.subject || '—'}>{delRow.subject || '—'}</div>
              </div>
            )}
          </div>
        </Modal.Body>
        <Modal.Footer className="border-0 pt-0">
          <Button variant="secondary" onClick={() => setShowDel(false)}>Cancel</Button>
          <Button variant="rose" onClick={doDel}>Delete</Button>
        </Modal.Footer>
      </Modal>
    </div>
  )
}