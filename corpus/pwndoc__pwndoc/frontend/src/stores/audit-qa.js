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

export const useAuditQaStore = defineStore('auditQa', {
  state: () => ({
    drawerOpen: false,
    auditId: null,
    severityFilter: 'all'
  }),

  getters: {
    qaKey: (state) => (state.auditId ? `audit:${state.auditId}` : null),

    // AI-scope runs are a server-side background job (job-driven, survives reloads/nav);
    // programmatic-only scope has no LLM call and resolves inline via qa-runs.js's `running`.
    running() {
      const qaRuns = useQaRunsStore()
      return qaRuns.isRunning(this.qaKey) || qaRuns.isJobRunning(this.qaKey)
    },

    // When the run started (ms), for the "in progress since …" indicator.
    startedAt() {
      const run = useQaRunsStore().getRun(this.qaKey)
      if (run?.job?.startedAt)
        return new Date(run.job.startedAt).getTime()
      return run?.startedAt || null
    },

    runScope() {
      const run = useQaRunsStore().getRun(this.qaKey)
      return run?.job?.scope || run?.scope || null
    },

    // Full-panel spinner only while first fetching a report with nothing to show yet.
    loading() {
      return useQaRunsStore().isLoading(this.qaKey) && !this.hasReport && !this.running
    },

    errorMessage() {
      const run = useQaRunsStore().getRun(this.qaKey)
      if (run?.job?.state === 'failed' && run.job.error)
        return run.job.error
      return run?.error || ''
    },

    reportViewModel() {
      return buildQaReportViewModel(useQaRunsStore().getRun(this.qaKey)?.report || {})
    },

    issues() { return this.reportViewModel.issues },
    counts() { return this.reportViewModel.counts || emptyCounts() },
    hasReport() { return this.reportViewModel.hasReport },
    outdated() { return this.reportViewModel.outdated },
    ranAt() { return this.reportViewModel.ranAt },
    programmaticRanAt() { return this.reportViewModel.programmaticRanAt },
    aiRanAt() { return this.reportViewModel.aiRanAt },
    cached() { return this.reportViewModel.cached },

    filteredIssues(state) {
      if (state.severityFilter === 'all')
        return this.issues

      return this.issues.filter((issue) => issue.severity === state.severityFilter)
    },

    // Whether a run is in flight for a given audit — used by toolbar buttons whose panel
    // may be closed (so a closed drawer still signals activity).
    runningForAudit: () => (auditId) => {
      const qaRuns = useQaRunsStore()
      const key = auditId ? `audit:${auditId}` : null
      return qaRuns.isRunning(key) || qaRuns.isJobRunning(key)
    }
  },

  actions: {
    open(auditId) {
      const aiStore = useAiGenerationStore()
      if (aiStore.drawerOpen)
        aiStore.closeDrawer()

      this.auditId = auditId
      this.drawerOpen = true
      this.severityFilter = 'all'
      // Re-attach to any in-flight run; loadQa is a no-op while a run is running.
      this.loadQa(auditId)
    },

    close() {
      this.drawerOpen = false
    },

    loadQa(auditId) {
      this.auditId = auditId
      const key = `audit:${auditId}`
      const qaRuns = useQaRunsStore()
      return qaRuns.load(
        key,
        () => AiService.runAuditQa(auditId, { loadOnly: true }).then((response) => {
          const datas = response.data.datas || {}
          qaRuns.setJob(key, datas.job || null)
          return datas
        }),
        { errorFallback: $t('auditQa.failed') }
      )
    },

    // AI scope runs as a background job (report arrives via the audit-qa:done socket event);
    // programmatic-only scope resolves inline - startJob() handles both shapes.
    runQa(auditId, scope = 'all', provider = '') {
      this.auditId = auditId
      this.severityFilter = 'all'
      const params = { scope }
      if (provider)
        params.provider = provider
      return useQaRunsStore().startJob(
        `audit:${auditId}`,
        () => AiService.runAuditQa(auditId, params).then((response) => response.data?.datas || {}),
        { errorFallback: $t('auditQa.failed'), scope }
      )
    },

    // Bound to the audit-qa:done socket event (see pages/audits/edit/index.vue). Refetches
    // the persisted report once the background job finishes.
    handleSocketDone(payload) {
      if (!payload || payload.auditId !== this.auditId)
        return

      useQaRunsStore().setJob(this.qaKey, payload)
      this.loadQa(this.auditId)
    },

    setSeverityFilter(filter) {
      this.severityFilter = filter
    }
  }
})
