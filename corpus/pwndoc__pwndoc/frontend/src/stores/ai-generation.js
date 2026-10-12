import { defineStore } from 'pinia'
import { useAuditQaStore } from '@/stores/audit-qa'

const emptyConversation = () => ({
  messages: [],
  userInput: '',
  confirmedPromptInstruction: ''
})

export const useAiGenerationStore = defineStore('aiGeneration', {
  state: () => ({
    drawerOpen: false,
    loading: false,
    lockKey: null,
    // Provider chosen in the drawer's selector. Remembered across sessions (not persisted
    // server-side); empty means "use the org default provider".
    selectedProvider: '',
    sessionConfig: null,
    sessionId: 0,
    conversation: emptyConversation(),
    selectionAnchor: null,
    _reject: null
  }),

  getters: {
    isActive(state) {
      return Boolean(state.sessionConfig)
    },

    isGenerating(state) {
      return state.loading
    },

    isFieldGenerating(state) {
      return (lockKey) => {
        if (!lockKey || !state.sessionConfig)
          return false
        return state.loading && state.lockKey === lockKey
      }
    },

    // Whether a session is active for this field. Used only to disable the sparkle
    // button for that field - fields stay editable while a session is active.
    isFieldSessionActive(state) {
      return (lockKey) => {
        if (!lockKey || !state.sessionConfig || !state.drawerOpen)
          return false
        return state.lockKey === lockKey
      }
    },

    // Selection-mode sessions on targets without position mapping (plain DOM
    // char-offset inputs) must stay readonly for the duration of the session,
    // since their stored offsets can't be remapped like ProseMirror positions.
    isFieldSelectionLocked(state) {
      return (lockKey) => {
        return this.isFieldSessionActive(lockKey) && state.sessionConfig.mode === 'selection'
      }
    }
  },

  actions: {
    clearConversation() {
      this.conversation = emptyConversation()
    },

    closeDrawer() {
      if (this.loading) {
        this.drawerOpen = false
        return
      }

      if (!this.sessionConfig) {
        this.drawerOpen = false
        return
      }

      if (this._reject)
        this._reject(new Error('cancelled'))
      this.endSession()
    },

    openSession(config = {}) {
      const lockKey = config.lockKey || null

      if (this.sessionConfig) {
        if (this._reject)
          this._reject(new Error('cancelled'))
        this._reject = null
      }

      // The returned promise only ever rejects (when the drawer closes) -
      // applying content happens via the onApply/onPartialApply/onInsertAtCursor
      // callbacks below, repeatably, without ever resolving this promise.
      return new Promise((_resolve, reject) => {
        this._reject = reject
        this.lockKey = lockKey
        this.sessionConfig = {
          title: config.title,
          selectedText: config.selectedText || '',
          defaultPrompt: config.defaultPrompt || '',
          outputType: config.outputType || 'html',
          requestParams: config.requestParams || {},
          diffContext: config.diffContext || null,
          mode: config.mode || (String(config.selectedText || '').trim() ? 'selection' : 'field'),
          // All three apply the current draft/fragment directly and can be
          // called as many times as the user likes - "Apply" never ends the
          // session on its own, only closing the drawer does.
          onApply: typeof config.onApply === 'function' ? config.onApply : null,
          onPartialApply: typeof config.onPartialApply === 'function' ? config.onPartialApply : null,
          onInsertAtCursor: typeof config.onInsertAtCursor === 'function' ? config.onInsertAtCursor : null
        }
        this.loading = false
        this.selectionAnchor = null
        this.clearConversation()

        this.sessionId += 1
        useAuditQaStore().close()
        this.drawerOpen = true
      })
    },

    setLoading(loading) {
      this.loading = Boolean(loading)
    },

    setSelectedProvider(provider) {
      this.selectedProvider = provider || ''
    },

    setSelectionAnchor(anchor) {
      this.selectionAnchor = anchor
    },

    // Field-mode whole-field replace. Repeatable - each click writes the
    // current draft/fragment straight to the field without ending the session.
    applyFieldValue(content) {
      if (this.sessionConfig?.onApply)
        this.sessionConfig.onApply(content)
    },

    // Selection-mode anchored-range replace (whole draft or just a fragment).
    // Also repeatable, and re-anchors over what was just written so the next
    // apply targets the latest content rather than the original selection.
    applyPartialDraft(content) {
      if (this.sessionConfig?.onPartialApply)
        this.sessionConfig.onPartialApply(content)
    },

    insertDraftAtCursor(content) {
      if (this.sessionConfig?.onInsertAtCursor)
        this.sessionConfig.onInsertAtCursor(content)
    },

    cancelSession({ force = false } = {}) {
      if (this.loading && !force)
        return false

      if (this._reject)
        this._reject(new Error('cancelled'))
      this.endSession()
      return true
    },

    endSession() {
      this.drawerOpen = false
      this.loading = false
      this.lockKey = null
      this.sessionConfig = null
      this.selectionAnchor = null
      this.clearConversation()
      this._reject = null
    }
  }
})
