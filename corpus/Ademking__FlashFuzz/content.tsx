import cssText from "data-text:~style.css"
import { Check, CopyIcon, Download, Info } from "lucide-react"
import type { PlasmoCSConfig } from "plasmo"
import React, { useEffect, useRef, useState } from "react"

import { Storage } from "@plasmohq/storage"
import { useStorage } from "@plasmohq/storage/hook"

import Logo from "~logo"
import { SECRET_PATTERNS } from "~patterns"

const BATCH_SIZE_KEY = "flashfuzz_batch_size"
const INTERVAL_MS_KEY = "flashfuzz_interval_ms"
const REPEATED_SIZES_KEY = "flashfuzz_repeated_sizes_threshold"
const SCAN_PORTS_KEY = "flashfuzz_scan_ports"

declare global {
  interface Window {
    flashfuzzPaused?: boolean
    flashfuzzController?: { paused: boolean; stopped: boolean }
  }
}

export const config: PlasmoCSConfig = {
  matches: ["<all_urls>"],
  all_frames: false,
  run_at: "document_idle"
}

type FoundUrl = { url: string; size: number; status: number }
type FoundPort = { url: string; port: string; open: boolean }

type MatchResult = {
  type: string
  match: string
  line: number
  context: string
}

const getAllPageJS = async () => {
  try {
    // 1. Collect inline scripts
    const inlineScripts = [
      ...document.querySelectorAll("script:not([src])")
    ].map(
      (s, i) => `/* --- inline script ${i + 1} --- */\n${s.textContent || ""}`
    )

    // 2. Collect external script URLs
    const externalUrls = [...document.querySelectorAll("script[src]")].map(
      (s) => (s as HTMLScriptElement).src
    )

    // 3. Fetch each external script (may fail on CORS)
    const externalTexts = []
    for (const url of externalUrls) {
      try {
        const res = await fetch(url, { credentials: "include" })
        if (!res.ok) {
          externalTexts.push(
            `/* --- ${url} --- FETCH ERROR: ${res.status} ${res.statusText} --- */`
          )
          continue
        }
        const text = await res.text()
        externalTexts.push(`/* --- ${url} --- */\n${text}`)
      } catch (err) {
        externalTexts.push(
          `/* --- ${url} --- FETCH FAILED: ${err.message} --- */`
        )
      }
    }

    // 4. Return all scripts combined
    return [...inlineScripts, ...externalTexts].join("\n\n")
  } catch (err) {
    console.error("❌ Error collecting JS:", err)
    return ""
  }
}
// Format bytes to human-readable string
function formatBytes(bytes: number): string {
  if (!bytes || bytes === 0) return "0 B"
  const k = 1024
  const sizes = ["B", "KB", "MB", "GB", "TB"]
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + sizes[i]
}

function findSecretsWithContext(jsText: string): MatchResult[] {
  const results: MatchResult[] = []
  const lines = jsText.split(/\r?\n/)

  for (const [name, regex] of Object.entries(SECRET_PATTERNS)) {
    // clone regex so lastIndex doesn't interfere
    const r = new RegExp(
      regex.source,
      regex.flags.includes("g")
        ? regex.flags
        : (regex.flags + "g").replace(/([g])/, "$1")
    )
    let m: RegExpExecArray | null
    while ((m = r.exec(jsText)) !== null) {
      const match = m[0]
      // find line number by counting newlines up to match.index
      const upto = jsText.slice(0, m.index)
      const line = upto.split(/\r?\n/).length
      const startLine = Math.max(0, line - 2)
      const endLine = Math.min(lines.length - 1, line + 1)
      const context = lines.slice(startLine, endLine + 1).join("\n")
      results.push({ type: name, match, line, context })
      // safeguard for zero-length matches
      if (m.index === r.lastIndex) r.lastIndex++
    }
  }

  // dedupe very similar matches
  const unique = new Map<string, MatchResult>()
  for (const r of results) {
    const key = `${r.type}::${r.match}`
    if (!unique.has(key)) unique.set(key, r)
  }

  return Array.from(unique.values()).sort((a, b) => a.line - b.line)
}

function isExcludedSite(url: string, excludedSites: string): boolean {
  const siteList = excludedSites
    .split(/\r?\n|,/)
    .map((s) => s.trim())
    .filter(Boolean)
  return siteList.some(
    (site) => url.includes(site) || window.location.hostname.includes(site)
  )
}

// Port scanning function with short timeout
async function scanPortsRoot(
  ports: string[],
  controller: { paused: boolean; stopped: boolean },
  onProgress: (done: number, total: number) => void
): Promise<FoundPort[]> {
  const foundPorts: FoundPort[] = []
  let requestsDone = 0
  const total = ports.length
  const TIMEOUT_MS = 700 // very short timeout

  await Promise.all(
    ports.map(async (port) => {
      if (controller.stopped) return
      let testUrl =
        window.location.protocol +
        "//" +
        window.location.hostname +
        ":" +
        port +
        "/"
      const controllerAbort = new AbortController()
      const timeout = setTimeout(() => controllerAbort.abort(), TIMEOUT_MS)
      try {
        const res = await fetch(testUrl, {
          method: "HEAD",
          signal: controllerAbort.signal
        })
        clearTimeout(timeout)
        foundPorts.push({ url: "/", port, open: true }) // Any response means open
      } catch (err) {
        clearTimeout(timeout)
        // If error is due to abort (timeout), treat as closed
        if (err && err.name === "AbortError") {
          foundPorts.push({ url: "/", port, open: false })
        } else {
          // Any other error (including CORS) means port is open
          foundPorts.push({ url: "/", port, open: true })
        }
      } finally {
        requestsDone++
        onProgress(requestsDone, total)
      }
    })
  )
  return foundPorts
}

const checkUrlsIncremental = async (
  wordlists: string,
  controller: { paused: boolean; stopped: boolean },
  batchSize: number,
  intervalMs: number,
  repeatedSizesThreshold: number,
  scanPorts: string,
  onResult: (urls: FoundUrl[], ports: FoundPort[]) => void,
  onDone: () => void,
  onProgress: (done: number, total: number) => void
) => {
  let foundUrls: FoundUrl[] = []
  const urls = wordlists.split("\n").filter(Boolean)
  const ports = scanPorts
    .split(",")
    .map((p) => p.trim())
    .filter(Boolean)
  let requestsDone = 0
  const total = urls.length + (ports.length || 0)

  // Scan open ports for the root only (not for every path)
  const foundPorts = await scanPortsRoot(ports, controller, (done) =>
    onProgress(done, total)
  )

  for (let i = 0; i < urls.length; i += batchSize) {
    if (controller.stopped) break
    while (controller.paused && !controller.stopped) {
      await new Promise((resolve) => setTimeout(resolve, 300))
    }
    const batch = urls.slice(i, i + batchSize)

    await Promise.all(
      batch.map(async (url) => {
        if (controller.stopped) return
        try {
          const response = await fetch(window.location.origin + "/" + url, {
            credentials: "omit" // Bypass browser asking for credentials every time 401 is encountered
          })
          if (
            // 200-299,301,302,307,401,403,405,500
            // TODO: Make this configurable later
            response.ok ||
            response.status === 301 ||
            response.status === 302 ||
            response.status === 307 ||
            response.status === 401 ||
            response.status === 403 ||
            response.status === 405 ||
            response.status === 500
          ) {
            let size = parseInt(response.headers.get("content-length") || "")
            if (!size || isNaN(size)) {
              const blob = await response.clone().blob()
              size = blob.size
            }
            foundUrls.push({ url, size, status: response.status })
          }
        } catch {
        } finally {
          requestsDone++
          onProgress(requestsDone + ports.length, total)
        }
      })
    )

    const sizeCount: Record<number, number> = {}
    foundUrls.forEach(({ size }) => {
      if (size) sizeCount[size] = (sizeCount[size] || 0) + 1
    })
    const repeatedSizes = Object.entries(sizeCount)
      .filter(([_, count]) => count > repeatedSizesThreshold)
      .map(([size]) => Number(size))
    const filtered = foundUrls.filter(
      ({ size }) => !repeatedSizes.includes(size)
    )
    onResult(filtered, foundPorts)

    if (i + batchSize < urls.length && !controller.stopped) {
      await new Promise((resolve) => setTimeout(resolve, intervalMs))
    }
  }
  onDone()
}

export const getStyle = () => {
  const style = document.createElement("style")
  style.textContent = cssText.replaceAll(":root", ":host(plasmo-csui)")
  return style
}

const Main = ({ wordlists }) => {
  const [foundUrls, setFoundUrls] = useState<FoundUrl[]>([])
  const [foundPorts, setFoundPorts] = useState<FoundPort[]>([])
  const [loading, setLoading] = useState(true)
  const shouldRunRef = useRef(true)
  const [reqCount, setReqCount] = useState(0)
  const [visible, setVisible] = useState(true)
  const [minimized, setMinimized] = useState(false)
  const [copied, setCopied] = useState(false)

  // Draggable state
  const [pos, setPos] = useState({ x: 0, y: 0 })
  const dragRef = useRef<HTMLDivElement>(null)
  const dragging = useRef(false)
  const offset = useRef({ x: 0, y: 0 })
  const [paused, setPaused] = useState(false)
  const [foundSecrets, setFoundSecrets] = useState<MatchResult[]>([])
  const [secretSearch, setSecretSearch] = useState("")
  const [secretTypeFilter, setSecretTypeFilter] = useState("All")

  // Derive unique types for the filter dropdown
  const secretTypes = Array.from(
    new Set(foundSecrets.map((s) => s.type))
  ).sort()

  // Apply filters
  const filteredSecrets = foundSecrets.filter((s) => {
    const matchesSearch =
      secretSearch === "" ||
      s.match.toLowerCase().includes(secretSearch.toLowerCase())
    const matchesType =
      secretTypeFilter === "All" || s.type === secretTypeFilter
    return matchesSearch && matchesType
  })

  // Read batchSize, intervalMs, repeatedSizesThreshold, scanPorts from storage (local area)
  const [batchSize] = useStorage<number>(
    { key: BATCH_SIZE_KEY, instance: new Storage({ area: "local" }) },
    10
  )
  const [intervalMs] = useStorage<number>(
    { key: INTERVAL_MS_KEY, instance: new Storage({ area: "local" }) },
    500
  )
  const [repeatedSizesThreshold] = useStorage<number>(
    { key: REPEATED_SIZES_KEY, instance: new Storage({ area: "local" }) },
    5
  )
  const [scanPorts] = useStorage<string>(
    { key: SCAN_PORTS_KEY, instance: new Storage({ area: "local" }) },
    "80,443"
  )

  // Calculate total requests for progress bar
  const totalRequests =
    wordlists.split("\n").filter(Boolean).length +
    scanPorts.split(",").filter(Boolean).length

  // Function to save results to a text file
  const handleSaveResultsAsTXT = () => {
    if (
      foundUrls.length === 0 &&
      foundSecrets.length === 0 &&
      foundPorts.length === 0
    )
      return

    const now = new Date()
    const header = `FlashFuzz Scan Results\nPage scanned: ${window.location.href}\nDate scanned: ${now.toLocaleString()}\n\nURLs:\nURL\tSize (bytes)\n--------------------------------`

    const urlsBody = foundUrls
      .map(
        ({ url, size }) =>
          `${window.location.origin}/${url}\t${
            size ? formatBytes(size) : "unknown"
          }`
      )
      .join("\n")

    const portsHeader = `\nPorts:\nURL\tPort\tOpen\n--------------------------------`
    const portsBody = foundPorts
      .map(
        ({ url, port, open }) =>
          `${window.location.origin}/${url}\t${port}\t${open ? "open" : "closed"}`
      )
      .join("\n")

    const secretsHeader = `\nSecrets:\nType\tMatch\n--------------------------------`

    const secretsBody = foundSecrets
      .map(({ type, match }) => `${type}\t${match}`)
      .join("\n")

    const textContent = `${header}\n${urlsBody}\n${portsHeader}\n${portsBody}\n${secretsHeader}\n${secretsBody}`

    const blob = new Blob([textContent], { type: "text/plain" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "flashfuzz_results.txt"
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleSaveResultsAsJSON = () => {
    if (
      foundUrls.length === 0 &&
      foundSecrets.length === 0 &&
      foundPorts.length === 0
    )
      return
    const now = new Date()
    const results = {
      pageScanned: window.location.href,
      dateScanned: now.toISOString(),
      urls: foundUrls.map(({ url, size }) => ({
        url: `${window.location.origin}/${url}`,
        size: size ? formatBytes(size) : "unknown"
      })),
      ports: foundPorts.map(({ url, port, open }) => ({
        url: `${window.location.origin}/${url}`,
        port,
        open
      })),
      secrets: foundSecrets
    }
    const jsonContent = JSON.stringify(results, null, 2)
    const blob = new Blob([jsonContent], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "flashfuzz_results.json"
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleCopyToClipboard = () => {
    if (
      foundUrls.length === 0 &&
      foundSecrets.length === 0 &&
      foundPorts.length === 0
    )
      return

    const header = `FlashFuzz Scan Results\nPage scanned: ${window.location.href}\nDate scanned: ${new Date().toLocaleString()}\nURLs:\nURL\tSize (bytes)\n--------------------------------`
    const urlsBody = foundUrls
      .map(
        ({ url, size }) =>
          `${window.location.origin}/${url}\t${
            size ? formatBytes(size) : "unknown"
          }`
      )
      .join("\n")
    const portsHeader = `\nPorts:\nURL\tPort\tOpen\n--------------------------------`
    const portsBody = foundPorts
      .map(
        ({ url, port, open }) =>
          `${window.location.origin}/${url}\t${port}\t${open ? "open" : "closed"}`
      )
      .join("\n")
    const secretsHeader = `\nSecrets:\nType\tMatch\n--------------------------------`
    const secretsBody = foundSecrets
      .map(({ type, match }) => `${type}\t${match}`)
      .join("\n")
    const textContent = `${header}\n${urlsBody}\n${portsHeader}\n${portsBody}\n${secretsHeader}\n${secretsBody}`

    navigator.clipboard
      .writeText(textContent)
      .then(() => {
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      })
      .catch((err) =>
        console.error("Failed to copy results to clipboard:", err)
      )
  }

  const handleAboutClick = () => {
    // Open a new tab with about info
    window.open("https://github.com/Ademking/FlashFuzz", "_blank")
  }

  // Main effect to run the scans

  useEffect(() => {
    const controller = { paused: false, stopped: false }
    setFoundUrls([])
    setFoundPorts([])
    setFoundSecrets([])
    setLoading(true)
    setReqCount(0)

    // URL and Port scanning
    const runUrlPortScan = async () => {
      await checkUrlsIncremental(
        wordlists,
        controller,
        batchSize,
        intervalMs,
        repeatedSizesThreshold,
        scanPorts,
        (urls, ports) => {
          setFoundUrls(urls)
          setFoundPorts(ports)
        },
        () => {},
        (done) => setReqCount(done)
      )
    }

    // Secret scanning (unchanged)
    const runSecretScan = async () => {
      try {
        const inlineScripts = [
          ...document.querySelectorAll("script:not([src])")
        ]
        const externalUrls = [...document.querySelectorAll("script[src]")].map(
          (s) => (s as HTMLScriptElement).src
        )

        const scripts = inlineScripts.map((s, i) => ({
          name: `inline-${i + 1}`,
          content: s.textContent || ""
        }))

        for (const url of externalUrls) {
          try {
            const res = await fetch(url, { credentials: "include" })
            const text = res.ok ? await res.text() : `/* ERROR ${res.status} */`
            scripts.push({ name: url, content: text })
          } catch (err) {
            scripts.push({ name: url, content: `/* FETCH ERROR */` })
          }
        }

        let allSecrets: MatchResult[] = []

        for (const script of scripts) {
          if (!script.content) continue
          const secrets = findSecretsWithContext(script.content)
          allSecrets = allSecrets.concat(secrets)
          setFoundSecrets([...allSecrets])
          await new Promise((r) => setTimeout(r, 10))
        }
      } catch (err) {
        console.error(err)
      }
    }

    runUrlPortScan()
    runSecretScan()
    window.flashfuzzController = controller
    return () => {
      controller.stopped = true
    }
  }, [wordlists, batchSize, intervalMs, repeatedSizesThreshold, scanPorts])

  // Only set loading to false when scan is truly finished

  useEffect(() => {
    const ctrl = window.flashfuzzController
    if (reqCount >= totalRequests || (ctrl && ctrl.stopped)) {
      setLoading(false)
    }
  }, [reqCount, totalRequests])

  // Overlay is always shown, even if there are no results
  if (!visible) return null

  // Draggable handlers
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!dragging.current) return
      setPos({
        x: e.clientX - offset.current.x,
        y: e.clientY - offset.current.y
      })
    }
    const handleMouseUp = () => {
      dragging.current = false
    }
    window.addEventListener("mousemove", handleMouseMove)
    window.addEventListener("mouseup", handleMouseUp)
    return () => {
      window.removeEventListener("mousemove", handleMouseMove)
      window.removeEventListener("mouseup", handleMouseUp)
    }
  }, [])

  return (
    <div
      ref={dragRef}
      dir="ltr"
      style={{
        zIndex: 99999999999,
        position: "fixed",
        left: pos.x || undefined,
        top: pos.y || undefined,
        width: minimized ? 160 : 480,
        // fallback to top-right if untouched
        ...(pos.x === 0 && pos.y === 0 ? { top: 12, right: 12 } : {})
      }}
      className={`z-50 text-gray-200 border border-gray-800 rounded-xl shadow-xl bg-gray-900 bg-opacity-95 ${minimized ? "!w-[200px]" : "!w-[480px]"} `}
      role="region"
      aria-label="FlashFuzz overlay">
      {/* Header */}
      <div
        className={`flex items-center gap-2 relative cursor-move select-none ${
          minimized ? "px-4 pt-1 pb-1" : "px-4 pt-3 pb-2"
        }`}
        style={{ userSelect: "none" }}
        onMouseDown={(e) => {
          const target = e.target as HTMLElement
          // Only start drag if clicked directly on header (not links/buttons inside)
          if (target.closest("a, button, input, select, textarea")) return
          if (e.button !== 0) return // only left click
          dragging.current = true
          const rect = dragRef.current?.getBoundingClientRect()
          offset.current = {
            x: e.clientX - (rect?.left ?? 0),
            y: e.clientY - (rect?.top ?? 0)
          }
          e.stopPropagation()
          e.preventDefault()
        }}>
        <span
          className={`flex items-center justify-center rounded ${minimized ? "w-4 h-4" : "w-7 h-7"}`}>
          <Logo />
        </span>
        <span className={`font-semibold ${minimized ? "text-sm" : "text-lg"}`}>
          FlashFuzz
        </span>

        {/* Header buttons container */}
        <div className="absolute top-0 right-0 mt-1 mr-1 flex gap-1">
          {/* Pause / Resume Button */}
          {loading && (
            <button
              aria-label={paused ? "Play" : "Pause"}
              className="w-6 h-6 flex items-center justify-center rounded hover:bg-gray-700 focus:outline-none"
              onClick={() => {
                const ctrl = window.flashfuzzController
                if (ctrl) ctrl.paused = !ctrl.paused
                setPaused((p) => !p)
              }}>
              {paused ? (
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 20 20"
                  fill="none"
                  className="text-gray-400">
                  <path d="M6 4L14 10L6 16V4Z" fill="currentColor" />
                </svg>
              ) : (
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 20 20"
                  fill="none"
                  className="text-gray-400">
                  <rect x="5" y="4" width="3" height="12" fill="currentColor" />
                  <rect
                    x="12"
                    y="4"
                    width="3"
                    height="12"
                    fill="currentColor"
                  />
                </svg>
              )}
            </button>
          )}

          {/* Stop Button */}
          {loading && (
            <button
              aria-label="Stop"
              className="w-6 h-6 flex items-center justify-center rounded hover:bg-red-700 focus:outline-none"
              onClick={() => {
                const ctrl = window.flashfuzzController
                if (ctrl) ctrl.stopped = true
                setLoading(false)
              }}>
              <svg
                width="16"
                height="16"
                viewBox="0 0 20 20"
                fill="none"
                className="text-red-400">
                <rect x="5" y="5" width="10" height="10" fill="currentColor" />
              </svg>
            </button>
          )}

          {/* Minimize / Maximize Button */}
          <button
            aria-label={minimized ? "Maximize" : "Minimize"}
            className="w-6 h-6 flex items-center justify-center rounded hover:bg-gray-700 focus:outline-none"
            onClick={() => setMinimized((prev) => !prev)}>
            {minimized ? (
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="text-gray-400">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              </svg>
            ) : (
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="text-gray-400">
                <line x1="3" y1="12" x2="21" y2="12" />
              </svg>
            )}
          </button>

          {/* Close Button */}
          <button
            aria-label="Close overlay"
            className="w-6 h-6 flex items-center justify-center rounded hover:bg-gray-700 focus:outline-none"
            onClick={() => setVisible(false)}>
            <svg
              width="16"
              height="16"
              viewBox="0 0 20 20"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              className="text-gray-400">
              <path
                d="M6 6L14 14M6 14L14 6"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </button>
        </div>
      </div>

      {!minimized && (
        <>
          {/* Body */}
          <div className="px-4">
            {loading ? (
              <div className="flex flex-col items-center py-2">
                <span className="text-xs font-medium text-gray-400 mb-1">
                  {paused ? "Paused" : "Scanning..."}
                </span>
                <span className="text-[10px] text-yellow-200">
                  {reqCount}/{totalRequests} requests
                </span>
                <div className="w-full h-3 mt-2 rounded-full bg-gray-700 border border-gray-600 relative">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-yellow-400 to-yellow-600 transition-all duration-300"
                    style={{
                      width: `${totalRequests > 0 ? Math.round((reqCount / totalRequests) * 100) : 0}%`
                    }}
                  />
                  <span
                    className="absolute left-1/2 top-1/2 transform -translate-x-1/2 -translate-y-1/2 text-[10px] text-gray-200 font-semibold pointer-events-none"
                    style={{ userSelect: "none" }}>
                    {totalRequests > 0
                      ? `${Math.round((reqCount / totalRequests) * 100)}%`
                      : "0%"}
                  </span>
                </div>
              </div>
            ) : (
              <>
                <div className="text-xs font-semibold text-gray-400 mb-1">
                  {foundUrls.length === 0 ? (
                    <span>No URLs found</span>
                  ) : (
                    <span>Found URLs</span>
                  )}{" "}
                  <span className="text-gray-200">
                    ({foundUrls.length}/
                    {wordlists.split("\n").filter(Boolean).length})
                  </span>
                  :
                </div>
              </>
            )}

            {foundUrls.length > 0 && (
              <div className="max-h-[120px] overflow-y-auto rounded bg-gray-800 border border-gray-400/20 p-1 mt-1">
                <ul className="space-y-1">
                  {foundUrls.map(({ url, size, status }) => (
                    <li
                      key={url}
                      className="flex items-center justify-between px-1 py-0.5 rounded hover:bg-gray-400/10 transition-colors cursor-pointer"
                      onClick={() =>
                        window.open(
                          window.location.origin + "/" + url,
                          "_blank"
                        )
                      }>
                      <span className="text-gray-400 underline font-mono text-[11px] hover:text-yellow-200 transition-colors">
                        {url}
                      </span>
                      <div className="flex items-center gap-2 ml-2">
                        <span className="text-yellow-200 text-[10px] font-mono">
                          {size ? formatBytes(size) : "N/A"}
                        </span>
                        <span
                          className={`text-[10px] font-mono ${
                            status >= 200 && status < 300
                              ? "text-green-400"
                              : status >= 400 && status < 500
                                ? "text-yellow-400"
                                : "text-red-400"
                          }`}>
                          [{status}]
                        </span>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="pointer-events-auto select-text py-2">
              <div className="flex items-center flex-wrap gap-2">
                <span className="text-xs font-semibold text-gray-400">
                  Available Ports:
                </span>

                {foundPorts.filter((p) => p.open).length > 0 ? (
                  foundPorts
                    .filter((p) => p.open)
                    .map((p, i) => {
                      const portUrl = `${window.location.protocol}//${window.location.hostname}:${p.port}/`
                      return (
                        <a
                          key={i}
                          href={portUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          aria-label={`Open ${p.port} in new tab`}
                          className="
    inline-flex items-center justify-center
    bg-blue-500/10 hover:bg-blue-500/20
    text-blue-300 hover:text-blue-200
    font-mono text-[10px] px-2 py-0.5 rounded-full
    transition-colors duration-150 ease-in-out
    focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-blue-400/50
    min-w-[32px]
  ">
                          {p.port}
                        </a>
                      )
                    })
                ) : (
                  <span className="text-[11px] text-gray-500 italic">
                    No open ports detected
                  </span>
                )}
              </div>
            </div>

            {/* Found Secrets Section */}
            {foundSecrets.length > 0 && (
              <>
                <div className="text-xs font-semibold my-2 text-red-400 flex justify-between items-center">
                  <span>
                    Potential Secrets ({filteredSecrets.length}/
                    {foundSecrets.length})
                  </span>
                  <div className="flex gap-1">
                    {/* Search */}
                    <input
                      type="text"
                      placeholder="Search..."
                      value={secretSearch}
                      onChange={(e) => setSecretSearch(e.target.value)}
                      className="text-[10px] px-1 py-0.5 rounded bg-gray-700 text-gray-200 border border-gray-600 focus:outline-none"
                    />
                    {/* Type Filter */}
                    <select
                      value={secretTypeFilter}
                      onChange={(e) => setSecretTypeFilter(e.target.value)}
                      className="text-[10px] px-1 py-0.5 rounded bg-gray-700 text-gray-200 border border-gray-600 focus:outline-none">
                      <option value="All">All Types</option>
                      {secretTypes.map((t) => (
                        <option key={t} value={t}>
                          {t}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="max-h-[300px] overflow-y-auto rounded bg-gray-800 border border-red-600/50 p-1 mt-2">
                  <ul className="space-y-1">
                    {filteredSecrets.map((s, i) => (
                      <li
                        key={i}
                        className="px-1 py-0.5 rounded hover:bg-red-700/10">
                        <div className="flex justify-between items-center">
                          <span className="text-[10px] text-red-300 font-mono break-all">
                            {s.match}
                          </span>
                          <span className="text-[9px] font-semibold text-red-500 ml-2 font-mono">
                            [{s.type}]
                          </span>
                        </div>
                      </li>
                    ))}
                    {filteredSecrets.length === 0 && (
                      <li className="text-[10px] text-gray-400 italic px-1 py-0.5">
                        No secrets match the filter/search.
                      </li>
                    )}
                  </ul>
                </div>
              </>
            )}
          </div>

          {/* Footer */}
          <div className="flex justify-end gap-2 px-4 py-2">
            <button
              onClick={handleAboutClick}
              className="flex items-center gap-1 text-xs font-semibold text-gray-300 bg-gray-800 px-3 py-1 rounded hover:bg-gray-700 transition">
              <Info className="w-3 h-3" />
              About
            </button>

            <button
              onClick={handleSaveResultsAsTXT}
              className="flex items-center gap-1 text-xs font-semibold text-gray-300 bg-gray-800 px-3 py-1 rounded hover:bg-gray-700 transition">
              <Download className="w-3 h-3" />
              TXT
            </button>

            <button
              onClick={handleSaveResultsAsJSON}
              className="flex items-center gap-1 text-xs font-semibold text-gray-300 bg-gray-800 px-3 py-1 rounded hover:bg-gray-700 transition">
              <Download className="w-3 h-3" />
              JSON
            </button>

            <button
              onClick={handleCopyToClipboard}
              className="flex items-center gap-1 text-xs font-semibold text-gray-300 bg-gray-800 px-3 py-1 rounded hover:bg-gray-700 transition">
              {copied ? (
                <Check className="w-3 h-3 text-green-400" />
              ) : (
                <CopyIcon className="w-3 h-3" />
              )}
              {copied ? "Copied!" : "Copy"}
            </button>
          </div>
        </>
      )}
    </div>
  )
}

const Content = () => {
  const [enabled] = useStorage<boolean>(
    { key: "flashfuzz_enabled", instance: new Storage({ area: "local" }) },
    false
  )
  const [wordlists] = useStorage<string>(
    { key: "flashfuzz_wordlists", instance: new Storage({ area: "local" }) },
    ""
  )
  const [excludedSites] = useStorage<string>(
    {
      key: "flashfuzz_excluded_sites",
      instance: new Storage({ area: "local" })
    },
    ""
  )

  if (!enabled) return null
  if (isExcludedSite(window.location.href, excludedSites)) return null
  return <Main wordlists={wordlists} />
}

export default Content
