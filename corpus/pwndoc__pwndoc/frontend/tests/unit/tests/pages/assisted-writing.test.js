import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import { createI18n } from 'vue-i18n'

// Must mock the user store before importing the page - assisted-writing.js calls
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

import AssistedWritingPage from '@/pages/data/assisted-writing/index.vue'
import DataService from '@/services/data'
import { Notify, Dialog } from 'quasar'

describe('Assisted Writing Page', () => {
  let router, pinia, i18n

  const mockPromptMappings = () => ([
    {
      entityType: 'finding',
      fieldKey: 'description',
      fieldLabel: 'Description',
      outputType: 'html',
      source: 'builtin',
      customFieldDisplay: null,
      customFieldDisplaySub: null,
      enabled: true,
      prompt: 'Describe the finding thoroughly.',
      usingDefaultPrompt: false
    },
    {
      entityType: 'finding',
      fieldKey: 'custom-field:abc123',
      fieldLabel: 'Finding Custom Field: Severity Rationale',
      outputType: 'text',
      source: 'custom-field',
      customFieldDisplay: 'finding',
      customFieldDisplaySub: '',
      enabled: true,
      prompt: 'Explain why this severity was chosen.',
      usingDefaultPrompt: true
    },
    {
      entityType: 'finding',
      fieldKey: 'custom-field:web1',
      fieldLabel: 'Finding Custom Field: Application ID',
      outputType: 'text',
      source: 'custom-field',
      customFieldDisplay: 'vulnerability',
      customFieldDisplaySub: 'Web',
      enabled: true,
      prompt: 'Extract the application identifier.',
      usingDefaultPrompt: false
    },
    {
      entityType: 'finding',
      fieldKey: 'custom-field:vall1',
      fieldLabel: 'Finding Custom Field: MFA Enabled',
      outputType: 'text',
      source: 'custom-field',
      customFieldDisplay: 'vulnerability',
      customFieldDisplaySub: '',
      enabled: false,
      prompt: 'State whether MFA is enabled.',
      usingDefaultPrompt: true
    },
    {
      entityType: 'section',
      fieldKey: 'custom-field:sec1',
      fieldLabel: 'Section Custom Field: Executive Overview',
      outputType: 'html',
      source: 'custom-field',
      customFieldDisplay: 'section',
      customFieldDisplaySub: 'Executive Summary',
      enabled: true,
      prompt: 'Summarize for executives.',
      usingDefaultPrompt: true
    }
  ])

  const mockGlobalPrompts = () => ([
    { id: 'g1', label: 'Tone', prompt: 'Write in a formal, professional tone.', enabled: true },
    { id: 'g2', label: 'Audience', prompt: 'Write for a technical audience.', enabled: true }
  ])

  const mockPayload = () => ({
    aiEnabled: true,
    promptMappings: mockPromptMappings(),
    globalPrompts: mockGlobalPrompts(),
    redactionGuidelines: { content: '' },
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
        { path: '/data/assisted-writing', name: 'assisted-writing', component: AssistedWritingPage }
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
    return mount(AssistedWritingPage, {
      props: { ...(options.props || {}) },
      global: {
        plugins: [pinia, router, i18n],
        stubs: {
          'q-card': true,
          'q-card-section': true,
          'q-card-actions': true,
          'q-spinner': true,
          'q-banner': true,
          'q-tabs': true,
          'q-tab': true,
          'q-separator': true,
          'q-tab-panels': true,
          'q-tab-panel': true,
          'q-list': true,
          'q-tree': true,
          'q-table': true,
          'q-markup-table': true,
          'q-tr': true,
          'q-td': true,
          'q-item': true,
          'q-item-label': true,
          'q-item-section': true,
          'q-avatar': true,
          'q-expansion-item': true,
          'q-input': true,
          'q-toggle': true,
          'q-checkbox': true,
          'q-btn': true,
          'q-chip': true,
          'q-badge': true,
          'q-icon': true,
          'q-space': true,
          'q-breadcrumbs': true,
          'q-breadcrumbs-el': true,
          draggable: true,
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

    it('should populate promptMappings and globalPrompts from the response', async () => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      expect(wrapper.vm.promptMappings).toHaveLength(5)
      expect(wrapper.vm.globalPrompts).toHaveLength(2)
      expect(wrapper.vm.selectedNode).toBe('generic')
    })

    it('should render the assisted writing title', async () => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      expect(wrapper.text()).toContain('aiIntegration.pageTitleWriting')
    })

    it('should surface loading failures', async () => {
      DataService.getAiIntegration.mockRejectedValueOnce({ response: { data: { datas: 'Load failed' } } })
      createWrapper()
      await wrapper_flushPromises()
      expect(Notify.create).toHaveBeenCalledWith(expect.objectContaining({ message: 'Load failed' }))
    })
  })

  describe('promptTreeNodes', () => {
    it('should build generic, findings, vulnerabilities and sections nodes with counts', async () => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      const byKey = Object.fromEntries(wrapper.vm.promptTreeNodes.map((node) => [node.key, node]))

      expect(byKey.generic.count).toBe(2)

      expect(byKey.findings.count).toBe(2)
      const findingsChildren = Object.fromEntries(byKey.findings.children.map((node) => [node.key, node]))
      expect(findingsChildren['findings:builtin'].count).toBe(1)
      expect(findingsChildren['findings:all'].count).toBe(1)

      expect(byKey.vulnerabilities.count).toBe(2)
      const vulnChildren = Object.fromEntries(byKey.vulnerabilities.children.map((node) => [node.key, node]))
      expect(vulnChildren['vulnerabilities:all'].count).toBe(1)
      expect(vulnChildren['vulnerabilities:cat:Web'].count).toBe(1)
      expect(vulnChildren['vulnerabilities:cat:Web'].label).toBe('Web')

      expect(byKey.sections.count).toBe(1)
      expect(byKey.sections.children[0].key).toBe('sections:sub:Executive Summary')
    })

    it('should hide empty nodes', async () => {
      DataService.getAiIntegration.mockResolvedValue({
        data: {
          datas: {
            ...mockPayload(),
            promptMappings: mockPromptMappings().filter((mapping) => mapping.entityType !== 'section')
          }
        }
      })
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      const keys = wrapper.vm.promptTreeNodes.map((node) => node.key)
      expect(keys).not.toContain('sections')
    })

    it('should filter by category name and hide nodes without a matching label', async () => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      wrapper.vm.treeFilter = 'web'
      await wrapper.vm.$nextTick()

      const byKey = Object.fromEntries(wrapper.vm.promptTreeNodes.map((node) => [node.key, node]))
      expect(byKey.generic).toBeUndefined()
      expect(byKey.findings).toBeUndefined()
      expect(byKey.sections).toBeUndefined()
      expect(byKey.vulnerabilities.children.map((node) => node.key)).toEqual(['vulnerabilities:cat:Web'])
    })

    it('should show every descendant once a parent node name matches', async () => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      // The i18n mock returns the translation key verbatim, so this matches the
      // "nodeVulnerabilities" node label rather than any field or category content.
      wrapper.vm.treeFilter = 'vulnerabilities'
      await wrapper.vm.$nextTick()

      const byKey = Object.fromEntries(wrapper.vm.promptTreeNodes.map((node) => [node.key, node]))
      expect(byKey.generic).toBeUndefined()
      expect(byKey.findings).toBeUndefined()
      expect(byKey.vulnerabilities.children.map((node) => node.key)).toEqual([
        'vulnerabilities:all',
        'vulnerabilities:cat:Web'
      ])
    })

    it('should not match field or generic prompt content, only node labels', async () => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      // 'application' only appears inside a field label ("Application ID"), and 'tone'
      // only appears as a generic prompt's label - neither is a tree node name.
      wrapper.vm.treeFilter = 'application'
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.promptTreeNodes).toEqual([])

      wrapper.vm.treeFilter = 'tone'
      await wrapper.vm.$nextTick()
      expect(wrapper.vm.promptTreeNodes).toEqual([])
    })

    it('should not throw when the search input is cleared to null', async () => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      wrapper.vm.treeFilter = 'web'
      await wrapper.vm.$nextTick()

      // Quasar's clearable q-input emits null (not '') when its clear icon is clicked.
      wrapper.vm.treeFilter = null
      await wrapper.vm.$nextTick()

      expect(() => wrapper.vm.promptTreeNodes).not.toThrow()
      expect(wrapper.vm.promptTreeNodes.map((node) => node.key)).toEqual(['generic', 'findings', 'vulnerabilities', 'sections'])
    })
  })

  describe('selectedNodeMappings / fieldTableRows', () => {
    it('should aggregate all descendants when a parent node is selected', async () => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      wrapper.vm.selectedNode = 'vulnerabilities'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.selectedNodeMappings.map((mapping) => mapping.fieldKey).sort()).toEqual([
        'custom-field:vall1',
        'custom-field:web1'
      ])
    })

    it('should return only the leaf mappings when a leaf is selected', async () => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      wrapper.vm.selectedNode = 'findings:builtin'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.selectedNodeMappings.map((mapping) => mapping.fieldKey)).toEqual(['description'])
    })

    it('should filter table rows by the display label', async () => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      wrapper.vm.selectedNode = 'findings'
      await wrapper.vm.$nextTick()
      wrapper.vm.tableFilter = 'severity'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.fieldTableRows).toHaveLength(1)
      expect(wrapper.vm.fieldTableRows[0].fieldKey).toBe('custom-field:abc123')
    })

    it('should reset the table filter and generic selection when the node changes', async () => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      wrapper.vm.tableFilter = 'tone'
      wrapper.vm.selectedGenericIds = ['g1']
      wrapper.vm.selectedNode = 'findings'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.tableFilter).toBe('')
      expect(wrapper.vm.selectedGenericIds).toEqual([])
    })
  })

  describe('fieldDisplayLabel', () => {
    it('should strip the "Finding Custom Field: " prefix', async () => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      const mapping = { fieldLabel: 'Finding Custom Field: Severity Rationale' }
      expect(wrapper.vm.fieldDisplayLabel(mapping)).toBe('Severity Rationale')
    })

    it('should strip the "Section Custom Field: " prefix', async () => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      const mapping = { fieldLabel: 'Section Custom Field: Executive Summary' }
      expect(wrapper.vm.fieldDisplayLabel(mapping)).toBe('Executive Summary')
    })

    it('should leave builtin field labels untouched', async () => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      const mapping = { fieldLabel: 'Description' }
      expect(wrapper.vm.fieldDisplayLabel(mapping)).toBe('Description')
    })
  })

  describe('outputTypeLabel', () => {
    it.each([
      ['html', 'aiIntegration.prompts.outputTypeHtml'],
      ['array', 'aiIntegration.prompts.outputTypeList'],
      ['text', 'aiIntegration.prompts.outputTypeText']
    ])('should map %s to its i18n key', async (outputType, expected) => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      expect(wrapper.vm.outputTypeLabel(outputType)).toBe(expected)
    })

    it('should fall back to the raw output type for anything else', async () => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      expect(wrapper.vm.outputTypeLabel('markdown')).toBe('markdown')
      expect(wrapper.vm.outputTypeLabel(undefined)).toBe(undefined)
    })
  })

  describe('toggleFieldEnabled', () => {
    it('should persist a single mapping immediately', async () => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      const mapping = wrapper.vm.promptMappings.find((entry) => entry.fieldKey === 'description')
      wrapper.vm.toggleFieldEnabled(mapping, false)
      await wrapper_flushPromises()

      expect(DataService.updateAiIntegration).toHaveBeenCalledTimes(1)
      const payload = DataService.updateAiIntegration.mock.calls[0][0]
      expect(payload.promptMappings).toEqual([{
        entityType: 'finding',
        fieldKey: 'description',
        enabled: false,
        prompt: 'Describe the finding thoroughly.'
      }])
    })

    it('should send an empty prompt for fields still on the default so they keep following it', async () => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      const mapping = wrapper.vm.promptMappings.find((entry) => entry.fieldKey === 'custom-field:abc123')
      wrapper.vm.toggleFieldEnabled(mapping, false)
      await wrapper_flushPromises()

      const payload = DataService.updateAiIntegration.mock.calls[0][0]
      expect(payload.promptMappings[0].prompt).toBe('')
    })

    it('should revert the toggle when the save fails', async () => {
      DataService.updateAiIntegration.mockRejectedValue({ response: { data: { datas: 'nope' } } })
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      const mapping = wrapper.vm.promptMappings.find((entry) => entry.fieldKey === 'description')
      wrapper.vm.toggleFieldEnabled(mapping, false)
      await wrapper_flushPromises()

      expect(mapping.enabled).toBe(true)
      expect(Notify.create).toHaveBeenCalledWith(expect.objectContaining({ color: 'negative' }))
    })

    it('should not persist anything without edit permission', async () => {
      mockUserStore.isAllowed.mockReturnValue(false)
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      wrapper.vm.toggleFieldEnabled(wrapper.vm.promptMappings[0], false)
      await wrapper.vm.$nextTick()

      expect(DataService.updateAiIntegration).not.toHaveBeenCalled()
    })
  })

  describe('generic prompts', () => {
    it('should persist the full list, preserving order, when toggling one prompt', async () => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      wrapper.vm.toggleGenericEnabled(wrapper.vm.globalPrompts[1], false)
      await wrapper_flushPromises()

      const payload = DataService.updateAiIntegration.mock.calls[0][0]
      expect(payload.globalPrompts.map((entry) => entry.id)).toEqual(['g1', 'g2'])
      expect(payload.globalPrompts[1].enabled).toBe(false)
    })

    it('should persist a reorder without sorting by label', async () => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      const reversed = [...wrapper.vm.globalPrompts].reverse()
      wrapper.vm.persistGenericOrder(reversed)
      await wrapper_flushPromises()

      const payload = DataService.updateAiIntegration.mock.calls[0][0]
      expect(payload.globalPrompts.map((entry) => entry.id)).toEqual(['g2', 'g1'])
    })

    it('should restore the previous order when the reorder save fails', async () => {
      DataService.updateAiIntegration.mockRejectedValue({ response: { data: { datas: 'nope' } } })
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      const reversed = [...wrapper.vm.globalPrompts].reverse()
      wrapper.vm.persistGenericOrder(reversed)
      await wrapper_flushPromises()

      expect(wrapper.vm.globalPrompts.map((entry) => entry.id)).toEqual(['g1', 'g2'])
    })

    it('should not reorder while a table filter is active', async () => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      wrapper.vm.tableFilter = 'tone'
      wrapper.vm.persistGenericOrder([...wrapper.vm.globalPrompts].reverse())
      await wrapper.vm.$nextTick()

      expect(DataService.updateAiIntegration).not.toHaveBeenCalled()
      expect(wrapper.vm.canReorderGeneric).toBe(false)
    })

    it('should delete the selected prompts after confirmation', async () => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      let confirmDelete
      Dialog.create.mockImplementationOnce(() => ({
        onOk(cb) {
          confirmDelete = cb
          return this
        }
      }))

      wrapper.vm.selectedGenericIds = ['g1']
      wrapper.vm.deleteSelectedGenericPrompts()
      expect(DataService.updateAiIntegration).not.toHaveBeenCalled()

      confirmDelete()
      await wrapper_flushPromises()

      const payload = DataService.updateAiIntegration.mock.calls[0][0]
      expect(payload.globalPrompts.map((entry) => entry.id)).toEqual(['g2'])
    })
  })

  describe('editor panel', () => {
    it('should switch tree nodes and close a clean editor immediately', async () => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      wrapper.vm.selectTreeNode('findings')
      expect(wrapper.vm.selectedNode).toBe('findings')

      wrapper.vm.openFieldEditor(wrapper.vm.promptMappings[0])
      wrapper.vm.closeEditor()
      expect(wrapper.vm.editor).toBe(null)
    })

    it('should open a field editor with a working copy and breadcrumbs', async () => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      const mapping = wrapper.vm.promptMappings.find((entry) => entry.fieldKey === 'custom-field:web1')
      wrapper.vm.openFieldEditor(mapping)
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.editor.kind).toBe('field')
      expect(wrapper.vm.editor.prompt).toBe('Extract the application identifier.')
      expect(wrapper.vm.editorDirty).toBe(false)
      expect(wrapper.vm.editorBreadcrumbs).toEqual([
        'aiIntegration.prompts.nodeVulnerabilities',
        'Web',
        'Application ID'
      ])
    })

    it('should become dirty when the working copy changes and save a single mapping', async () => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      const mapping = wrapper.vm.promptMappings.find((entry) => entry.fieldKey === 'description')
      wrapper.vm.openFieldEditor(mapping)
      wrapper.vm.editor.prompt = 'New description prompt.'
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.editorDirty).toBe(true)
      expect(wrapper.vm.editorCanSave).toBe(true)

      wrapper.vm.saveEditor()
      await wrapper_flushPromises()

      const payload = DataService.updateAiIntegration.mock.calls[0][0]
      expect(payload.promptMappings).toEqual([{
        entityType: 'finding',
        fieldKey: 'description',
        enabled: true,
        prompt: 'New description prompt.'
      }])
    })

    it('should require label and prompt before saving a new generic prompt', async () => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      wrapper.vm.openNewGenericEditor()
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.editor.isNew).toBe(true)
      expect(wrapper.vm.editorCanSave).toBe(false)

      wrapper.vm.editor.label = 'Spellcheck'
      expect(wrapper.vm.editorCanSave).toBe(false)

      wrapper.vm.editor.prompt = 'Fix spelling and grammar.'
      expect(wrapper.vm.editorCanSave).toBe(true)

      wrapper.vm.saveEditor()
      await wrapper_flushPromises()

      const payload = DataService.updateAiIntegration.mock.calls[0][0]
      expect(payload.globalPrompts).toHaveLength(3)
      expect(payload.globalPrompts[2]).toMatchObject({ label: 'Spellcheck', prompt: 'Fix spelling and grammar.', enabled: true })
    })

    it('should append new generic prompts at the end so chat order follows the list', async () => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      wrapper.vm.openNewGenericEditor()
      wrapper.vm.editor.label = 'Last'
      wrapper.vm.editor.prompt = 'Prompt'
      wrapper.vm.saveEditor()
      await wrapper_flushPromises()

      const payload = DataService.updateAiIntegration.mock.calls[0][0]
      expect(payload.globalPrompts.map((entry) => entry.label)).toEqual(['Tone', 'Audience', 'Last'])
    })

    it('should reset a customized field prompt to the default after confirmation', async () => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      let confirmReset
      Dialog.create.mockImplementationOnce(() => ({
        onOk(cb) {
          confirmReset = cb
          return this
        }
      }))

      const mapping = wrapper.vm.promptMappings.find((entry) => entry.fieldKey === 'description')
      wrapper.vm.openFieldEditor(mapping)
      wrapper.vm.resetFieldPrompt()
      expect(DataService.updateAiIntegration).not.toHaveBeenCalled()

      confirmReset()
      await wrapper_flushPromises()

      const payload = DataService.updateAiIntegration.mock.calls[0][0]
      expect(payload.promptMappings[0].prompt).toBe('')
    })

    it('should confirm before replacing a dirty editor with another row', async () => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      const first = wrapper.vm.promptMappings[0]
      const second = wrapper.vm.promptMappings[1]
      wrapper.vm.openFieldEditor(first)
      wrapper.vm.editor.prompt = 'Unsaved edit.'
      await wrapper.vm.$nextTick()

      let confirmDiscard
      Dialog.create.mockImplementationOnce(() => ({
        onOk(cb) {
          confirmDiscard = cb
          return this
        },
        onDismiss() {
          return this
        }
      }))

      wrapper.vm.openFieldEditor(second)
      expect(wrapper.vm.editor.mappingKey).toBe('finding:description')

      confirmDiscard()
      expect(wrapper.vm.editor.mappingKey).toBe('finding:custom-field:abc123')
    })

    it('should delete the generic prompt open in the editor after confirmation', async () => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      let confirmDelete
      Dialog.create.mockImplementationOnce(() => ({
        onOk(cb) {
          confirmDelete = cb
          return this
        }
      }))

      wrapper.vm.openGenericEditor(wrapper.vm.globalPrompts[0])
      wrapper.vm.deleteEditorGenericPrompt()
      confirmDelete()
      await wrapper_flushPromises()

      const payload = DataService.updateAiIntegration.mock.calls[0][0]
      expect(payload.globalPrompts.map((entry) => entry.id)).toEqual(['g2'])
      expect(wrapper.vm.editor).toBe(null)
    })
  })

  describe('applyPayload prompts-only refresh', () => {
    it('should not clobber unsaved guideline edits when a prompt save returns the full payload', async () => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      wrapper.vm.redactionGuidelines.content = 'Unsaved guideline edit.'
      const mapping = wrapper.vm.promptMappings.find((entry) => entry.fieldKey === 'description')
      wrapper.vm.toggleFieldEnabled(mapping, false)
      await wrapper_flushPromises()

      expect(wrapper.vm.redactionGuidelines.content).toBe('Unsaved guideline edit.')
      expect(wrapper.vm.hasGuidelineChanges).toBe(true)
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

    it('should open a confirm dialog and only call next() once onOk fires when the editor has unsaved changes', async () => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      wrapper.vm.openFieldEditor(wrapper.vm.promptMappings[0])
      wrapper.vm.editor.prompt = 'Unsaved edit.'
      await wrapper.vm.$nextTick()

      let confirmLeave
      Dialog.create.mockImplementationOnce(() => ({
        onOk(cb) {
          confirmLeave = cb
          return this
        }
      }))

      const next = vi.fn()
      wrapper.vm.$options.beforeRouteLeave.call(wrapper.vm, { name: 'to' }, { name: 'from' }, next)

      expect(Dialog.create).toHaveBeenCalledTimes(1)
      expect(next).not.toHaveBeenCalled()

      confirmLeave()

      expect(next).toHaveBeenCalledTimes(1)
    })

    it('should open a confirm dialog when there are unsaved guideline changes', async () => {
      const wrapper = createWrapper()
      await wrapper_flushPromises()

      wrapper.vm.redactionGuidelines.content = 'New redaction guidance.'
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
