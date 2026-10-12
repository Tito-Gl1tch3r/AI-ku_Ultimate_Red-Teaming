import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";

function getCaret(el) {
  return el.selectionStart ?? 0
}

function setCaret(el, pos) {
  try {
    el.setSelectionRange(pos, pos)
  } catch {}
  el.focus()
}

function replaceRange(str, start, end, insert) {
  return str.slice(0, start) + insert + str.slice(end)
}

export default function VarAutocomplete({ targetRef, variables = [], anchorRight, onInsert }) {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState("")
  const [startIdx, setStartIdx] = useState(null)
  const [sel, setSel] = useState(0)
  const menuRef = useRef(null)
  const [pos, setPos] = useState(null)

  const filtered = useMemo(() => {
    const needle = q.toLowerCase()
    const uniq = Array.from(new Set(variables))

    const starts = [], contains = []
    for (const v of uniq) {
      const l = v.toLowerCase()
      if (!needle || l.startsWith(needle)) starts.push(v)
      else if (l.includes(needle)) contains.push(v)
    }
    return [...starts, ...contains].slice(0, 12)
  }, [q, variables])

  const insert = (chosen) => {
    const el = targetRef?.current
    if (!el || startIdx == null) return setOpen(false)
    const posCaret = getCaret(el)
    const token = `{{${chosen}}}`
    const newValue = replaceRange(el.value, startIdx, posCaret, token)
    el.value = newValue
    const newPos = startIdx + token.length
    setCaret(el, newPos)

    if (typeof onInsert === 'function') {
      onInsert(newValue)
    }

    setOpen(false)
  };


  // Listen to typing in the field
  useEffect(() => {
    const el = targetRef?.current
    if (!el) return

    const onInput = () => {
      const pos = getCaret(el)
      const before = el.value.slice(0, pos)
      const m = before.match(/\{\{[A-Za-z0-9_\-]*$/)

      if (m) {
        setOpen(true)
        setStartIdx(pos - m[0].length)
        setQ(m[0].slice(2))
        setSel(0)

      } else {
        setOpen(false)
      }
    }

    const onKeyDown = (e) => {
      if (!open) return

      if (["ArrowDown","ArrowUp","Enter","Tab","Escape"].includes(e.key)) {
        e.preventDefault()
        if (e.key === "ArrowDown") {
          setSel(s => Math.min(s + 1, filtered.length - 1))
        }
        if (e.key === "ArrowUp") {
          setSel(s => Math.max(s - 1, 0))
        }
        if (e.key === "Escape") {
          setOpen(false)
        }
        if (e.key === "Enter" || e.key === "Tab") {
          insert(filtered[sel] || q)
        }
      }
    };

    el.addEventListener("input", onInput)
    el.addEventListener("keydown", onKeyDown)

    return () => {
      el.removeEventListener("input", onInput)
      el.removeEventListener("keydown", onKeyDown)
    }

  }, [targetRef, open, filtered, sel, q, startIdx])

  // Position the dropdown under the input
  useLayoutEffect(() => {
    if (!open) return

    const el = targetRef?.current
    if (!el) return

    const compute = () => {
      const r = el.getBoundingClientRect()
      const minW = 240
      const width = Math.max(minW, r.width)
      const left = anchorRight ? r.right - width : r.left
      const top = r.bottom + 4
      setPos({ top, left, width })
    }

    compute()
    const onScroll = () => compute()
    const onResize = () => compute()

    window.addEventListener("scroll", onScroll, true)
    window.addEventListener("resize", onResize)

    return () => {
      window.removeEventListener("scroll", onScroll, true)
      window.removeEventListener("resize", onResize)
    }

  }, [open, targetRef, anchorRight])

  // Close on outside click
  useEffect(() => {
    if (!open) return

    const onDocMouseDown = (e) => {
      const el = targetRef?.current
      if (menuRef.current?.contains(e.target)) return
      if (el && el.contains(e.target)) return
      setOpen(false)
    }

    document.addEventListener("mousedown", onDocMouseDown)
    return () => document.removeEventListener("mousedown", onDocMouseDown)

  }, [open, targetRef])

  if (!open || filtered.length === 0 || !pos) {
    return null
  }

  // Render via portal so it never overlaps the input
   return createPortal(
    <div
      ref={menuRef}
      className="var-ac-menu"
      style={{
        position: "fixed",
        zIndex: 1080,
        top: pos.top,
        left: pos.left,
        width: pos.width,
        maxHeight: 260
      }}
      onMouseDown={(e) => e.preventDefault()} // keep focus in input
      role="listbox"
    >
      {filtered.map((v, i) => (
        <button
          key={v}
          type="button"
          className={`var-ac-item ${i === sel ? "is-active" : ""}`}
          onClick={() => insert(v)}
          onMouseEnter={() => setSel(i)}
          role="option"
          aria-selected={i === sel}
        >
          <code className="var-ac-token">{`{{${v}}}`}</code>
          <span className="var-ac-label">{v}</span>
        </button>
      ))}
    </div>,
    document.body
  )

}