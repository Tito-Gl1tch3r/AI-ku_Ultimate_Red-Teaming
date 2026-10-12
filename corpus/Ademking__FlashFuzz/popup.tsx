"use client"

import clsx from "clsx"
import { Check, Info, RefreshCcw, Save, Zap } from "lucide-react"
import type React from "react"
import { useEffect, useState } from "react"

import { Storage } from "@plasmohq/storage"

import {
  batchSizeDefault,
  defaultPorts,
  excludedSitesDefault,
  intervalMsDefault,
  repeatedSizesThresholdDefault
} from "~constants"
import Logo from "~logo"
import urlsToCheck from "~wordlist"

import "./style.css"

const EXT_KEY = "flashfuzz_enabled"
const WORDLISTS_KEY = "flashfuzz_wordlists"
const EXCLUDED_SITES_KEY = "flashfuzz_excluded_sites"
const SCAN_PORTS_KEY = "flashfuzz_scan_ports"
const BATCH_SIZE_KEY = "flashfuzz_batch_size"
const INTERVAL_MS_KEY = "flashfuzz_interval_ms"
const REPEATED_SIZES_KEY = "flashfuzz_repeated_sizes_threshold"

const storage = new Storage({
  area: "local"
})
const wordlistsDefault = urlsToCheck.join("\n")
const scanPortsDefault = defaultPorts.join(",")

const Popup = () => {
  const [enabled, setEnabled] = useState(false)
  const [wordlists, setWordlists] = useState("")
  const [excludedSites, setExcludedSites] = useState("")
  const [scanPorts, setScanPorts] = useState("")
  const [batchSize, setBatchSize] = useState(batchSizeDefault)
  const [intervalMs, setIntervalMs] = useState(intervalMsDefault)
  const [repeatedSizesThreshold, setRepeatedSizesThreshold] = useState(
    repeatedSizesThresholdDefault
  )
  const [showSaved, setShowSaved] = useState(false)

  useEffect(() => {
    // Get Enabled/Disabled state from storage
    storage.get(EXT_KEY).then((stored) => {
      if (typeof stored === "boolean") setEnabled(stored)
      else if (typeof stored === "string") setEnabled(stored === "true")
    })

    // Get Wordlists from storage or set default if not present
    storage.get(WORDLISTS_KEY).then((stored) => {
      if (typeof stored === "string") setWordlists(stored)
      else {
        setWordlists(wordlistsDefault)
        storage.set(WORDLISTS_KEY, wordlistsDefault)
      }
    })

    // Get Excluded Sites from storage or set default if not present
    storage.get(EXCLUDED_SITES_KEY).then((stored) => {
      if (typeof stored === "string") setExcludedSites(stored)
      else {
        setExcludedSites(excludedSitesDefault)
        storage.set(EXCLUDED_SITES_KEY, excludedSitesDefault)
      }
    })
    // Get Scan Ports from storage or set default if not present
    storage.get(SCAN_PORTS_KEY).then((stored) => {
      if (typeof stored === "string") setScanPorts(stored)
      else {
        setScanPorts(scanPortsDefault)
        storage.set(SCAN_PORTS_KEY, scanPortsDefault)
      }
    })

    // Get other settings from storage or set defaults if not present
    storage.get(BATCH_SIZE_KEY).then((stored) => {
      const val = Number.parseInt(stored)
      setBatchSize(Number.isNaN(val) ? batchSizeDefault : val)
    })
    storage.get(INTERVAL_MS_KEY).then((stored) => {
      const val = Number.parseInt(stored)
      setIntervalMs(Number.isNaN(val) ? intervalMsDefault : val)
    })
    storage.get(REPEATED_SIZES_KEY).then((stored) => {
      const val = Number.parseInt(stored)
      setRepeatedSizesThreshold(
        Number.isNaN(val) ? repeatedSizesThresholdDefault : val
      )
    })
  }, [])

  // Toggle Enabled/Disabled state
  const handleToggle = async () => {
    await storage.set(EXT_KEY, !enabled)
    setEnabled((prev) => !prev)
  }

  // Handle changes in the wordlists textarea
  const handleWordlistsChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setWordlists(e.target.value)
  }

  // Reset settings to default values
  const handleReset = () => {
    setWordlists(wordlistsDefault)
    storage.set(WORDLISTS_KEY, wordlistsDefault)
    setBatchSize(batchSizeDefault)
    storage.set(BATCH_SIZE_KEY, batchSizeDefault)
    setIntervalMs(intervalMsDefault)
    storage.set(INTERVAL_MS_KEY, intervalMsDefault)
    setRepeatedSizesThreshold(repeatedSizesThresholdDefault)
    storage.set(REPEATED_SIZES_KEY, repeatedSizesThresholdDefault)
    setExcludedSites(excludedSitesDefault)
    storage.set(EXCLUDED_SITES_KEY, excludedSitesDefault)
    setScanPorts(scanPortsDefault)
    storage.set(SCAN_PORTS_KEY, scanPortsDefault)
  }

  // Save all settings to storage
  const handleSaveSettings = () => {
    storage.set(WORDLISTS_KEY, wordlists)
    storage.set(EXCLUDED_SITES_KEY, excludedSites)
    storage.set(BATCH_SIZE_KEY, batchSize)
    storage.set(INTERVAL_MS_KEY, intervalMs)
    storage.set(REPEATED_SIZES_KEY, repeatedSizesThreshold)
    storage.set(SCAN_PORTS_KEY, scanPorts)
    setShowSaved(true)
    setTimeout(() => setShowSaved(false), 2000)
  }

  return (
    <div className="min-w-[340px] max-w-sm bg-gradient-to-b from-slate-900 via-slate-950 to-black text-slate-100 overflow-hidden text-xs border border-slate-800/50">
      <div className="px-4 py-3 border-b border-slate-800/50 bg-gradient-to-r from-slate-900/80 to-slate-950/80 backdrop-blur-sm">
        <div className="flex items-center justify-between gap-3">
          {/* Left: Logo + Text */}
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <div className="flex-shrink-0 p-1.5 bg-gradient-to-br from-yellow-500/20 to-amber-500/20 rounded-lg border border-yellow-500/30">
              <Logo className="w-5 h-5 text-yellow-400" />
            </div>
            <div className="min-w-0">
              <h1 className="text-sm font-bold text-white tracking-tight">
                FlashFuzz
              </h1>
              <p className="text-xs text-slate-400">v1.2</p>
            </div>
          </div>

          <button
            onClick={handleToggle}
            role="switch"
            aria-checked={enabled}
            className={clsx(
              "flex items-center gap-1.5 px-2.5 py-1 rounded-lg font-semibold text-xs",
              "transition-all duration-300 flex-shrink-0",
              "focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-950",
              {
                "bg-gradient-to-r from-yellow-500 to-amber-500 text-slate-900 focus:ring-yellow-400 shadow-lg shadow-yellow-500/20":
                  enabled,
                "bg-slate-800 text-slate-400 hover:bg-slate-700 focus:ring-slate-600":
                  !enabled
              }
            )}>
            <Zap className={clsx("w-3 h-3", enabled ? "fill-current" : "")} />
            <span>{enabled ? "ON" : "OFF"}</span>
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="px-4 py-3 space-y-3 overflow-y-auto">
        <div className="space-y-2">
          <div className="space-y-1.5 bg-slate-800/40 rounded-lg p-2.5 border border-slate-700/50 backdrop-blur-sm">
            {[
              {
                label: "Batch Size",
                val: batchSize,
                set: setBatchSize,
                def: batchSizeDefault,
                tooltip: "Number of requests to send in each batch."
              },
              {
                label: "Interval (ms)",
                val: intervalMs,
                set: setIntervalMs,
                def: intervalMsDefault,
                tooltip: "The time to wait between each request."
              },
              {
                label: "Duplicate Filter",
                val: repeatedSizesThreshold,
                set: setRepeatedSizesThreshold,
                def: repeatedSizesThresholdDefault,
                tooltip:
                  "Filters out duplicate responses when requests return the same data. For every response size that is repeated more than this threshold, only one will be kept."
              }
            ].map((item, i) => (
              <div
                key={i}
                className="flex items-center justify-between gap-2 py-0.5">
                <div className="flex items-center gap-1 flex-1 text-xs text-slate-300 font-medium">
                  {item.label}
                  <span title={item.tooltip} className="flex-shrink-0">
                    <Info className="w-3 h-3 text-slate-500 hover:text-slate-400 cursor-help transition-colors" />
                  </span>
                </div>
                <input
                  type="number"
                  min={1}
                  value={item.val}
                  onChange={(e) =>
                    item.set(
                      Math.max(1, Number.parseInt(e.target.value) || item.def)
                    )
                  }
                  className="w-16 px-1.5 py-0.5 text-xs bg-slate-900/60 border border-slate-700 rounded-md text-slate-100 placeholder-slate-500 focus:outline-none focus:border-yellow-500 focus:ring-1 focus:ring-yellow-500/50 transition"
                />
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-2">
          {/* Wordlists */}
          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-300 flex items-center gap-1 px-0.5">
              Wordlists
              <span title="List of words used for fuzzing. Each entry should be on a new line.">
                <Info className="w-3 h-3 text-slate-500 hover:text-slate-400 cursor-help transition-colors" />
              </span>
            </label>
            <textarea
              value={wordlists}
              rows={2}
              onChange={handleWordlistsChange}
              placeholder="Enter wordlists (one per line)..."
              className="w-full border border-slate-700 bg-slate-900/60 text-slate-100 px-2 py-1.5 text-xs rounded-lg resize-none focus:outline-none focus:border-yellow-500 focus:ring-1 focus:ring-yellow-500/50 transition placeholder-slate-500"
            />
            <div className="text-xs text-slate-600 px-0.5 text-right">
              {wordlists
                ? wordlists.split("\n").filter((l) => l.trim()).length
                : 0}{" "}
              words
            </div>
          </div>

          {/* Ports */}
          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-300 flex items-center gap-1 px-0.5">
              Scan Ports
              <span title="List of ports to scan, separated by commas.">
                <Info className="w-3 h-3 text-slate-500 hover:text-slate-400 cursor-help transition-colors" />
              </span>
            </label>
            <input
              value={scanPorts}
              onChange={(e) => setScanPorts(e.target.value)}
              placeholder="Enter scan ports (comma-separated)..."
              className="w-full border border-slate-700 bg-slate-900/60 text-slate-100 px-2 py-1.5 text-xs rounded-lg resize-none focus:outline-none focus:border-yellow-500 focus:ring-1 focus:ring-yellow-500/50 transition placeholder-slate-500"
            />
            <div className="text-xs text-slate-600 px-0.5 text-right">
              {scanPorts
                ? scanPorts.split(",").filter((l) => l.trim()).length
                : 0}{" "}
              ports
            </div>
          </div>

          {/* Excluded Websites */}
          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-300 flex items-center gap-1 px-0.5">
              Excluded Websites
              <span title="List of websites where FlashFuzz should be inactive. Each entry should be on a new line.">
                <Info className="w-3 h-3 text-slate-500 hover:text-slate-400 cursor-help transition-colors" />
              </span>
            </label>
            <textarea
              value={excludedSites}
              rows={2}
              onChange={(e) => setExcludedSites(e.target.value)}
              placeholder="Enter excluded websites (one per line)..."
              className="w-full border border-slate-700 bg-slate-900/60 text-slate-100 px-2 py-1.5 text-xs rounded-lg resize-none focus:outline-none focus:border-yellow-500 focus:ring-1 focus:ring-yellow-500/50 transition placeholder-slate-500"
            />
            <div className="text-xs text-slate-600 px-0.5 text-right">
              {excludedSites
                ? excludedSites.split("\n").filter((l) => l.trim()).length
                : 0}{" "}
              excluded sites
            </div>
          </div>

          <div className="flex gap-2 mt-3 pt-1.5">
            <button
              onClick={handleSaveSettings}
              className={clsx(
                "flex-1 flex items-center justify-center gap-1.5 px-2.5 py-1.5 font-semibold text-xs rounded-lg transition-all duration-300",
                "focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-950",
                showSaved
                  ? "bg-gradient-to-r from-emerald-500 to-green-500 text-white focus:ring-emerald-400 shadow-lg shadow-emerald-500/20"
                  : "bg-gradient-to-r from-yellow-500 to-amber-500 text-slate-900 hover:shadow-lg hover:shadow-yellow-500/20 focus:ring-yellow-400 font-bold"
              )}>
              {showSaved ? (
                <>
                  <Check className="w-3.5 h-3.5" /> Saved!
                </>
              ) : (
                <>
                  <Save className="w-3.5 h-3.5" /> Save
                </>
              )}
            </button>
            <button
              onClick={handleReset}
              className="flex-1 flex items-center justify-center gap-1.5 px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs rounded-lg border border-slate-700 transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-950 focus:ring-slate-600">
              <RefreshCcw className="w-3.5 h-3.5" /> Reset
            </button>
          </div>
        </div>
      </div>

      <div className="px-4 py-2 border-t border-slate-800/50 bg-slate-900/50 text-xs text-slate-400 flex justify-center gap-1.5 flex-wrap">
        <a
          href="https://github.com/Ademking/FlashFuzz"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 hover:text-yellow-400 hover:underline transition">
          Like it? ⭐ Star it on GitHub!
        </a>
        <span className="text-slate-600">•</span>
        <a
          href="https://github.com/Ademking"
          target="_blank"
          rel="noopener noreferrer"
          className="hover:text-yellow-400 hover:underline transition">
          Made by Adem Kouki
        </a>
      </div>
    </div>
  )
}

export default Popup
