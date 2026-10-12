import { defineStore } from 'pinia'

// Run state for QA reports, keyed by target so it survives the panel/drawer being closed,
// remounted (language-tab switch), or the route changing. Keys look like:
//   audit:<auditId>            audit report QA
//   vuln:<vulnId>:<locale>     single stored-vulnerability QA
//   all:<locale>               run-all vulnerability QA for a locale
//   draft                      the unsaved vulnerability currently in the modal
//
// A run holds the raw report payload plus its lifecycle flags; consumers build their own
// view models from `report`.
const emptyRun = () => ({
  running: false,
  loading: false,
  loaded: false,
  startedAt: null,
  scope: null,
  report: null,
  error: '',
  // Set when a run is a server-side background job (serialized job payload from the backend);
  // callers derive in-flight state from `job.state === 'running'`. The `running`/`startedAt`/
  // `scope` fields above are for the older client-owned lifecycle (`start()`) and stay null.
  job: null
})

const resolveError = (err, fallback) => {
  const datas = err?.response?.data?.datas
  if (typeof datas === 'string' && datas.trim())
    return datas

  const status = err?.response?.status
  if (status === 502 || status === 504 || err?.code === 'ECONNABORTED' || /timeout/i.test(String(err?.message || '')))
    return 'The QA request timed out. Partial results may already be saved — try running again.'

  return fallback || err?.message || ''
}

export const useQaRunsStore = defineStore('qaRuns', {
  state: () => ({
    runs: {}
  }),

  getters: {
    getRun: (state) => (key) => (key ? state.runs[key] || null : null),
    isRunning: (state) => (key) => Boolean(key && state.runs[key]?.running),
    isLoading: (state) => (key) => Boolean(key && state.runs[key]?.loading),
    startedAt: (state) => (key) => (key && state.runs[key]?.startedAt) || null,
    runScope: (state) => (key) => (key && state.runs[key]?.scope) || null,
    isJobRunning: (state) => (key) => Boolean(key && state.runs[key]?.job?.state === 'running')
  },

  actions: {
    ensureRun(key) {
      if (!this.runs[key])
        this.runs[key] = emptyRun()
      return this.runs[key]
    },

    // Fetch a cached report. Never runs while a QA run is in flight (the run owns the state),
    // and never overwrites a run that starts while the fetch is outstanding.
    async load(key, loader, { errorFallback = '' } = {}) {
      const run = this.ensureRun(key)
      if (run.running)
        return

      run.loading = true
      run.error = ''
      try {
        const data = await loader()
        if (run.running)
          return
        run.report = data || {}
        run.loaded = true
      } catch (err) {
        if (!run.running)
          run.error = resolveError(err, errorFallback)
      } finally {
        run.loading = false
      }
    },

    // Start a QA run for a target. Ignored if that target already has a run in flight
    // (double-run guard). The report stays visible while running so panels can dim it.
    // Runner may call setReport() to push partial results before finishing.
    async start(key, runner, { errorFallback = '', scope = null } = {}) {
      const run = this.ensureRun(key)
      if (run.running)
        return

      run.running = true
      run.startedAt = Date.now()
      run.scope = scope || null
      run.error = ''
      // Drop finished progress so a new run doesn't show e.g. "394 of 394" from the previous pass.
      if (run.report?.progress)
        run.report = { ...run.report, progress: null }
      try {
        const result = await runner({
          setReport: (data) => {
            run.report = data || {}
            run.loaded = true
          }
        })
        if (result !== undefined)
          run.report = result || {}
        run.loaded = true
      } catch (err) {
        run.error = resolveError(err, errorFallback)
      } finally {
        run.running = false
        run.scope = null
        run.startedAt = null
      }
    },

    // Replace a run's report directly — used by server-driven runs (the QA-all background
    // job) where progress and results arrive via socket/status fetches rather than a
    // client-owned request.
    setReport(key, data) {
      const run = this.ensureRun(key)
      run.report = data || {}
      run.loaded = true
    },

    // Start a run whose backend response is either a background job ({ job }; a *:done
    // socket handler later calls setJob/setReport) or an inline result (no `job` key).
    // Ignored while a previous run for this key is still in flight.
    async startJob(key, runner, { errorFallback = '', scope = null } = {}) {
      const run = this.ensureRun(key)
      if (run.running || run.job?.state === 'running')
        return

      run.running = true
      run.startedAt = Date.now()
      run.scope = scope || null
      run.job = null
      run.error = ''
      // Drop finished progress so a new run doesn't show stale state from a previous pass.
      if (run.report?.progress)
        run.report = { ...run.report, progress: null }

      try {
        const datas = await runner()
        if (datas?.job) {
          run.job = datas.job
        } else {
          run.job = null
          run.report = datas || {}
          run.loaded = true
        }
      } catch (err) {
        run.error = resolveError(err, errorFallback)
      } finally {
        run.running = false
        run.startedAt = null
        run.scope = null
      }
    },

    // Update a run's job status - called from the *:done socket handler once a background
    // job started by startJob() finishes.
    setJob(key, job) {
      const run = this.ensureRun(key)
      run.job = job
    },

    reset(key) {
      if (this.runs[key])
        this.runs[key] = emptyRun()
    }
  }
})
