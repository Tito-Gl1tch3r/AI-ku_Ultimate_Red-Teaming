import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useQaRunsStore } from '@/stores/qa-runs'

beforeEach(() => {
  setActivePinia(createPinia())
})

const deferred = () => {
  let resolve
  let reject
  const promise = new Promise((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

describe('qa-runs store', () => {
  it('marks the target running and stores the report on success', async () => {
    const store = useQaRunsStore()
    const runner = vi.fn().mockResolvedValue({ summary: 'ok', issues: [] })

    const run = store.start('audit:1', runner)
    expect(store.isRunning('audit:1')).toBe(true)
    expect(store.startedAt('audit:1')).toBeTruthy()

    await run
    expect(store.isRunning('audit:1')).toBe(false)
    expect(store.getRun('audit:1').report).toEqual({ summary: 'ok', issues: [] })
    expect(runner).toHaveBeenCalledTimes(1)
  })

  it('marks an inline job request running with its selected scope', async () => {
    const store = useQaRunsStore()
    const request = deferred()

    const promise = store.startJob('audit:1', () => request.promise, { scope: 'programmatic' })
    expect(store.isRunning('audit:1')).toBe(true)
    expect(store.runScope('audit:1')).toBe('programmatic')
    expect(store.startedAt('audit:1')).toBeTruthy()

    request.resolve({ summary: 'built-in result' })
    await promise
    expect(store.isRunning('audit:1')).toBe(false)
    expect(store.getRun('audit:1').report).toEqual({ summary: 'built-in result' })
  })

  it('ignores a second run for a target that is already running (double-run guard)', async () => {
    const store = useQaRunsStore()
    const first = deferred()
    const runner2 = vi.fn().mockResolvedValue({ summary: 'second' })

    const startPromise = store.start('audit:1', () => first.promise)
    expect(store.isRunning('audit:1')).toBe(true)

    await store.start('audit:1', runner2)
    expect(runner2).not.toHaveBeenCalled()
    expect(store.isRunning('audit:1')).toBe(true)

    first.resolve({ summary: 'first' })
    await startPromise
    expect(store.getRun('audit:1').report).toEqual({ summary: 'first' })
  })

  it('re-attaches instead of reloading while a run is in flight', async () => {
    const store = useQaRunsStore()
    const first = deferred()
    const loader = vi.fn().mockResolvedValue({ summary: 'cached' })

    const startPromise = store.start('audit:1', () => first.promise)
    await store.load('audit:1', loader)

    expect(loader).not.toHaveBeenCalled()
    expect(store.isRunning('audit:1')).toBe(true)

    first.resolve({ summary: 'fresh' })
    await startPromise
    expect(store.getRun('audit:1').report).toEqual({ summary: 'fresh' })
  })

  it('does not let a slow cached load clobber a run started during the fetch', async () => {
    const store = useQaRunsStore()
    const fetch = deferred()
    const runFetch = deferred()

    const loadPromise = store.load('audit:1', () => fetch.promise)
    const startPromise = store.start('audit:1', () => runFetch.promise)
    expect(store.isRunning('audit:1')).toBe(true)

    // Cached fetch resolves after the run has taken over — it must not overwrite.
    fetch.resolve({ summary: 'stale-cached' })
    await loadPromise
    expect(store.isRunning('audit:1')).toBe(true)

    runFetch.resolve({ summary: 'fresh-run' })
    await startPromise
    expect(store.getRun('audit:1').report).toEqual({ summary: 'fresh-run' })
  })

  it('loads a cached report when idle', async () => {
    const store = useQaRunsStore()
    const loader = vi.fn().mockResolvedValue({ summary: 'cached', issues: [] })

    await store.load('vuln:1:en', loader)
    expect(loader).toHaveBeenCalledTimes(1)
    expect(store.getRun('vuln:1:en').report).toEqual({ summary: 'cached', issues: [] })
    expect(store.getRun('vuln:1:en').loaded).toBe(true)
  })

  it('records the run error and clears the running flag on failure', async () => {
    const store = useQaRunsStore()

    await store.start(
      'audit:1',
      () => Promise.reject({ response: { data: { datas: 'boom' } } }),
      { errorFallback: 'fallback' }
    )

    expect(store.isRunning('audit:1')).toBe(false)
    expect(store.getRun('audit:1').error).toBe('boom')
  })

  it('reset clears a target run', async () => {
    const store = useQaRunsStore()
    await store.start('draft', () => Promise.resolve({ summary: 'draft result' }))
    expect(store.getRun('draft').report).toEqual({ summary: 'draft result' })

    store.reset('draft')
    expect(store.getRun('draft').report).toBeNull()
    expect(store.isRunning('draft')).toBe(false)
  })

  it('exposes setReport so progressive runners can update mid-flight', async () => {
    const store = useQaRunsStore()
    const gate = deferred()

    const startPromise = store.start('all:en', async ({ setReport }) => {
      setReport({ summary: 'partial', issues: [{ title: 'A' }], progress: { done: false, processed: 1, total: 2 } })
      await gate.promise
      return { summary: 'final', issues: [{ title: 'A' }, { title: 'B' }], progress: { done: true, processed: 2, total: 2 } }
    })

    await Promise.resolve()
    expect(store.isRunning('all:en')).toBe(true)
    expect(store.getRun('all:en').report.summary).toBe('partial')
    expect(store.getRun('all:en').report.issues).toHaveLength(1)

    gate.resolve()
    await startPromise
    expect(store.getRun('all:en').report.summary).toBe('final')
    expect(store.getRun('all:en').report.issues).toHaveLength(2)
  })

  it('keys are isolated from one another', async () => {
    const store = useQaRunsStore()
    await store.start('audit:1', () => Promise.resolve({ summary: 'A' }))
    await store.start('audit:2', () => Promise.resolve({ summary: 'B' }))

    expect(store.getRun('audit:1').report).toEqual({ summary: 'A' })
    expect(store.getRun('audit:2').report).toEqual({ summary: 'B' })
  })

  it('exposes safe defaults for missing keys', () => {
    const store = useQaRunsStore()
    expect(store.getRun(null)).toBeNull()
    expect(store.getRun('missing')).toBeNull()
    expect(store.isRunning(null)).toBe(false)
    expect(store.isLoading('missing')).toBe(false)
    expect(store.startedAt(null)).toBeNull()
    expect(store.runScope('missing')).toBeNull()
    expect(store.isJobRunning('missing')).toBe(false)
  })

  it.each([
    [{ response: { data: { datas: 'server detail' } } }, '', 'server detail'],
    [{ response: { status: 502 } }, 'fallback', 'The QA request timed out. Partial results may already be saved — try running again.'],
    [{ response: { status: 504 } }, '', 'The QA request timed out. Partial results may already be saved — try running again.'],
    [{ code: 'ECONNABORTED' }, '', 'The QA request timed out. Partial results may already be saved — try running again.'],
    [new Error('request timeout'), '', 'The QA request timed out. Partial results may already be saved — try running again.'],
    [new Error('boom'), 'fallback', 'fallback'],
    [new Error('boom'), '', 'boom']
  ])('normalizes load failures', async (error, fallback, expected) => {
    const store = useQaRunsStore()
    await store.load('audit:1', () => Promise.reject(error), { errorFallback: fallback })
    expect(store.getRun('audit:1').error).toBe(expected)
    expect(store.getRun('audit:1').loading).toBe(false)
  })

  it('does not let a run starting during a failed load publish its error', async () => {
    const store = useQaRunsStore()
    const fetch = deferred()
    const run = deferred()
    const loading = store.load('audit:1', () => fetch.promise)
    const running = store.start('audit:1', () => run.promise)
    fetch.reject(new Error('stale error'))
    await loading
    expect(store.getRun('audit:1').error).toBe('')
    run.resolve()
    await running
    expect(store.getRun('audit:1').report).toBeNull()
  })

  it('clears stale progress and accepts runner-driven reports', async () => {
    const store = useQaRunsStore()
    store.setReport('audit:1', { progress: { processed: 3 } })
    await store.start('audit:1', async ({ setReport }) => {
      expect(store.getRun('audit:1').report.progress).toBeNull()
      setReport(null)
    })
    expect(store.getRun('audit:1').report).toEqual({})
  })

  it('tracks background jobs, rejects duplicates, and resets them', async () => {
    const store = useQaRunsStore()
    store.setReport('audit:1', { progress: { processed: 3 } })
    await store.startJob('audit:1', () => Promise.resolve({ job: { state: 'running' } }), { scope: 'ai' })
    expect(store.isJobRunning('audit:1')).toBe(true)
    expect(store.getRun('audit:1').report.progress).toBeNull()
    const duplicate = vi.fn()
    await store.startJob('audit:1', duplicate)
    expect(duplicate).not.toHaveBeenCalled()
    store.setJob('audit:1', null)
    store.reset('missing')
    expect(store.isJobRunning('audit:1')).toBe(false)
  })

  it('records startJob errors and inline empty results', async () => {
    const store = useQaRunsStore()
    await store.startJob('audit:1', () => Promise.reject(new Error('boom')), { errorFallback: 'fallback' })
    expect(store.getRun('audit:1').error).toBe('fallback')
    await store.startJob('audit:1', () => Promise.resolve(null))
    expect(store.getRun('audit:1').report).toEqual({})
    expect(store.getRun('audit:1').loaded).toBe(true)
  })
})
