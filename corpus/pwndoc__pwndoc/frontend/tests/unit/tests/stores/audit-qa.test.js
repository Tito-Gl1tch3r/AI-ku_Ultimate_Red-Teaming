import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/boot/i18n', () => ({ $t: (key) => key }))
vi.mock('@/services/ai', () => ({ default: { runAuditQa: vi.fn() } }))

import AiService from '@/services/ai'
import { useAiGenerationStore } from '@/stores/ai-generation'
import { useAuditQaStore } from '@/stores/audit-qa'
import { useQaRunsStore } from '@/stores/qa-runs'

describe('audit-qa store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('opens the audit drawer, closes AI, resets filters and loads the cached report', async () => {
    AiService.runAuditQa.mockResolvedValue({ data: { datas: { job: null, issues: [], ranAt: 'now' } } })
    const ai = useAiGenerationStore()
    ai.drawerOpen = true
    const close = vi.spyOn(ai, 'closeDrawer')
    const store = useAuditQaStore()
    store.severityFilter = 'error'

    await store.open('a1')

    expect(close).toHaveBeenCalled()
    expect(store.drawerOpen).toBe(true)
    expect(store.qaKey).toBe('audit:a1')
    expect(store.severityFilter).toBe('all')
    expect(AiService.runAuditQa).toHaveBeenCalledWith('a1', { loadOnly: true })
    expect(useQaRunsStore().getRun('audit:a1').job).toBeNull()
    store.close()
    expect(store.drawerOpen).toBe(false)
  })

  it('starts inline and provider-backed runs with the requested scope', async () => {
    AiService.runAuditQa.mockResolvedValueOnce({ data: { datas: { issues: [] } } })
    const store = useAuditQaStore()
    await store.runQa('a1', 'programmatic')
    expect(AiService.runAuditQa).toHaveBeenLastCalledWith('a1', { scope: 'programmatic' })

    AiService.runAuditQa.mockResolvedValueOnce({ data: { datas: { job: { state: 'running', startedAt: '2026-01-01' } } } })
    await store.runQa('a1', 'all', 'openai')
    expect(AiService.runAuditQa).toHaveBeenLastCalledWith('a1', { scope: 'all', provider: 'openai' })
    expect(store.running).toBe(true)
    expect(store.startedAt).toBe(new Date('2026-01-01').getTime())
  })

  it('derives report fields, filters issues, and reports failed jobs', () => {
    const store = useAuditQaStore()
    store.auditId = 'a1'
    useQaRunsStore().setReport('audit:a1', {
      issues: [{ severity: 'error' }, { severity: 'warning' }],
      ranAt: 'now', programmaticRanAt: 'p', aiRanAt: 'a', cached: true, outdated: true
    })
    store.setSeverityFilter('error')
    expect(store.filteredIssues).toEqual([{ severity: 'error' }])
    expect(store.hasReport).toBe(true)
    expect(store.counts.total).toBe(2)
    expect(store.outdated).toBe(true)
    expect(store.ranAt).toBe('now')
    expect(store.programmaticRanAt).toBe('p')
    expect(store.aiRanAt).toBe('a')
    expect(store.cached).toBe(true)

    useQaRunsStore().setJob('audit:a1', { state: 'failed', error: 'failed', scope: 'ai' })
    expect(store.errorMessage).toBe('failed')
    expect(store.runScope).toBe('ai')
    expect(store.runningForAudit('a1')).toBe(false)
    expect(store.runningForAudit(null)).toBe(false)
  })

  it('handles only matching socket completion events', async () => {
    AiService.runAuditQa.mockResolvedValue({ data: { datas: { report: true } } })
    const store = useAuditQaStore()
    store.auditId = 'a1'
    store.handleSocketDone(null)
    store.handleSocketDone({ auditId: 'other' })
    expect(AiService.runAuditQa).not.toHaveBeenCalled()

    store.handleSocketDone({ auditId: 'a1', state: 'done' })
    await Promise.resolve()
    expect(AiService.runAuditQa).toHaveBeenCalled()
  })

  it('covers empty, loading and client-owned run states', async () => {
    const store = useAuditQaStore()
    expect(store.qaKey).toBeNull()
    expect(store.startedAt).toBeNull()
    expect(store.runScope).toBeNull()
    expect(store.errorMessage).toBe('')
    expect(store.counts).toEqual({ total: 0, error: 0, warning: 0, info: 0 })
    expect(store.filteredIssues).toEqual([])

    store.auditId = 'a1'
    const qaRuns = useQaRunsStore()
    const gate = new Promise(() => {})
    qaRuns.load('audit:a1', () => gate)
    expect(store.loading).toBe(true)
    qaRuns.getRun('audit:a1').loading = false
    qaRuns.getRun('audit:a1').running = true
    qaRuns.getRun('audit:a1').startedAt = 123
    qaRuns.getRun('audit:a1').scope = 'programmatic'
    qaRuns.getRun('audit:a1').error = 'client failure'
    expect(store.running).toBe(true)
    expect(store.startedAt).toBe(123)
    expect(store.runScope).toBe('programmatic')
    expect(store.errorMessage).toBe('client failure')
    expect(store.runningForAudit('a1')).toBe(true)
  })

  it('handles sparse service response shapes', async () => {
    AiService.runAuditQa.mockResolvedValue({ data: {} })
    const store = useAuditQaStore()
    await store.loadQa('a1')
    expect(useQaRunsStore().getRun('audit:a1').report).toEqual({})
    await store.runQa('a2')
    expect(useQaRunsStore().getRun('audit:a2').report).toEqual({})
  })
})
