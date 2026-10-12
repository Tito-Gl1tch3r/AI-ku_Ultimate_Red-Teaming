import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import { createI18n } from 'vue-i18n'

// Must mock the user store before importing the page - quality-assurance.js calls
// useUserStore() at module scope (`const userStore = useUserStore();`).
const { mockUserStore } = vi.hoisted(() => ({
  mockUserStore: {
    isAllowed: vi.fn(() => true)
  }
}))
vi.mock('@/stores/user', () => ({
  useUserStore: vi.fn(() => mockUserStore)
}))

vi.mock('@/boot/i18n', () => ({
  $t: (key) => key
}))

vi.mock('quasar', async () => {
  const actual = await vi.importActual('quasar')
  return {
    ...actual,
    Notify: { create: vi.fn() },
    Dialog: { create: vi.fn(() => ({ onOk: vi.fn(() => ({ onCancel: vi.fn(), onDismiss: vi.fn() })) })) }
  }
})

vi.mock('@/services/data', () => ({
  default: {
    getAiIntegration: vi.fn(),
    updateAiIntegration: vi.fn()
  }
}))

import QualityAssurancePage from '@/pages/data/quality-assurance/index.vue'
import DataService from '@/services/data'
import { Notify, Dialog } from 'quasar'

describe('Quality Assurance Page', () => {
  let router, pinia, i18n

  const mockPayload = () => ({
    aiEnabled: true,
    qaInstructions: { content: '' },
    qaChecks: {
      completeness: true,
      references: true,
      imageCaptions: true,
      duplicates: true,
      aiDuplicates: true,
      aiUnlinkedTranslations: true,
      redaction: true,
      customer: true,
      instructions: true
    }
  })

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)

    router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/data/quality-assurance', name: 'quality-assurance', component: QualityAssurancePage }
      ]
    })

    i18n = createI18n({
      legacy: false,
      globalInjection: true,
      locale: 'en-US',
      fallbackLocale: 'en-US',
      messages: { 'en-US': {} }
    })

    vi.clearAllMocks()
    mockUserStore.isAllowed.mockReturnValue(true)

    DataService.getAiIntegration.mockResolvedValue({ data: { datas: mockPayload() } })
    DataService.updateAiIntegration.mockResolvedValue({ data: { datas: mockPayload() } })
  })

  const createWrapper = (options = {}) => {
    return mount(QualityAssurancePage, {
      props: { ...(options.props || {}) },
      global: {
        plugins: [pinia, router, i18n],
        stubs: {
          'q-card': true,
          'q-card-section': true,
          'q-card-actions': true,
          'q-spinner': true,
          'q-banner': true,
          'q-separator': true,
          'q-item': true,
          'q-item-label': true,
          'q-item-section': true,
          'q-avatar': true,
          'q-expansion-item': true,
          'q-input': true,
          'q-toggle': true,
          'q-btn': true,
          'q-chip': true,
          'q-icon': true,
          'q-space': true,
          ...(options.stubs || {})
        },
        mocks: {
          $t: (key) => key,
          ...(options.mocks || {})
        }
      }
    })
  }

  describe('Initialization', () => {
    it('should fetch AI integration data on mount', async () => {
      createWrapper()
      await wrapper_flushPromises()

      expect(DataService.getAiIntegration).toHaveBeenCalled()
    })

    it('should render QA in an open page layout (no legacy save card)', async () => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      expect(wrapper.find('.qa-settings-card').exists()).toBe(false)
      expect(wrapper.text()).toContain('aiIntegration.pageTitleQa')
      expect(wrapper.text()).toContain('aiIntegration.qa.description')
    })

    it('should show the built-in checks even when AI integration is disabled', async () => {
      const payload = mockPayload()
      payload.aiEnabled = false
      DataService.getAiIntegration.mockResolvedValue({ data: { datas: payload } })

      // Render the banner's default slot so its text is assertable (boolean stubs
      // drop slot content in this suite).
      const wrapper = createWrapper({
        stubs: { 'q-banner': { template: '<div><slot /></div>' } }
      })
      await wrapper_flushPromises()

      expect(wrapper.vm.aiEnabled).toBe(false)
      // Page renders (built-in checks section), rather than being replaced by a
      // whole-page "AI disabled" banner.
      expect(wrapper.text()).toContain('aiIntegration.tabProgrammaticChecks')
      // AI checks section shows the light-grey "AI disabled" banner with a Settings link.
      expect(wrapper.text()).toContain('aiIntegration.qa.aiChecksDisabledBefore')
      expect(wrapper.text()).toContain('aiIntegration.qa.aiChecksDisabledLink')
      expect(wrapper.find('a[href="/settings"]').exists()).toBe(true)
    })
  })

  describe('QA checks', () => {
    it('should label check scopes for audit-vs-vulnerability', () => {
      const wrapper = createWrapper()
      expect(wrapper.vm.scopeLabel('audit')).toBe('aiIntegration.qa.scopeAudit')
      expect(wrapper.vm.scopeLabel('vulnerability')).toBe('aiIntegration.qa.scopeVulnerability')
    })

    it('should mark only duplicate-detection checks as vulnerability-only', async () => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      const byKey = Object.fromEntries(
        [...wrapper.vm.programmaticQaCheckOptions, ...wrapper.vm.aiQaCheckOptions].map((check) => [check.key, check.scopes])
      )

      expect(byKey.duplicates).toEqual(['vulnerability'])
      expect(byKey.aiDuplicates).toEqual(['vulnerability'])
      expect(byKey.aiUnlinkedTranslations).toEqual(['vulnerability'])
      expect(byKey.completeness).toEqual(['audit', 'vulnerability'])
      expect(byKey.redaction).toEqual(['audit', 'vulnerability'])
      expect(byKey.customer).toEqual(['audit', 'vulnerability'])
      expect(byKey.instructions).toEqual(['audit', 'vulnerability'])
    })

    it('should save a toggled check immediately without overwriting instruction edits', async () => {
      const response = mockPayload()
      response.qaChecks.completeness = false
      DataService.updateAiIntegration.mockResolvedValueOnce({ data: { datas: response } })
      const refresh = vi.fn().mockResolvedValue()
      const wrapper = createWrapper({ mocks: { $settings: { refresh } } })
      await wrapper_flushPromises()

      wrapper.vm.qaInstructions.content = 'Unsaved instruction edit.'
      vi.useFakeTimers()
      const save = wrapper.vm.toggleQaCheck('completeness', false)

      expect(wrapper.vm.qaToggleSaveKey).toBe('completeness')
      expect(wrapper.vm.qaToggleSaveState).toBe('saving')
      await save

      expect(DataService.updateAiIntegration).toHaveBeenCalledWith({
        qaChecks: expect.objectContaining({ completeness: false })
      })
      expect(wrapper.vm.qaChecks.completeness).toBe(false)
      expect(wrapper.vm.orig.qaChecks.completeness).toBe(false)
      expect(wrapper.vm.qaInstructions.content).toBe('Unsaved instruction edit.')
      expect(wrapper.vm.qaToggleSaveState).toBe('saved')
      expect(refresh).toHaveBeenCalled()

      vi.advanceTimersByTime(1999)
      expect(wrapper.vm.qaToggleSaveKey).toBe('completeness')
      vi.advanceTimersByTime(1)
      expect(wrapper.vm.qaToggleSaveKey).toBe(null)
      expect(wrapper.vm.qaToggleSaveState).toBe(null)
      vi.useRealTimers()
    })

    it('should roll back a toggled check when automatic saving fails', async () => {
      DataService.updateAiIntegration.mockRejectedValueOnce({ response: { data: { datas: 'Save failed' } } })
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      wrapper.vm.toggleQaCheck('completeness', false)
      await wrapper_flushPromises()

      expect(wrapper.vm.qaChecks.completeness).toBe(true)
      expect(wrapper.vm.qaToggleSaveKey).toBe(null)
      expect(wrapper.vm.qaToggleSaveState).toBe(null)
      expect(Notify.create).toHaveBeenCalledWith(expect.objectContaining({ message: 'Save failed' }))
    })

    it('should render toggle save feedback without the old save footer', async () => {
      let resolveSave
      DataService.updateAiIntegration.mockReturnValueOnce(new Promise((resolve) => {
        resolveSave = resolve
      }))
      const wrapper = createWrapper({
        stubs: {
          'q-card': { template: '<div><slot /></div>' },
          'q-card-section': { template: '<div><slot /></div>' }
        }
      })
      await wrapper_flushPromises()

      wrapper.vm.toggleQaCheck('completeness', false)
      await wrapper.vm.$nextTick()

      const savingStatus = wrapper.find('.qa-toggle-save-status')
      expect(savingStatus.classes()).toContain('text-positive')
      expect(savingStatus.text()).toBe('')
      expect(savingStatus.find('q-spinner-stub').exists()).toBe(true)
      expect(wrapper.html().indexOf('qa-toggle-save-status')).toBeLessThan(wrapper.html().indexOf('q-toggle-stub'))
      expect(wrapper.find('.ai-integration-save-bar').exists()).toBe(false)

      const response = mockPayload()
      response.qaChecks.completeness = false
      resolveSave({ data: { datas: response } })
      await wrapper_flushPromises()

      const savedStatus = wrapper.find('.qa-toggle-save-status')
      expect(savedStatus.text()).toBe('aiIntegration.qa.saved')
      expect(savedStatus.find('q-icon-stub').attributes('name')).toBe('check_circle')
    })
  })

  describe('beforeRouteLeave', () => {
    it('should call next() immediately when there are no unsaved changes', async () => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      const next = vi.fn()
      wrapper.vm.$options.beforeRouteLeave.call(wrapper.vm, { name: 'to' }, { name: 'from' }, next)

      expect(Dialog.create).not.toHaveBeenCalled()
      expect(next).toHaveBeenCalledTimes(1)
    })

    it('should open a confirm dialog when there are unsaved QA changes', async () => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      wrapper.vm.qaChecks.completeness = false
      await wrapper.vm.$nextTick()

      const next = vi.fn()
      wrapper.vm.$options.beforeRouteLeave.call(wrapper.vm, { name: 'to' }, { name: 'from' }, next)

      expect(Dialog.create).toHaveBeenCalledTimes(1)
      expect(next).not.toHaveBeenCalled()
    })
  })
})

// Helper to flush all pending promises
function wrapper_flushPromises() {
  return new Promise((resolve) => setTimeout(resolve, 50))
}
