import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { Dialog } from 'quasar'
import { useAiGenerationStore } from '@/stores/ai-generation'
import { runAfterAiGenerationCheck, confirmRouterLeaveIfAiGenerating } from '@/composables/confirmLeaveIfAiGenerating'

vi.mock('@/stores/audit-qa', () => ({
  useAuditQaStore: () => ({
    close: vi.fn()
  })
}))

vi.mock('@/boot/i18n', () => ({
  $t: (key) => key
}))

vi.mock('quasar', async () => {
  const actual = await vi.importActual('quasar')
  return {
    ...actual,
    Dialog: {
      create: vi.fn(() => ({
        onOk: vi.fn(() => ({ onCancel: vi.fn() })),
        onCancel: vi.fn()
      }))
    }
  }
})

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

describe('runAfterAiGenerationCheck', () => {
  it('leaves immediately with no dialog when there is no session at all', () => {
    const onLeave = vi.fn()
    runAfterAiGenerationCheck(onLeave)

    expect(Dialog.create).not.toHaveBeenCalled()
    expect(onLeave).toHaveBeenCalled()
  })

  it('confirms before leaving while a session is still in progress', () => {
    const store = useAiGenerationStore()
    store.openSession({ title: 'AI', lockKey: 'finding:1:description', mode: 'field' })
    const onLeave = vi.fn()

    runAfterAiGenerationCheck(onLeave)

    expect(Dialog.create).toHaveBeenCalled()
    expect(onLeave).not.toHaveBeenCalled()
    expect(store.sessionConfig).not.toBeNull()
  })

})

describe('confirmRouterLeaveIfAiGenerating', () => {
  it('calls next() when there is nothing to confirm', () => {
    const next = vi.fn()
    confirmRouterLeaveIfAiGenerating(next)

    expect(next).toHaveBeenCalledWith()
  })
})
