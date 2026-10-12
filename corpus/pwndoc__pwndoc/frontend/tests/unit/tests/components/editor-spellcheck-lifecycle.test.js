import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { Editor } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'

vi.mock('@/services/spellcheck', () => ({
  default: { addWord: vi.fn() }
}))

import { LanguageTool } from '@/components/editor/editor-spellcheck'

describe('LanguageTool editor lifecycle', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('aborts pending checks and releases editor state when destroyed', async () => {
    const fetchMock = vi.fn((_url, { signal }) => new Promise((_resolve, reject) => {
      signal.addEventListener('abort', () => {
        reject(Object.assign(new Error('aborted'), { name: 'AbortError' }))
      }, { once: true })
    }))
    vi.stubGlobal('fetch', fetchMock)

    const editor = new Editor({
      content: '<p>Content that starts an automatic spellcheck request.</p>',
      extensions: [
        StarterKit,
        LanguageTool.configure({
          apiUrl: '/api/spellcheck',
          automaticMode: true,
          active: true
        })
      ]
    })

    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledOnce())
    const storage = editor.storage.languagetool
    const signal = fetchMock.mock.calls[0][1].signal

    expect(signal.aborted).toBe(false)
    expect(storage.editorView).not.toBeNull()

    editor.destroy()

    expect(signal.aborted).toBe(true)
    expect(storage.destroyed).toBe(true)
    expect(storage.editorView).toBeNull()
    expect(storage.abortControllers.size).toBe(0)
    expect(storage.pendingTimeouts.size).toBe(0)
    expect(storage.decorationSet).not.toBeNull()
    expect(() => storage.decorationSet.map({ maps: [] }, editor.state.doc)).not.toThrow()
  })

  it('supports another editor transaction after an editor is replaced', () => {
    vi.stubGlobal('fetch', vi.fn())
    const languageTool = LanguageTool.configure({
      apiUrl: '/api/spellcheck',
      automaticMode: false,
      active: true
    })
    const firstEditor = new Editor({
      content: '<p>First vulnerability</p>',
      extensions: [StarterKit, languageTool]
    })

    firstEditor.destroy()

    const secondEditor = new Editor({
      content: '<p>Second vulnerability</p>',
      extensions: [StarterKit, languageTool]
    })

    expect(() => {
      secondEditor.commands.focus()
      secondEditor.commands.setContent('<p>Updated vulnerability</p>')
    }).not.toThrow()

    secondEditor.destroy()
  })
})
