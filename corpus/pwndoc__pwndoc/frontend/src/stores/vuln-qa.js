import { defineStore } from 'pinia'
import AiService from '@/services/ai'
import { useAiGenerationStore } from '@/stores/ai-generation'
import { useQaRunsStore } from '@/stores/qa-runs'
import { buildQaReportViewModel } from '@/services/qa-display'
import { $t } from '@/boot/i18n'

const emptyCounts = () => ({
  total: 0,
  error: 0,
  warning: 0,
  info: 0
})

const ACTIVE_JOB_STATES = ['running', 'cancelling']

// Trailing delay between revision-triggered status refetches while a job streams
// progress — the socket payload carries counters only, the report comes from here.
const REFRESH_THROTTLE_MS = 3000

// Docked "QA all vulnerabilities" panel. Unlike audit QA, the run itself lives on the
// server (background job): `job` mirrors the last job payload from the status endpoint /
// socket events and is the source of truth for the running state, so an in-flight run
// survives page reloads and navigation.
export const useVulnQaStore = defineStore('vulnQa', {
  state: () => ({
    panelOpen: false,
    locale: null,
    severityFilter: 'all',
    textFilter: '',
    statusFilter: 'active',
    job: null,
    lastFetchedRevision: -1,
    recheckingIds: [],
    resolvingIds: [],
    dismissingKeys: [],
    error: '',
    refreshTimer: null
  }),

  getters: {
    qaKey: (state) => (state.locale ? `all:${state.locale}` : null),

    running() {
      return Boolean(this.job && ACTIVE_JOB_STATES.includes(this.job.state))
    },

    cancelling() {
      return this.job?.state === 'cancelling'
    },

    // Determinate progress for the panel: reused (cache hits) count as done work.
    progress() {
      if (!this.job)
        return null

      return {
        processed: (this.job.processed || 0) + (this.job.reused || 0),
        total: this.job.total || 0,
        reused: this.job.reused || 0,
        phase: this.job.phase || 'templates',
        catalogDone: this.job.catalogDone || 0,
        catalogTotal: this.job.catalogTotal || 0
      }
    },

    loading() {
      return useQaRunsStore().isLoading(this.qaKey) && !this.hasReport && !this.running
    },

    errorMessage(state) {
      return state.error || useQaRunsStore().getRun(this.qaKey)?.error || ''
    },

    reportData() {
      return useQaRunsStore().getRun(this.qaKey)?.report || {}
    },

    reportViewModel() {
      return buildQaReportViewModel(this.reportData)
    },

    issues() { return this.reportViewModel.issues },
    counts() { return this.reportViewModel.counts || emptyCounts() },
    hasReport() { return this.reportViewModel.hasReport },
    outdated() { return this.reportViewModel.outdated },
    programmaticRanAt() { return this.reportViewModel.programmaticRanAt },
    aiRanAt() { return this.reportViewModel.aiRanAt },

    vulnerabilityCount() { return this.reportData.vulnerabilityCount || 0 },
    checkedCount() { return this.reportData.checkedCount || 0 }
  },

  actions: {
    open(locale) {
      const aiStore = useAiGenerationStore()
      if (aiStore.drawerOpen)
        aiStore.closeDrawer()

      this.locale = locale
      this.panelOpen = true
      this.severityFilter = 'all'
      this.textFilter = ''
      this.statusFilter = 'active'
      this.error = ''
      this.loadStatus()
    },

    close() {
      this.panelOpen = false
    },

    toggle(locale) {
      if (this.panelOpen && this.locale === locale)
        this.close()
      else
        this.open(locale)
    },

    async loadStatus() {
      const locale = this.locale
      if (!locale)
        return

      const qaRuns = useQaRunsStore()
      const run = qaRuns.ensureRun(`all:${locale}`)
      run.loading = true
      try {
        const response = await AiService.getVulnerabilityQaStatus(locale)
        // The panel may have switched locale while the request was in flight.
        if (this.locale !== locale)
          return

        const datas = response.data.datas || {}
        this.job = datas.job || null
        this.error = ''
        if (this.job && Number.isFinite(this.job.revision))
          this.lastFetchedRevision = this.job.revision
        qaRuns.setReport(`all:${locale}`, datas.report || {})
      } catch (err) {
        if (this.locale === locale)
          this.error = err?.response?.data?.datas || err?.message || $t('vulnerabilityQa.failed')
      } finally {
        run.loading = false
      }
    },

    async run(scope, provider = '') {
      if (!this.locale || this.running)
        return

      this.severityFilter = 'all'
      this.error = ''
      try {
        const params = { locale: this.locale, scope }
        if (provider)
          params.provider = provider
        const response = await AiService.startVulnerabilityQaRun(params)
        const datas = response.data.datas || {}
        this.job = datas.job || null
        this.lastFetchedRevision = this.job?.revision ?? -1
      } catch (err) {
        this.error = err?.response?.data?.datas || err?.message || $t('vulnerabilityQa.failed')
      }
    },

    async cancel() {
      if (!this.locale || !this.running)
        return

      try {
        const response = await AiService.cancelVulnerabilityQaRun(this.locale)
        this.job = response.data.datas?.job || this.job
      } catch (err) {
        this.error = err?.response?.data?.datas || err?.message || $t('vulnerabilityQa.failed')
      }
    },

    // Recheck one template: the regular single-vulnerability run, which writes the same
    // unified per-vuln report the assembled QA-all view reads. Scope follows the last catalog
    // run so the recheck button never silently fires (paid) AI checks. AI scope is a server
    // background job: startJob() resolves when the job *starts*, so recheckingIds (row spinner)
    // stays set until the vuln-qa-single:done event calls finishRecheck(); programmatic-only
    // scope resolves inline.
    async recheck(vulnerabilityId) {
      if (!vulnerabilityId || this.running || this.recheckingIds.includes(vulnerabilityId))
        return

      const qaRuns = useQaRunsStore()
      const vulnKey = `vuln:${vulnerabilityId}:${this.locale}`
      const locale = this.locale
      const scope = this.job?.scope || 'all'

      this.recheckingIds = [...this.recheckingIds, vulnerabilityId]
      try {
        await qaRuns.startJob(
          vulnKey,
          async () => {
            const response = await AiService.runVulnerabilityQa({ locale, vulnerabilityId, scope })
            return response?.data?.datas || {}
          },
          { errorFallback: $t('vulnerabilityQa.recheckFailed') }
        )

        if (qaRuns.isJobRunning(vulnKey))
          return

        await this.loadStatus()
      } catch (err) {
        this.error = err?.response?.data?.datas || err?.message || $t('vulnerabilityQa.recheckFailed')
      } finally {
        if (!qaRuns.isJobRunning(vulnKey))
          this.recheckingIds = this.recheckingIds.filter((id) => id !== vulnerabilityId)
      }
    },

    // Bound to the vuln-qa-single:done socket event (see vulnerabilities.js) - clears the
    // row spinner a recheck() call left running while its background job finished.
    finishRecheck(vulnerabilityId) {
      if (this.recheckingIds.includes(vulnerabilityId))
        this.recheckingIds = this.recheckingIds.filter((id) => id !== vulnerabilityId)
    },

    // Resolve or unresolve an entire vulnerability's QA (all its issues hide until the
    // "Show resolved" toggle is on). Scoped server-side to the current content fingerprint.
    async resolveVuln(vulnerabilityId, resolved) {
      if (!vulnerabilityId || this.resolvingIds.includes(vulnerabilityId))
        return

      this.resolvingIds = [...this.resolvingIds, vulnerabilityId]
      try {
        await AiService.resolveVulnerabilityQa({
          locale: this.locale,
          vulnerabilityId: vulnerabilityId,
          resolved: resolved
        })
        await this.loadStatus()
      } catch (err) {
        this.error = err?.response?.data?.datas || err?.message || $t('vulnerabilityQa.resolveFailed')
      } finally {
        this.resolvingIds = this.resolvingIds.filter((id) => id !== vulnerabilityId)
      }
    },

    setSeverityFilter(filter) {
      this.severityFilter = filter
    },

    setTextFilter(value) {
      this.textFilter = String(value || '')
    },

    setStatusFilter(value) {
      this.statusFilter = String(value || 'active')
    },

    // Dismiss or restore one issue. Template issues carry the row's vulnerabilityId;
    // catalog issues have none and are stored on the catalog document instead.
    async setIssueDismissed(issue, vulnerabilityId, dismissed) {
      const key = issue?.key
      if (!key || this.dismissingKeys.includes(key))
        return

      this.dismissingKeys = [...this.dismissingKeys, key]
      try {
        await AiService.setVulnerabilityQaIssueDismissed({
          locale: this.locale,
          vulnerabilityId: vulnerabilityId || undefined,
          key: key,
          dismissed: dismissed
        })
        await this.loadStatus()
      } catch (err) {
        this.error = err?.response?.data?.datas || err?.message || $t('vulnerabilityQa.resolveFailed')
      } finally {
        this.dismissingKeys = this.dismissingKeys.filter((entry) => entry !== key)
      }
    },

    // Socket events carry counters only (the room is joinable without auth); when the
    // revision advances past what we last fetched, pull the report over the
    // authenticated status endpoint — throttled while the job streams.
    handleSocketProgress(payload) {
      if (!payload || payload.locale !== this.locale)
        return

      this.job = { ...(this.job || {}), ...payload }

      if (this.panelOpen && Number(payload.revision) > this.lastFetchedRevision)
        this.scheduleStatusRefresh()
    },

    handleSocketDone(payload) {
      if (!payload || payload.locale !== this.locale)
        return

      this.job = { ...(this.job || {}), ...payload }
      this.clearStatusRefresh()
      this.loadStatus()
    },

    scheduleStatusRefresh() {
      if (this.refreshTimer)
        return

      this.refreshTimer = setTimeout(() => {
        this.refreshTimer = null
        this.loadStatus()
      }, REFRESH_THROTTLE_MS)
    },

    clearStatusRefresh() {
      if (this.refreshTimer) {
        clearTimeout(this.refreshTimer)
        this.refreshTimer = null
      }
    }
  }
})
