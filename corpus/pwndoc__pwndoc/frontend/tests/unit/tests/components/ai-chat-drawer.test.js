import { beforeEach, describe, it, expect, vi } from 'vitest'
import { createTestWrapper } from '../../test-utils'
import AiChatDrawer from '@/components/ai-chat-drawer.vue'
import { useAiGenerationStore } from '@/stores/ai-generation'
import AiService from '@/services/ai'

vi.mock('@/services/ai', () => ({
  default: {
    streamGenerateFieldDraft: vi.fn()
  }
}))

vi.mock('@/boot/i18n', () => ({
  $t: (key) => key
}))

function createWrapper({ notify, settings = {} } = {}) {
  return createTestWrapper(AiChatDrawer, {
    global: {
      stubs: {
        'q-chat-message': true,
        'q-icon': true,
        'q-toolbar-title': true,
        'q-toolbar': true,
        'q-separator': true,
        'q-card-section': {
          template: '<div><slot /></div>'
        },
        'q-input': {
          props: ['readonly', 'disable', 'placeholder'],
          template: '<div><textarea :readonly="readonly" :disabled="disable" :placeholder="placeholder" /><slot name="prepend" /><slot name="append" /></div>'
        },
        'q-btn-toggle': true,
        'q-btn': {
          props: ['label'],
          template: '<button @click="$emit(\'click\')">{{ label }}<slot /></button>'
        },
        'q-menu': {
          template: '<div class="ai-chat-prompt-menu"><slot /></div>',
          methods: {
            updatePosition() {}
          }
        },
        'q-list': true,
        'q-card': true,
        'q-avatar': true,
        'q-item': true,
        'q-item-section': true,
        'q-item-label': true,
        'q-spinner-dots': true
      },
      directives: {
        'close-popup': {}
      },
      mocks: {
        $settings: settings,
        // The shared test setup doesn't install Quasar's Notify plugin, so $q.notify
        // isn't a real function unless a test needs to assert on it.
        ...(notify ? { $q: { notify } } : {})
      }
    },
    messages: {
      'en-US': {
        aiChat: {
          assistant: 'Assistant',
          apply: 'Apply',
          applyField: 'Apply to field',
          applySelection: 'Apply selection',
          insertAtCursor: 'Insert at cursor',
          anchorCollapsed: 'The selected text was removed. The draft will be inserted at its original position.',
          anchorLost: 'The original selection could not be tracked.',
          defaultPromptPlaceholder: 'Ask the AI to update this field...',
          askAnything: 'Ask anything',
          defaultPromptOption: 'Field default',
          promptSelectLabel: 'Prompt template',
          howCanIHelp: 'How can I help?',
          inputPlaceholder: 'Ask the AI to rewrite the selection...',
          originalResponse: 'Original response',
          previewChanges: 'Preview changes',
          reviewDefaultPrompt: 'Ask the AI to help with this field.',
          quickPrompts: 'Quick prompts',
          quickPromptsHint: 'Choose a prompt.',
          searchPrompts: 'Search prompts...',
          searchResults: 'Search results',
          fieldPrompt: 'Field prompt',
          defaultPromptHint: 'Uses the predefined instructions configured for this field.',
          usePrompt: 'Use',
          recentPrompts: 'Recent',
          allPrompts: 'All prompts',
          browsePrompts: 'Browse prompts',
          noPromptsFound: 'No prompts match your search.',
          selectedText: 'Selected text',
          send: 'Send',
          sendHint: 'Tip: Press Ctrl+Enter to send.',
          stop: 'Stop generating',
          generating: 'Generating content...',
          updatedDraft: 'Updated draft',
          startPrompt: 'Ask the AI to rewrite or improve the selected text.',
          you: 'You'
        }
      }
    }
  })
}

beforeEach(() => {
  localStorage.clear()
  vi.clearAllMocks()
})

const globalPrompts = Array.from({ length: 7 }, (_, index) => ({
  id: `prompt-${index + 1}`,
  label: `Prompt ${index + 1}`,
  prompt: index === 6 ? 'Translate this content into French.' : `Instruction ${index + 1}`,
  enabled: true
}))

function promptSettings(prompts = globalPrompts) {
  return { ai: { public: { globalPrompts: prompts } } }
}

describe('AiChatDrawer prompt selection', () => {
  it('shows the searchable empty-state browser with a blank Ask anything input', async () => {
    const wrapper = createWrapper({ settings: promptSettings() })
    const store = useAiGenerationStore()
    store.sessionConfig = {
      title: 'AI - Description',
      defaultPrompt: 'Write the field description.',
      outputType: 'html',
      mode: 'field',
      requestParams: {}
    }
    await wrapper.vm.$nextTick()

    expect(store.conversation.userInput).toBe('')
    expect(wrapper.find('.ai-chat-prompt-browser').exists()).toBe(true)
    expect(wrapper.find('.ai-chat-prompt-greeting').text()).toBe('How can I help?')
    expect(wrapper.find('.ai-chat-conversation').classes()).toContain('ai-chat-conversation--prompt-browser')
    expect(wrapper.find('.ai-chat-prompt-results').classes()).toContain('ai-chat-prompt-results--fill')
    expect(wrapper.find('.ai-chat-prompt-selector').exists()).toBe(false)
    expect(wrapper.find('.ai-chat-input textarea').attributes('placeholder')).toBe('Ask anything')
    expect(wrapper.find('.ai-chat-input__prompt-toggle').exists()).toBe(false)
    expect(wrapper.find('.ai-chat-prompt-browser').element.children[1].classList).toContain('ai-chat-prompt-search')
  })

  it('shows global prompts when assisting selected text', async () => {
    const wrapper = createWrapper({ settings: promptSettings() })
    const store = useAiGenerationStore()
    store.sessionConfig = {
      title: 'AI - Description',
      selectedText: 'text to improve',
      outputType: 'html',
      mode: 'selection',
      requestParams: {}
    }
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.ai-chat-prompt-browser').exists()).toBe(true)
    expect(wrapper.find('.ai-chat-prompt-results').exists()).toBe(true)
    expect(wrapper.vm.promptOptions.map(({ id }) => id)).toEqual(globalPrompts.map(({ id }) => id))
    expect(wrapper.vm.promptSections[0].options).toHaveLength(5)
    expect(wrapper.vm.promptSections.some(({ id }) => id === 'default')).toBe(false)
    expect(wrapper.find('.ai-chat-input textarea').attributes('placeholder')).toBe('Ask the AI to rewrite the selection...')
  })

  it('keeps global prompts browsable after a selected-text discussion starts', async () => {
    const wrapper = createWrapper({ settings: promptSettings() })
    const store = useAiGenerationStore()
    store.sessionConfig = {
      title: 'AI - Description',
      selectedText: 'text to improve',
      outputType: 'html',
      mode: 'selection',
      requestParams: {}
    }
    store.conversation.messages.push({ role: 'user', content: 'Make this clearer' })
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.ai-chat-prompt-browser').exists()).toBe(false)
    expect(wrapper.find('.ai-chat-prompt-selector').exists()).toBe(true)
  })

  it('pins the field default, ranks five globals, and leaves remaining prompts browsable', () => {
    const wrapper = createWrapper({ settings: promptSettings() })
    const store = useAiGenerationStore()
    store.sessionConfig = { title: 'AI', defaultPrompt: 'Field instruction', mode: 'field', requestParams: {} }
    wrapper.vm.promptUsage = { 'prompt-7': 4, 'prompt-6': 2 }

    expect(wrapper.vm.promptSections[0].options.map(({ id }) => id)).toEqual(['__default__'])
    expect(wrapper.vm.promptSections[1].options.map(({ id }) => id)).toEqual([
      'prompt-7', 'prompt-6', 'prompt-1', 'prompt-2', 'prompt-3'
    ])
    expect(wrapper.vm.promptSections[2].options.map(({ id }) => id)).toEqual(['prompt-4', 'prompt-5'])
    expect(wrapper.vm.promptSections[1]).toMatchObject({ label: 'Recent', icon: 'history' })
    expect(wrapper.vm.promptSections[2]).toMatchObject({ label: 'All prompts', icon: 'format_list_bulleted' })
  })

  it('searches prompt labels without matching instruction text', () => {
    const wrapper = createWrapper({ settings: promptSettings() })
    const store = useAiGenerationStore()
    store.sessionConfig = { title: 'AI', defaultPrompt: 'Field instruction', mode: 'field', requestParams: {} }

    wrapper.vm.promptSearch = 'prompt 2'
    expect(wrapper.vm.promptSections[0].options.map(({ id }) => id)).toEqual(['prompt-2'])

    wrapper.vm.promptSearch = 'field default'
    expect(wrapper.vm.promptSections).toEqual([])

    wrapper.vm.promptSearch = 'into french'
    expect(wrapper.vm.promptSections).toEqual([])

    wrapper.vm.promptSearch = 'does not exist'
    expect(wrapper.vm.promptSections).toEqual([])
  })

  it('fills but does not send the selected prompt', () => {
    const wrapper = createWrapper({ settings: promptSettings() })
    const store = useAiGenerationStore()
    store.sessionConfig = { title: 'AI', defaultPrompt: 'Field instruction', mode: 'field', requestParams: {} }

    wrapper.vm.selectPrompt('prompt-2')

    expect(store.conversation.userInput).toBe('Instruction 2')
    expect(store.conversation.messages).toEqual([])
    expect(wrapper.vm.selectedPromptId).toBe('prompt-2')
  })

  it('replaces the empty-state browser with the below-input selector after discussion starts', async () => {
    const wrapper = createWrapper({ settings: promptSettings() })
    const store = useAiGenerationStore()
    store.sessionConfig = { title: 'AI', defaultPrompt: 'Field instruction', mode: 'field', requestParams: {} }
    store.conversation.messages.push({ role: 'user', content: 'Question' })
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.ai-chat-prompt-browser').exists()).toBe(false)
    expect(wrapper.find('.ai-chat-prompt-selector').exists()).toBe(true)
    expect(wrapper.find('.ai-chat-prompt-menu').element.firstElementChild.classList).toContain('ai-chat-prompt-results')
    expect(wrapper.find('.ai-chat-prompt-menu').element.lastElementChild.querySelector('.ai-chat-prompt-search')).not.toBeNull()

    wrapper.find('.ai-chat-prompt-selector').element.getBoundingClientRect = () => ({ width: 288 })
    wrapper.vm.preparePromptMenu()
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.ai-chat-prompt-menu').attributes('style')).toContain('width: 288px')
    expect(wrapper.find('.ai-chat-prompt-menu').attributes('style')).toContain('max-width: 288px')

    const updatePosition = vi.spyOn(wrapper.vm.$refs.promptMenu, 'updatePosition')
    wrapper.vm.promptSearch = 'prompt 2'
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()

    expect(updatePosition).toHaveBeenCalled()
  })

  it('ignores malformed usage history', () => {
    localStorage.setItem('ai_prompt_usage', '{broken')
    const wrapper = createWrapper({ settings: promptSettings() })

    wrapper.vm.loadPromptUsage()

    expect(wrapper.vm.promptUsage).toEqual({})
  })
})

describe('AiChatDrawer formatDraftPreview', () => {
  it('uses the shared gradient treatment for assisted-writing chrome and primary actions', async () => {
    const wrapper = createWrapper()
    const store = useAiGenerationStore()
    store.sessionConfig = { title: 'AI', outputType: 'text', requestParams: {} }
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.ai-chat-toolbar').exists()).toBe(true)
    expect(wrapper.find('.ai-primary-btn').exists()).toBe(true)
  })

  it('renders an HTML draft as formatted HTML, not escaped source', () => {
    const wrapper = createWrapper()
    const store = useAiGenerationStore()
    store.sessionConfig = { title: 'AI', outputType: 'html', requestParams: {} }

    const preview = wrapper.vm.formatDraftPreview('<p>Hello <b>world</b></p>')

    expect(preview).toBe('<p>Hello <b>world</b></p>')
    expect(preview).not.toContain('&lt;')
  })

  it('normalizes editor image ids to downloadable image URLs with captions', () => {
    const wrapper = createWrapper()
    const store = useAiGenerationStore()
    const imageId = '0123456789abcdef01234567'
    store.sessionConfig = { title: 'AI', outputType: 'html', requestParams: {} }

    const preview = wrapper.vm.formatDraftPreview(`<p>Before</p><img src="${imageId}" alt="Figure caption"><p>After</p>`)

    expect(preview).toContain(`src="/api/images/download/${imageId}"`)
    expect(preview).toContain('<figure class="draft-image">')
    expect(preview).toContain('<figcaption>Figure caption</figcaption>')
    expect(preview).toContain('<p>After</p>')
  })

  it('renders editor HTML previews with the editor-style wrapper classes', async () => {
    const wrapper = createWrapper()
    const store = useAiGenerationStore()
    store.sessionConfig = { title: 'AI', outputType: 'html', requestParams: {} }
    store.conversation.messages.push({
      role: 'assistant',
      content: 'Updated',
      draft: '<pre><code class="language-js">const value = 1</code></pre>',
      draftPreview: '<pre><code class="language-js">const value = 1</code></pre>'
    })
    await wrapper.vm.$nextTick()

    const preview = wrapper.find('.ai-chat-draft-preview')
    expect(preview.classes()).toEqual(expect.arrayContaining(['ProseMirror', 'draft-rendered-diff']))
    expect(preview.find('pre code.language-js').exists()).toBe(true)
    const response = wrapper.find('.ai-chat-assistant-response')
    const actions = wrapper.find('.ai-chat-response-actions')
    expect(response.find('.ai-chat-response-actions').exists()).toBe(false)
    expect(response.element.nextElementSibling).toBe(actions.element)
  })

  it('strips disallowed tags from an HTML draft (no script injection)', () => {
    const wrapper = createWrapper()
    const store = useAiGenerationStore()
    store.sessionConfig = { title: 'AI', outputType: 'html', requestParams: {} }

    const preview = wrapper.vm.formatDraftPreview('<script>alert(1)</script><p>safe</p>')

    expect(preview).not.toContain('<script>')
    expect(preview).toContain('<p>safe</p>')
  })

  it('HTML-escapes each line for array output', () => {
    const wrapper = createWrapper()
    const store = useAiGenerationStore()
    store.sessionConfig = { title: 'AI', outputType: 'array', requestParams: {} }

    const preview = wrapper.vm.formatDraftPreview(['<b>one</b>', 'two'])

    expect(preview).toBe('&lt;b&gt;one&lt;/b&gt;<br/>two')
  })

  it('HTML-escapes plain text output', () => {
    const wrapper = createWrapper()
    const store = useAiGenerationStore()
    store.sessionConfig = { title: 'AI', outputType: 'text', requestParams: {} }

    const preview = wrapper.vm.formatDraftPreview('<b>bold</b>')

    expect(preview).toBe('&lt;b&gt;bold&lt;/b&gt;')
  })

  it('renders the sanitized HTML preview via v-html in the conversation', async () => {
    const wrapper = createWrapper()
    const store = useAiGenerationStore()
    store.sessionConfig = { title: 'AI', outputType: 'html', requestParams: {} }
    store.conversation.messages.push({
      role: 'assistant',
      content: 'Updated',
      draft: '<p>Formatted content</p>',
      draftPreview: '<p>Formatted content</p>'
    })
    await wrapper.vm.$nextTick()

    const preview = wrapper.find('.ai-chat-draft-preview')
    expect(preview.html()).toContain('<p>Formatted content</p>')
  })
})

describe('AiChatDrawer preview changes toggle', () => {
  function addAssistantMessage(store, draft = '<p>New description</p>') {
    store.conversation.messages.push({
      role: 'assistant',
      content: 'Updated',
      draft,
      draftPreview: draft,
      previewDiffOpen: false,
      previewDiffDraft: null
    })
  }

  it('toggles an assistant response between rendered draft and inline diff', async () => {
    const wrapper = createWrapper()
    const store = useAiGenerationStore()
    const entity = { description: '<p>Old description</p>' }
    store.sessionConfig = {
      title: 'AI - Description',
      outputType: 'html',
      mode: 'field',
      requestParams: {},
      diffContext: {
        getDiffEntity: () => entity,
        entityShape: 'finding',
        fieldKey: 'description',
        locale: 'en',
        outputType: 'html',
        mode: 'field',
        selection: null,
        getSelectionPreviewValue: null,
        languages: []
      }
    }
    addAssistantMessage(store)
    const message = store.conversation.messages[0]
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.ai-chat-draft-preview').exists()).toBe(true)

    wrapper.vm.togglePreviewDiff(message)
    await wrapper.vm.$nextTick()

    expect(message.previewDiffOpen).toBe(true)
    expect(message.previewDiffCurrent.description).toBe('<p>Old description</p>')
    expect(message.previewDiffDraft.description).toBe('<p>New description</p>')
    expect(wrapper.find('.draft-diff').exists()).toBe(true)
    expect(wrapper.find('.draft-diff--chat-preview').exists()).toBe(true)
    expect(wrapper.find('.diff-block__header').exists()).toBe(false)
    expect(wrapper.find('.ai-chat-draft-preview').exists()).toBe(false)
    expect(wrapper.text()).toContain('Original response')

    wrapper.vm.togglePreviewDiff(message)
    await wrapper.vm.$nextTick()

    expect(message.previewDiffOpen).toBe(false)
    expect(wrapper.find('.ai-chat-draft-preview').exists()).toBe(true)
    expect(wrapper.text()).toContain('Preview changes')
  })

  it('recomputes the diff from the live entity every time it is reopened', async () => {
    const wrapper = createWrapper()
    const store = useAiGenerationStore()
    const entity = { description: '<p>Old description</p>' }
    store.sessionConfig = {
      title: 'AI - Description',
      outputType: 'html',
      mode: 'field',
      requestParams: {},
      diffContext: {
        getDiffEntity: () => entity,
        entityShape: 'finding',
        fieldKey: 'description',
        locale: 'en',
        outputType: 'html',
        mode: 'field',
        selection: null,
        getSelectionPreviewValue: null,
        languages: []
      }
    }
    addAssistantMessage(store)
    const message = store.conversation.messages[0]

    wrapper.vm.togglePreviewDiff(message)
    expect(message.previewDiffCurrent.description).toBe('<p>Old description</p>')
    wrapper.vm.togglePreviewDiff(message) // close

    entity.description = '<p>Edited while the AI drawer was open</p>'
    wrapper.vm.togglePreviewDiff(message) // reopen - should reflect the edit
    expect(message.previewDiffCurrent.description).toBe('<p>Edited while the AI drawer was open</p>')
  })

  it('builds selected-text preview diff from the selected replacement using start/end offsets', () => {
    const wrapper = createWrapper()
    const store = useAiGenerationStore()
    const entity = { description: 'alpha wrong omega' }
    store.sessionConfig = {
      title: 'AI - Description',
      selectedText: 'wrong',
      outputType: 'text',
      mode: 'selection',
      requestParams: {},
      diffContext: {
        getDiffEntity: () => entity,
        entityShape: 'finding',
        fieldKey: 'description',
        locale: 'en',
        outputType: 'text',
        mode: 'selection',
        selection: { start: 6, end: 11, text: 'wrong' },
        getSelectionPreviewValue: null,
        languages: []
      }
    }
    addAssistantMessage(store, 'right')
    const message = store.conversation.messages[0]

    wrapper.vm.togglePreviewDiff(message)

    expect(message.previewDiffDraft.description).toBe('alpha right omega')
  })
})

describe('AiChatDrawer partial apply from a preview selection', () => {
  function addAssistantMessage(store, draft = '<p>Paragraph one</p><p>Paragraph two</p>') {
    store.conversation.messages.push({
      role: 'assistant',
      content: 'Updated',
      draft,
      draftPreview: draft,
      previewDiffOpen: false,
      previewDiffDraft: null,
      previewDiffCurrent: null
    })
  }

  it('selection mode: applies only the selected fragment to the anchored range and keeps the session open', () => {
    const wrapper = createWrapper()
    const store = useAiGenerationStore()
    const onPartialApply = vi.fn()
    store.sessionConfig = {
      title: 'AI - Description',
      selectedText: 'wrong',
      outputType: 'html',
      mode: 'selection',
      requestParams: {},
      onPartialApply
    }
    addAssistantMessage(store)

    wrapper.vm.previewSelection = { messageIndex: 0, html: '<p>Paragraph one</p>', text: 'Paragraph one' }
    expect(wrapper.vm.applyLabel(0)).toBe('Apply selection')

    wrapper.vm.applyDraft(store.conversation.messages[0], 0)

    expect(onPartialApply).toHaveBeenCalledWith('<p>Paragraph one</p>')
    expect(store.isActive).toBe(true)
    expect(wrapper.vm.previewSelection).toBeNull()
  })

  it('field mode: applies the selected fragment as the whole field value without ending the session', () => {
    // Field mode has no original range to preserve - "Apply" with a fragment
    // selected writes it as the whole field (via onApply), same mechanism as
    // the no-selection case, but never ends the session.
    const wrapper = createWrapper()
    const store = useAiGenerationStore()
    const onApply = vi.fn()
    store.sessionConfig = { title: 'AI - Description', outputType: 'html', mode: 'field', requestParams: {}, onApply }
    addAssistantMessage(store)

    wrapper.vm.previewSelection = { messageIndex: 0, html: '<p>Paragraph one</p>', text: 'Paragraph one' }
    expect(wrapper.vm.applyLabel(0)).toBe('Apply selection')

    wrapper.vm.applyDraft(store.conversation.messages[0], 0)

    expect(onApply).toHaveBeenCalledWith('<p>Paragraph one</p>')
    expect(store.isActive).toBe(true)
    expect(wrapper.vm.previewSelection).toBeNull()
  })

  it('field mode: applies the whole draft when nothing is selected, without ending the session', () => {
    const wrapper = createWrapper()
    const store = useAiGenerationStore()
    const onApply = vi.fn()
    store.sessionConfig = { title: 'AI', outputType: 'html', mode: 'field', requestParams: {}, onApply }
    addAssistantMessage(store, '<p>Whole draft</p>')

    wrapper.vm.applyDraft(store.conversation.messages[0], 0)

    expect(onApply).toHaveBeenCalledWith('<p>Whole draft</p>')
    expect(store.isActive).toBe(true)
  })

  it('field mode: applying again after already applying still works (repeatable, not a one-shot)', () => {
    const wrapper = createWrapper()
    const store = useAiGenerationStore()
    const onApply = vi.fn()
    store.sessionConfig = { title: 'AI', outputType: 'html', mode: 'field', requestParams: {}, onApply }
    addAssistantMessage(store, '<p>First draft</p>')

    wrapper.vm.applyDraft(store.conversation.messages[0], 0)
    wrapper.vm.applyDraft(store.conversation.messages[0], 0)

    expect(onApply).toHaveBeenCalledTimes(2)
    expect(wrapper.vm.applyDisabled).toBe(false)
  })

  it('inserts the selected fragment at cursor without ending the session', () => {
    const wrapper = createWrapper()
    const store = useAiGenerationStore()
    const onInsertAtCursor = vi.fn()
    store.sessionConfig = {
      title: 'AI',
      outputType: 'html',
      mode: 'field',
      requestParams: {},
      onInsertAtCursor
    }
    addAssistantMessage(store)

    wrapper.vm.previewSelection = { messageIndex: 0, html: '<p>Paragraph two</p>', text: 'Paragraph two' }
    wrapper.vm.insertAtCursor(store.conversation.messages[0], 0)

    expect(onInsertAtCursor).toHaveBeenCalledWith('<p>Paragraph two</p>')
    expect(store.isActive).toBe(true)
  })
})

describe('AiChatDrawer send/stop generation', () => {
  it('records a selected global prompt only after a successful response and resets the selection', async () => {
    const wrapper = createWrapper({ settings: promptSettings() })
    const store = useAiGenerationStore()
    store.sessionConfig = {
      title: 'AI',
      defaultPrompt: 'Field instruction',
      outputType: 'html',
      mode: 'field',
      requestParams: {}
    }
    wrapper.vm.selectPrompt('prompt-3')
    AiService.streamGenerateFieldDraft.mockImplementation(async (payload, { onEvent }) => {
      onEvent({ event: 'done', data: { draft: '<p>ok</p>', reply: '' } })
    })

    await wrapper.vm.sendMessage()

    expect(JSON.parse(localStorage.getItem('ai_prompt_usage'))).toEqual({ 'prompt-3': 1 })
    expect(wrapper.vm.promptUsage).toEqual({ 'prompt-3': 1 })
    expect(wrapper.vm.selectedPromptId).toBeNull()
  })

  it('does not record prompt usage when generation fails and preserves the selection for retry', async () => {
    const notify = vi.fn()
    const wrapper = createWrapper({ notify, settings: promptSettings() })
    const store = useAiGenerationStore()
    store.sessionConfig = {
      title: 'AI',
      defaultPrompt: 'Field instruction',
      outputType: 'html',
      mode: 'field',
      requestParams: {}
    }
    wrapper.vm.selectPrompt('prompt-4')
    AiService.streamGenerateFieldDraft.mockRejectedValue(new Error('boom'))

    await wrapper.vm.sendMessage()

    expect(localStorage.getItem('ai_prompt_usage')).toBeNull()
    expect(wrapper.vm.selectedPromptId).toBe('prompt-4')
    expect(store.conversation.userInput).toBe('Instruction 4')
  })

  it('keeps the stop button interactive while making the prompt read-only', async () => {
    const wrapper = createWrapper()
    const store = useAiGenerationStore()
    store.sessionConfig = { title: 'AI', outputType: 'html', mode: 'field', requestParams: {} }
    store.loading = true
    await wrapper.vm.$nextTick()

    const input = wrapper.find('.ai-chat-input textarea')
    const stopButton = wrapper.find('button[aria-label="Stop generating"]')
    const abort = vi.fn()
    wrapper.vm.abortController = { abort }

    expect(input.attributes('readonly')).toBeDefined()
    expect(input.attributes('disabled')).toBeUndefined()
    expect(stopButton.exists()).toBe(true)

    await stopButton.trigger('click')

    expect(abort).toHaveBeenCalled()
  })

  it('passes an abort signal to AiService.streamGenerateFieldDraft while a request is in flight', async () => {
    const wrapper = createWrapper()
    const store = useAiGenerationStore()
    store.sessionConfig = { title: 'AI', outputType: 'html', mode: 'field', requestParams: {} }
    store.conversation.userInput = 'do it'

    let resolveStream
    AiService.streamGenerateFieldDraft.mockReturnValue(new Promise((resolve) => { resolveStream = resolve }))

    const sendPromise = wrapper.vm.sendMessage()
    await wrapper.vm.$nextTick()

    expect(store.loading).toBe(true)
    const [, options] = AiService.streamGenerateFieldDraft.mock.calls[0]
    expect(options.signal).toBeInstanceOf(AbortSignal)

    options.onEvent({ event: 'done', data: { draft: '<p>ok</p>', reply: '' } })
    resolveStream()
    await sendPromise
  })

  it('includes the selected provider in the generate payload', async () => {
    const wrapper = createWrapper()
    const store = useAiGenerationStore()
    store.sessionConfig = { title: 'AI', outputType: 'html', mode: 'field', requestParams: {} }
    store.conversation.userInput = 'do it'
    store.selectedProvider = 'anthropic'

    AiService.streamGenerateFieldDraft.mockImplementation(async (payload, { onEvent }) => {
      onEvent({ event: 'done', data: { draft: '<p>ok</p>', reply: '' } })
    })

    await wrapper.vm.sendMessage()

    const [payload] = AiService.streamGenerateFieldDraft.mock.calls[0]
    expect(payload.provider).toBe('anthropic')
  })

  it('omits provider from the payload when none is selected (backend uses the org default)', async () => {
    const wrapper = createWrapper()
    const store = useAiGenerationStore()
    store.sessionConfig = { title: 'AI', outputType: 'html', mode: 'field', requestParams: {} }
    store.conversation.userInput = 'do it'
    store.selectedProvider = ''

    AiService.streamGenerateFieldDraft.mockImplementation(async (payload, { onEvent }) => {
      onEvent({ event: 'done', data: { draft: '<p>ok</p>', reply: '' } })
    })

    await wrapper.vm.sendMessage()

    const [payload] = AiService.streamGenerateFieldDraft.mock.calls[0]
    expect(payload.provider).toBeUndefined()
  })

  it('stopGeneration cancels the in-flight request, restores the input, and shows no error notify', async () => {
    const notify = vi.fn()
    const wrapper = createWrapper({ notify, settings: promptSettings() })
    const store = useAiGenerationStore()
    store.sessionConfig = { title: 'AI', defaultPrompt: 'Field instruction', outputType: 'html', mode: 'field', requestParams: {} }
    wrapper.vm.selectPrompt('prompt-5')

    AiService.streamGenerateFieldDraft.mockImplementation((payload, { signal }) => {
      return new Promise((_resolve, reject) => {
        signal.addEventListener('abort', () => {
          const err = new Error('aborted')
          err.name = 'AbortError'
          reject(err)
        })
      })
    })

    const sendPromise = wrapper.vm.sendMessage()
    await wrapper.vm.$nextTick()

    expect(store.conversation.messages).toHaveLength(1)

    wrapper.vm.stopGeneration()
    await sendPromise

    expect(store.loading).toBe(false)
    expect(store.conversation.messages).toHaveLength(0)
    expect(store.conversation.userInput).toBe('Instruction 5')
    expect(wrapper.vm.selectedPromptId).toBe('prompt-5')
    expect(localStorage.getItem('ai_prompt_usage')).toBeNull()
    expect(notify).not.toHaveBeenCalled()
  })

  it('shows an error notify and restores the input for a real request failure (not a cancel)', async () => {
    const notify = vi.fn()
    const wrapper = createWrapper({ notify })
    const store = useAiGenerationStore()
    store.sessionConfig = { title: 'AI', outputType: 'html', mode: 'field', requestParams: {} }
    store.conversation.userInput = 'do it'

    AiService.streamGenerateFieldDraft.mockRejectedValue(new Error('boom'))

    await wrapper.vm.sendMessage()

    expect(store.conversation.messages).toHaveLength(0)
    expect(store.conversation.userInput).toBe('do it')
    expect(notify).toHaveBeenCalledWith(expect.objectContaining({ color: 'negative' }))
  })

  it('shows the friendly timed-out message instead of a raw network error', async () => {
    const notify = vi.fn()
    const wrapper = createWrapper({ notify })
    const store = useAiGenerationStore()
    store.sessionConfig = { title: 'AI', outputType: 'html', mode: 'field', requestParams: {} }
    store.conversation.userInput = 'do it'

    AiService.streamGenerateFieldDraft.mockRejectedValue(new TypeError('Failed to fetch'))

    await wrapper.vm.sendMessage()

    expect(notify).toHaveBeenCalledWith(expect.objectContaining({
      message: 'aiChat.timedOut',
      color: 'negative'
    }))
  })
})

describe('AiChatDrawer selection anchor status', () => {
  it('exposes the collapsed anchor status for the caption', () => {
    const wrapper = createWrapper()
    const store = useAiGenerationStore()
    store.sessionConfig = { title: 'AI', selectedText: 'wrong', outputType: 'text', mode: 'selection', requestParams: {} }
    store.selectionAnchor = { from: 4, to: 4, status: 'collapsed' }

    expect(wrapper.vm.anchorStatus).toBe('collapsed')
  })

  it('disables Apply when the tracked selection was lost', () => {
    const wrapper = createWrapper()
    const store = useAiGenerationStore()
    store.sessionConfig = { title: 'AI', selectedText: 'wrong', outputType: 'text', mode: 'selection', requestParams: {} }
    store.selectionAnchor = { from: 0, to: 0, status: 'invalid' }

    expect(wrapper.vm.applyDisabled).toBe(true)
  })
})
