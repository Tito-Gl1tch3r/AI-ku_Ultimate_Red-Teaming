import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import AiFieldHelper from '@/services/ai-field-helper'
import { useAiGenerationStore } from '@/stores/ai-generation'

vi.mock('@/stores/audit-qa', () => ({
  useAuditQaStore: () => ({
    close: vi.fn()
  })
}))

beforeEach(() => {
  setActivePinia(createPinia())
})

describe('AiFieldHelper.buildAiDiffDraft', () => {
  it('replaces a finding field in field mode', () => {
    const entity = {
      title: 'Finding title',
      description: 'Old description'
    }
    const diffContext = {
      getDiffEntity: () => entity,
      entityShape: 'finding',
      fieldKey: 'description',
      locale: 'en',
      outputType: 'text',
      mode: 'field',
      selection: null,
      getSelectionPreviewValue: null,
      languages: []
    }

    const draftData = AiFieldHelper.buildAiDiffDraft(diffContext, 'New description')
    expect(draftData.description).toBe('New description')
    expect(entity.description).toBe('Old description')
  })

  it('replaces a selection inside a vulnerability detail using start/end offsets', () => {
    const entity = {
      details: [{
        locale: 'en',
        description: 'alpha beta gamma'
      }]
    }
    const diffContext = {
      getDiffEntity: () => entity,
      entityShape: 'vulnerability',
      fieldKey: 'description',
      locale: 'en',
      outputType: 'text',
      mode: 'selection',
      selection: { start: 6, end: 10, text: 'beta' },
      getSelectionPreviewValue: null,
      languages: []
    }

    const draftData = AiFieldHelper.buildAiDiffDraft(diffContext, 'delta')
    expect(draftData.details[0].description).toBe('alpha delta gamma')
  })

  it('recomputes the entity at call time, reflecting edits made after the session started', () => {
    const entity = { description: 'Old description' }
    const diffContext = {
      getDiffEntity: () => entity,
      entityShape: 'finding',
      fieldKey: 'description',
      locale: 'en',
      outputType: 'text',
      mode: 'field',
      selection: null,
      getSelectionPreviewValue: null,
      languages: []
    }

    entity.description = 'Edited while the AI session was open'
    const draftData = AiFieldHelper.buildAiDiffDraft(diffContext, 'New description')
    expect(draftData.description).toBe('New description')
  })

  it('delegates rich-editor (ProseMirror) selections to getSelectionPreviewValue instead of splicing offsets', () => {
    const entity = { description: 'Old description' }
    const getSelectionPreviewValue = vi.fn(() => 'simulated replacement result')
    const diffContext = {
      getDiffEntity: () => entity,
      entityShape: 'finding',
      fieldKey: 'description',
      locale: 'en',
      outputType: 'html',
      mode: 'selection',
      selection: { from: 3, to: 8, text: 'lo de' },
      getSelectionPreviewValue,
      languages: []
    }

    const draftData = AiFieldHelper.buildAiDiffDraft(diffContext, '<p>new</p>')
    expect(getSelectionPreviewValue).toHaveBeenCalled()
    expect(draftData.description).toBe('simulated replacement result')
  })
})

describe('AiFieldHelper.runFieldAiChat', () => {
  it('scopes field-mode context to the active standard field value', async () => {
    const promise = AiFieldHelper.runFieldAiChat({
      title: 'AI - Description',
      defaultPrompt: 'Proofread the text.',
      outputType: 'html',
      fieldLabel: 'Description',
      requestParams: {
        entityType: 'finding',
        field: 'description',
        locale: 'en',
        outputType: 'html',
        context: {
          title: 'Finding title',
          description: '<p>Description only</p>',
          observation: '<p>Observation must stay out</p>'
        }
      }
    })

    const store = useAiGenerationStore()
    expect(store.sessionConfig.requestParams.context).toEqual(expect.objectContaining({
      currentFieldKey: 'description',
      currentFieldLabel: 'Description',
      currentFieldValue: '<p>Description only</p>'
    }))

    store.cancelSession({ force: true })
    await expect(promise).resolves.toBeNull()
  })

  it('scopes field-mode context to the active custom field value', async () => {
    const promise = AiFieldHelper.runFieldAiChat({
      title: 'AI - Custom',
      defaultPrompt: 'Proofread the text.',
      outputType: 'html',
      fieldLabel: 'Custom',
      requestParams: {
        entityType: 'finding',
        field: 'custom-field:abc123',
        locale: 'en',
        outputType: 'html',
        context: {
          customFieldLabel: 'Custom',
          customFieldValue: '<p>Custom field only</p>',
          description: '<p>Description must stay out</p>'
        }
      }
    })

    const store = useAiGenerationStore()
    expect(store.sessionConfig.requestParams.context).toEqual(expect.objectContaining({
      currentFieldKey: 'custom-field:abc123',
      currentFieldLabel: 'Custom',
      currentFieldValue: '<p>Custom field only</p>'
    }))

    store.cancelSession({ force: true })
    await expect(promise).resolves.toBeNull()
  })
})

describe('AiFieldHelper session mode and partial apply wiring', () => {
  it('opens a field-mode session and forwards onInsertAtCursor', async () => {
    const onInsertAtCursor = vi.fn()
    const promise = AiFieldHelper.runFieldAiChat({
      title: 'AI - Description',
      defaultPrompt: 'Proofread the text.',
      outputType: 'html',
      onInsertAtCursor,
      requestParams: {
        entityType: 'finding',
        field: 'description',
        locale: 'en',
        outputType: 'html',
        context: {}
      }
    })

    const store = useAiGenerationStore()
    expect(store.sessionConfig.mode).toBe('field')
    store.sessionConfig.onInsertAtCursor('<p>inserted</p>')
    expect(onInsertAtCursor).toHaveBeenCalledWith('<p>inserted</p>')

    store.cancelSession({ force: true })
    await expect(promise).resolves.toBeNull()
  })

  it('opens a selection-mode session and forwards onPartialApply without ending it', async () => {
    const onPartialApply = vi.fn()
    const promise = AiFieldHelper.runSelectionAiChat({
      title: 'AI - Description',
      selectedText: 'selected text',
      outputType: 'html',
      onPartialApply,
      selection: { from: 0, to: 5, text: 'selec' },
      requestParams: {
        entityType: 'finding',
        field: 'description',
        locale: 'en',
        outputType: 'html',
        context: {}
      }
    })

    const store = useAiGenerationStore()
    expect(store.sessionConfig.mode).toBe('selection')
    store.applyPartialDraft('<p>partial</p>')
    expect(onPartialApply).toHaveBeenCalledWith('<p>partial</p>')
    expect(store.isActive).toBe(true)

    store.cancelSession({ force: true })
    await expect(promise).resolves.toBeNull()
  })
})

describe('AiFieldHelper.applySelectionDraft', () => {
  it('passes reanchor through to the selection target', () => {
    const replaceTextSelection = vi.fn()
    AiFieldHelper.applySelectionDraft({
      selectionTarget: { replaceTextSelection },
      selection: { from: 0, to: 4 },
      draft: 'new text',
      outputType: 'text',
      reanchor: true
    })

    expect(replaceTextSelection).toHaveBeenCalledWith('new text', { from: 0, to: 4 }, { reanchor: true })
  })
})

describe('AiFieldHelper.applyInsertAtCursor', () => {
  it('sanitizes html output before inserting at the cursor', () => {
    const insertAtCursor = vi.fn()
    AiFieldHelper.applyInsertAtCursor({
      selectionTarget: { insertAtCursor },
      draft: '<script>alert(1)</script><p>safe</p>',
      outputType: 'html'
    })

    expect(insertAtCursor).toHaveBeenCalledWith('<p>safe</p>')
  })

  it('is a no-op when the target does not support cursor insertion', () => {
    expect(() => AiFieldHelper.applyInsertAtCursor({
      selectionTarget: {},
      draft: 'text',
      outputType: 'text'
    })).not.toThrow()
  })
})

describe('AiFieldHelper.runFieldSession', () => {
  it('field mode: writes the whole field via setValue when nothing is selected', async () => {
    const setValue = vi.fn()
    const selectionTarget = { getTextSelection: () => null }

    const promise = AiFieldHelper.runFieldSession({
      field: 'description',
      fieldKey: 'description',
      lockKey: 'finding:1:description',
      selectionTarget,
      entityShape: 'finding',
      requestEntityType: 'finding',
      locale: 'en',
      aiFieldPrompts: [],
      buildContext: () => ({}),
      getDiffEntity: () => ({ description: 'old' }),
      setValue
    })

    const store = useAiGenerationStore()
    store.applyFieldValue('<p>new</p>')
    store.cancelSession({ force: true })

    await promise

    expect(setValue).toHaveBeenCalledWith('<p>new</p>')
  })

  it('selection mode: anchors the selection, writes via replaceTextSelection, and clears the anchor once the session ends', async () => {
    const selection = { from: 2, to: 6, text: 'text', html: 'text' }
    const setAiSelectionAnchor = vi.fn()
    const clearAiSelectionAnchor = vi.fn()
    const replaceTextSelection = vi.fn()
    const selectionTarget = {
      getTextSelection: () => selection,
      setAiSelectionAnchor,
      clearAiSelectionAnchor,
      replaceTextSelection,
      buildAnchoredPreviewHtml: vi.fn()
    }

    const promise = AiFieldHelper.runFieldSession({
      field: 'description',
      fieldKey: 'description',
      lockKey: 'finding:1:description',
      selectionTarget,
      entityShape: 'finding',
      requestEntityType: 'finding',
      locale: 'en',
      aiFieldPrompts: [],
      buildContext: () => ({}),
      getDiffEntity: () => ({ description: 'alpha text omega' }),
      setValue: vi.fn()
    })

    expect(setAiSelectionAnchor).toHaveBeenCalledWith(selection)

    const store = useAiGenerationStore()
    store.applyPartialDraft('replacement')
    store.cancelSession({ force: true })

    await promise

    expect(replaceTextSelection).toHaveBeenCalledWith(expect.any(String), selection, { reanchor: true })
    expect(clearAiSelectionAnchor).toHaveBeenCalled()
  })

  it('releases the selection anchor even when the session is cancelled without applying anything', async () => {
    const selection = { from: 2, to: 6, text: 'text', html: 'text' }
    const clearAiSelectionAnchor = vi.fn()
    const selectionTarget = {
      getTextSelection: () => selection,
      setAiSelectionAnchor: vi.fn(),
      clearAiSelectionAnchor,
      buildAnchoredPreviewHtml: vi.fn()
    }

    const promise = AiFieldHelper.runFieldSession({
      field: 'description',
      fieldKey: 'description',
      lockKey: 'finding:1:description',
      selectionTarget,
      entityShape: 'finding',
      requestEntityType: 'finding',
      locale: 'en',
      aiFieldPrompts: [],
      buildContext: () => ({}),
      getDiffEntity: () => ({ description: 'alpha text omega' }),
      setValue: vi.fn()
    })

    useAiGenerationStore().cancelSession({ force: true })

    await promise

    expect(clearAiSelectionAnchor).toHaveBeenCalled()
  })
})

describe('AiFieldHelper.getOutputType', () => {
  // Pinned to the literal mapping, not just re-derived, so a drift from the backend's
  // independent copy in ai-prompts.js is caught here (see the comment on
  // CUSTOM_FIELD_OUTPUT_TYPES in ai-field-helper.js).
  it.each([
    ['text', 'html'],
    ['input', 'text'],
    ['date', 'text'],
    ['select', 'text'],
    ['radio', 'text'],
    ['select-multiple', 'array'],
    ['checkbox', 'array']
  ])('maps custom field type %s to output type %s', (fieldType, expected) => {
    expect(AiFieldHelper.getOutputType(null, { customField: { fieldType } })).toBe(expected)
  })

  it('falls back to text for an unknown custom field type', () => {
    expect(AiFieldHelper.getOutputType(null, { customField: { fieldType: 'unknown' } })).toBe('text')
  })
})

describe('AiFieldHelper value helpers', () => {
  it('resolves standard/custom labels and prompt context values', () => {
    expect(AiFieldHelper.getFieldLabel('poc', null, 'poc')).toBe('Proofs')
    expect(AiFieldHelper.getFieldLabel('unknown', null, 'fallback')).toBe('fallback')
    expect(AiFieldHelper.getFieldLabel(null, { customField: { label: 'Custom' } }, 'x')).toBe('Custom')
    expect(AiFieldHelper.getDefaultPrompt([
      { fieldKey: 'description', prompt: 'Use {title}: {refs}; {missing}; {meta}' }
    ], 'description', { title: 'A', refs: ['one', 'two'], missing: null, meta: { safe: true } }))
      .toBe('Use A: one, two; ; {"safe":true}')
    expect(AiFieldHelper.getDefaultPrompt(null, 'missing')).toBe('')
  })

  it('reads non-empty DOM input selections only', () => {
    expect(AiFieldHelper.getInputSelection(null)).toBeNull()
    const el = { selectionStart: 1, selectionEnd: 4, value: 'abcde' }
    expect(AiFieldHelper.getInputSelection({ $el: { querySelector: () => el } })).toEqual({
      start: 1, end: 4, text: 'bcd', html: 'bcd'
    })
    el.selectionEnd = 1
    expect(AiFieldHelper.getInputSelection({ $el: { querySelector: () => el } })).toBeNull()
  })

  it('normalizes array/html/text field applications', () => {
    const setValue = vi.fn()
    AiFieldHelper.applyFieldDraft({ draft: [' a ', '', 'b'], outputType: 'array', setValue })
    expect(setValue).toHaveBeenLastCalledWith(['a', 'b'])
    AiFieldHelper.applyFieldDraft({ draft: ' a\n\n b ', outputType: 'array', setValue })
    expect(setValue).toHaveBeenLastCalledWith(['a', 'b'])
    AiFieldHelper.applyFieldDraft({ draft: '<script>x</script><p>ok</p>', outputType: 'html', setValue })
    expect(setValue).toHaveBeenLastCalledWith('<p>ok</p>')
    AiFieldHelper.applyFieldDraft({ draft: ' text ', outputType: 'text', setValue })
    expect(setValue).toHaveBeenLastCalledWith('text')
  })

  it('builds isolated context objects for findings, sections and vulnerabilities', () => {
    expect(AiFieldHelper.buildFindingAiContext({
      title: 'Finding', references: ['r'], customFields: [
        { customField: { label: 'Named' }, text: 'value' }, { customField: {}, text: 'ignored' }
      ]
    }, { customField: { label: 'Named' }, text: 'value' })).toMatchObject({
      title: 'Finding', observation: '', references: ['r'], customFieldLabel: 'Named', customFields: { Named: 'value' }
    })
    expect(AiFieldHelper.buildSectionAiContext({ field: 'summary', customFields: [] })).toMatchObject({
      sectionField: 'summary', sectionName: '', customFields: {}
    })
    expect(AiFieldHelper.buildVulnerabilityAiContext({ category: 'Web' }, {
      title: 'Vulnerability', customFields: [{ customField: { label: 'CV' }, text: 'x' }]
    })).toMatchObject({ category: 'Web', title: 'Vulnerability', customFields: { CV: 'x' } })
  })

  it('supports custom fields, array selections and missing diff targets', () => {
    expect(AiFieldHelper.buildAiDiffDraft(null, 'draft')).toBeNull()
    const entity = { customFields: [{ customField: 'id', text: 'old' }], references: ['one', 'two'] }
    const custom = AiFieldHelper.buildAiDiffDraft({
      getDiffEntity: () => entity, entityShape: 'finding', fieldKey: 'custom-field:id', outputType: 'text', mode: 'field'
    }, 'new')
    expect(custom.customFields[0].text).toBe('new')
    const array = AiFieldHelper.buildAiDiffDraft({
      getDiffEntity: () => entity, entityShape: 'finding', fieldKey: 'references', outputType: 'array', mode: 'selection',
      selection: { start: 4, end: 7 }
    }, ['three'])
    expect(array.references).toEqual(['one', 'three'])
    expect(AiFieldHelper.buildAiDiffDraft({
      getDiffEntity: () => entity, entityShape: 'finding', fieldKey: 'references', outputType: 'array', mode: 'selection', selection: {}
    }, ['x'])).toBeNull()
  })

  it('uses editor fallback replacement and exposes session locks', async () => {
    const replaceTextSelection = vi.fn()
    AiFieldHelper.applySelectionDraft({
      selectionTarget: { editor: { replaceTextSelection } }, selection: { start: 0, end: 1 }, draft: 'x', outputType: 'text'
    })
    expect(replaceTextSelection).toHaveBeenCalled()
    expect(AiFieldHelper.isFieldSessionActive('field')).toBe(false)
    expect(AiFieldHelper.isFieldSelectionLocked('field')).toBe(false)
  })
})

describe('AiFieldHelper cancellation and error handling', () => {
  it('runs cancellation callbacks for field and selection sessions', async () => {
    const onCancel = vi.fn()
    const field = AiFieldHelper.runFieldAiChat({ title: 'AI', outputType: 'text', requestParams: { field: 'x', context: {} }, onCancel })
    useAiGenerationStore().cancelSession({ force: true })
    await expect(field).resolves.toBeNull()
    const selection = AiFieldHelper.runSelectionAiChat({
      title: 'AI', selectedText: 'x', outputType: 'text', requestParams: {}, onCancel
    })
    useAiGenerationStore().cancelSession({ force: true })
    await expect(selection).resolves.toBeNull()
    expect(onCancel).toHaveBeenCalledTimes(2)
  })
})
