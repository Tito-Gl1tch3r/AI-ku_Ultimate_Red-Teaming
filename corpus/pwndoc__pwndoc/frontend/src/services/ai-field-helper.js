import Utils from '@/services/utils'
import { useAiGenerationStore } from '@/stores/ai-generation'

const FINDING_FIELD_OUTPUT_TYPES = {
  description: 'html',
  observation: 'html',
  remediation: 'html',
  poc: 'html',
  references: 'array'
}

// Must match CUSTOM_FIELD_OUTPUT_TYPES in backend/src/lib/ai-prompts.js, which independently
// derives the same output type when building the field's default generation prompt. The two
// can't share a module across the Node/browser boundary; covered by tests in both suites
// (ai-field-helper.test.js / backend/tests/ai-prompts.test.js) instead.
const CUSTOM_FIELD_OUTPUT_TYPES = {
  text: 'html',
  input: 'text',
  date: 'text',
  select: 'text',
  radio: 'text',
  'select-multiple': 'array',
  checkbox: 'array'
}

const getFieldLabel = (field, customField, fieldKey) => {
  if (customField?.customField?.label)
    return customField.customField.label

  return {
    description: 'Description',
    observation: 'Observation',
    remediation: 'Remediation',
    references: 'References',
    poc: 'Proofs'
  }[field] || fieldKey
}

const getOutputType = (field, customField) => {
  if (customField)
    return CUSTOM_FIELD_OUTPUT_TYPES[customField?.customField?.fieldType] || 'text'

  return FINDING_FIELD_OUTPUT_TYPES[field] || 'html'
}

const normalizeContextValue = (value) => {
  if (value === null || value === undefined)
    return ''
  if (Array.isArray(value))
    return value.join(', ')
  if (typeof value === 'object')
    return JSON.stringify(value)
  return String(value)
}

const renderPromptTemplate = (template = '', context = {}) => {
  return String(template || '').replace(/\{([a-zA-Z0-9_]+)\}/g, (match, key) => {
    return normalizeContextValue(context[key])
  }).trim()
}

const getDefaultPrompt = (fieldPrompts = [], fieldKey, context = {}) => {
  const mapping = (fieldPrompts || []).find((entry) => {
    return String(entry.fieldKey || '') === String(fieldKey)
  })
  return renderPromptTemplate(mapping?.prompt || '', context)
}

const normalizeDraftForApply = (draft, outputType) => {
  if (outputType === 'array') {
    const entries = Array.isArray(draft) ?
      draft :
      String(draft || '').split('\n')

    return entries
      .map((entry) => String(entry || '').trim())
      .filter(Boolean)
  }

  const text = String(draft || '').trim()
  if (outputType === 'html')
    return Utils.htmlEncode(text)

  return text
}

const getInputSelection = (inputRef) => {
  const el = inputRef?.$el?.querySelector('textarea, input')
  if (!el)
    return null

  const start = el.selectionStart
  const end = el.selectionEnd
  if (start === end)
    return null

  const text = el.value.substring(start, end)
  return {
    start,
    end,
    text,
    html: text
  }
}

const CUSTOM_FIELD_PREFIX = 'custom-field:'

const cloneData = (data) => JSON.parse(JSON.stringify(data))

const parseFieldKey = (fieldKey) => {
  const key = String(fieldKey || '')
  if (key.startsWith(CUSTOM_FIELD_PREFIX)) {
    return {
      kind: 'custom',
      customFieldId: key.slice(CUSTOM_FIELD_PREFIX.length)
    }
  }

  return { kind: 'standard', field: key }
}

const findCustomField = (container, customFieldId) => {
  const fields = container?.customFields
  if (!Array.isArray(fields))
    return null

  return fields.find((entry) => {
    const id = entry?.customField?._id || entry?.customField
    return String(id) === String(customFieldId)
  })
}

const getFieldContainer = (entity, entityShape, locale) => {
  if (entityShape === 'vulnerability') {
    const details = entity?.details
    if (!Array.isArray(details))
      return null
    return details.find((detail) => detail.locale === locale) || details[0]
  }

  if (entityShape === 'finding' || entityShape === 'section')
    return entity

  return entity
}

const getFieldValue = (entity, entityShape, fieldKey, locale) => {
  const container = getFieldContainer(entity, entityShape, locale)
  if (!container)
    return undefined

  const parsed = parseFieldKey(fieldKey)
  if (parsed.kind === 'custom')
    return findCustomField(container, parsed.customFieldId)?.text

  return container[parsed.field]
}

const getContextFieldValue = (context, fieldKey) => {
  const parsed = parseFieldKey(fieldKey)
  if (parsed.kind === 'custom')
    return context?.customFieldValue || ''

  return context?.[parsed.field] || ''
}

const withCurrentFieldContext = (context, fieldKey, fieldLabel) => ({
  ...(context || {}),
  currentFieldKey: fieldKey,
  currentFieldLabel: fieldLabel || fieldKey,
  currentFieldValue: getContextFieldValue(context || {}, fieldKey)
})

const setFieldValue = (entity, entityShape, fieldKey, locale, value) => {
  const result = cloneData(entity)
  const container = getFieldContainer(result, entityShape, locale)
  if (!container)
    return result

  const parsed = parseFieldKey(fieldKey)
  if (parsed.kind === 'custom') {
    const customField = findCustomField(container, parsed.customFieldId)
    if (customField)
      customField.text = value
  } else {
    container[parsed.field] = value
  }

  return result
}

const applySelectionToValue = (value, selection, replacement, outputType) => {
  const repl = Array.isArray(replacement) ?
    replacement.join('\n') :
    String(replacement || '')

  if (outputType === 'array') {
    const text = Array.isArray(value) ? value.join('\n') : String(value || '')
    const next = text.substring(0, selection.start) + repl + text.substring(selection.end)
    return next
      .split('\n')
      .map((entry) => entry.trim())
      .filter(Boolean)
  }

  const text = String(value || '')
  return text.substring(0, selection.start) + repl + text.substring(selection.end)
}

const createDiffContext = ({
  getDiffEntity,
  entityShape,
  fieldKey,
  locale,
  outputType,
  mode,
  selection = null,
  getSelectionPreviewValue = null,
  languages = []
}) => ({
  getDiffEntity,
  entityShape,
  fieldKey,
  locale,
  outputType,
  mode,
  selection: selection ? { ...selection } : null,
  getSelectionPreviewValue: typeof getSelectionPreviewValue === 'function' ? getSelectionPreviewValue : null,
  languages: languages || []
})

export default {
  getOutputType,
  getFieldLabel,
  getDefaultPrompt,
  getInputSelection,

  // `current` lets a caller that already cloned the entity (e.g. to also show it
  // as-is in the diff view) reuse that clone instead of re-deriving it here.
  buildAiDiffDraft(diffContext, draft, current = null) {
    if (!diffContext?.getDiffEntity)
      return null

    const {
      getDiffEntity,
      entityShape,
      fieldKey,
      locale,
      outputType,
      mode,
      selection,
      getSelectionPreviewValue
    } = diffContext
    const base = current || cloneData(getDiffEntity())
    const normalized = normalizeDraftForApply(draft, outputType)

    let nextValue = normalized
    if (mode === 'selection' && selection) {
      // Rich-text selections are tracked live (ProseMirror positions remapped
      // through edits) - ask the editor to simulate the replacement over the
      // current anchor rather than splicing stale start/end offsets.
      if (typeof getSelectionPreviewValue === 'function') {
        nextValue = getSelectionPreviewValue(normalized)
        if (nextValue === null || nextValue === undefined)
          return null
      } else if (selection.start != null) {
        const currentValue = getFieldValue(base, entityShape, fieldKey, locale)
        nextValue = applySelectionToValue(currentValue, selection, normalized, outputType)
      } else {
        return null
      }
    }

    return setFieldValue(base, entityShape, fieldKey, locale, nextValue)
  },

  cloneEntity(entity) {
    return cloneData(entity)
  },

  isFieldSessionActive(lockKey) {
    return useAiGenerationStore().isFieldSessionActive(lockKey)
  },

  isFieldSelectionLocked(lockKey) {
    return useAiGenerationStore().isFieldSelectionLocked(lockKey)
  },

  // Shared orchestration for "generate + apply" used identically by findings,
  // sections and vulnerabilities: resolve output type/label/context, branch
  // on whether text was selected (anchored partial replace) vs not (whole-field
  // replace), and always release the selection anchor on the way out. Error
  // display stays with the caller (its own try/catch), matching this app's
  // existing convention of showing Notify at the page/component level.
  async runFieldSession({
    field,
    customField = null,
    fieldKey,
    lockKey,
    selectionTarget,
    entityShape,
    requestEntityType,
    locale,
    aiFieldPrompts,
    buildContext,
    getDiffEntity,
    setValue,
    languages = []
  }) {
    const selection = selectionTarget?.getTextSelection?.()
    const outputType = getOutputType(field, customField)
    const fieldLabel = getFieldLabel(field, customField, fieldKey)
    const baseContext = buildContext()
    const requestParams = {
      entityType: requestEntityType,
      field: fieldKey,
      locale,
      outputType,
      context: baseContext
    }

    try {
      if (selection?.text) {
        selectionTarget?.setAiSelectionAnchor?.(selection)

        // Resolves only when the drawer closes. Apply/Apply selection write
        // straight to the anchored range via onPartialApply, repeatably,
        // without ending the session.
        await this.runSelectionAiChat({
          title: `AI - ${fieldLabel}`,
          selectedText: selection.text,
          outputType,
          lockKey,
          selection,
          getDiffEntity,
          entityShape,
          languages,
          getSelectionPreviewValue: (html) => selectionTarget?.buildAnchoredPreviewHtml?.(html),
          onPartialApply: (content) => this.applySelectionDraft({
            selectionTarget,
            selection,
            draft: content,
            outputType,
            reanchor: true
          }),
          requestParams: {
            ...requestParams,
            context: {
              ...baseContext,
              selectedText: selection.text,
              selectedHtml: selection.html || selection.text
            }
          }
        })
        return
      }

      const defaultPrompt = getDefaultPrompt(aiFieldPrompts, fieldKey, baseContext)

      // Same as above: resolves only when the drawer closes. Apply writes the
      // whole field via onApply, repeatably.
      await this.runFieldAiChat({
        title: `AI - ${fieldLabel}`,
        defaultPrompt,
        outputType,
        fieldLabel,
        lockKey,
        getDiffEntity,
        entityShape,
        languages,
        onApply: (content) => this.applyFieldDraft({
          draft: content,
          outputType,
          setValue
        }),
        onInsertAtCursor: selectionTarget?.insertAtCursor ?
          (content) => this.applyInsertAtCursor({ selectionTarget, draft: content, outputType }) :
          null,
        requestParams
      })
    } finally {
      // No-op unless a selection-mode anchor was set above.
      selectionTarget?.clearAiSelectionAnchor?.()
    }
  },

  async runFieldAiChat({
    title,
    defaultPrompt,
    outputType,
    requestParams,
    fieldLabel = null,
    lockKey = null,
    onCancel,
    onApply = null,
    onInsertAtCursor = null,
    getDiffEntity = null,
    entityShape = null,
    languages = []
  }) {
    const diffContext = (typeof getDiffEntity === 'function' && entityShape) ?
      createDiffContext({
        getDiffEntity,
        entityShape,
        fieldKey: requestParams.field,
        locale: requestParams.locale,
        outputType,
        mode: 'field',
        languages
      }) :
      null

    try {
      const scopedRequestParams = {
        ...requestParams,
        context: withCurrentFieldContext(
          requestParams?.context || {},
          requestParams?.field,
          fieldLabel || title
        )
      }

      // Resolves only when the drawer closes - applying happens via onApply/
      // onInsertAtCursor as the user clicks, not by settling this promise.
      return await useAiGenerationStore().openSession({
        title,
        defaultPrompt,
        outputType,
        requestParams: scopedRequestParams,
        lockKey,
        diffContext,
        mode: 'field',
        onApply,
        onInsertAtCursor
      })
    } catch (err) {
      if (err?.message === 'cancelled') {
        if (typeof onCancel === 'function')
          onCancel()
        return null
      }
      throw err
    }
  },

  applyFieldDraft({
    draft,
    outputType,
    setValue
  }) {
    setValue(normalizeDraftForApply(draft, outputType))
  },

  async runSelectionAiChat({
    title,
    selectedText,
    outputType,
    requestParams,
    lockKey = null,
    onCancel,
    onPartialApply = null,
    selection = null,
    getDiffEntity = null,
    entityShape = null,
    getSelectionPreviewValue = null,
    languages = []
  }) {
    const diffContext = (typeof getDiffEntity === 'function' && entityShape && selection) ?
      createDiffContext({
        getDiffEntity,
        entityShape,
        fieldKey: requestParams.field,
        locale: requestParams.locale,
        outputType,
        mode: 'selection',
        selection,
        getSelectionPreviewValue,
        languages
      }) :
      null

    try {
      return await useAiGenerationStore().openSession({
        title,
        selectedText,
        outputType,
        requestParams,
        lockKey,
        diffContext,
        mode: 'selection',
        onPartialApply
      })
    } catch (err) {
      if (err?.message === 'cancelled') {
        if (typeof onCancel === 'function')
          onCancel()
        return null
      }
      throw err
    }
  },

  applySelectionDraft({
    selectionTarget,
    selection,
    draft,
    outputType,
    reanchor = false
  }) {
    const normalizedDraft = normalizeDraftForApply(draft, outputType)

    if (selectionTarget?.replaceTextSelection) {
      selectionTarget.replaceTextSelection(normalizedDraft, selection, { reanchor })
      return
    }

    if (selectionTarget?.editor?.replaceTextSelection) {
      selectionTarget.editor.replaceTextSelection(normalizedDraft, selection, { reanchor })
    }
  },

  applyInsertAtCursor({ selectionTarget, draft, outputType }) {
    const normalizedDraft = normalizeDraftForApply(draft, outputType)
    selectionTarget?.insertAtCursor?.(normalizedDraft)
  },

  buildFindingAiContext(finding, customField) {
    const customFieldContext = {}
    if (finding.customFields && finding.customFields.length > 0) {
      finding.customFields.forEach((entry) => {
        if (entry?.customField?.label)
          customFieldContext[entry.customField.label] = entry.text
      })
    }

    return {
      title: finding.title || '',
      vulnType: finding.vulnType || '',
      observation: finding.observation || '',
      description: finding.description || '',
      remediation: finding.remediation || '',
      references: finding.references || [],
      poc: finding.poc || '',
      scope: finding.scope || '',
      customFieldLabel: customField?.customField?.label || '',
      customFieldValue: customField?.text || '',
      customFields: customFieldContext
    }
  },

  buildSectionAiContext(section, customField) {
    const customFieldContext = {}
    if (section.customFields && section.customFields.length > 0) {
      section.customFields.forEach((entry) => {
        if (entry?.customField?.label)
          customFieldContext[entry.customField.label] = entry.text
      })
    }

    return {
      sectionField: section.field || '',
      sectionName: section.name || '',
      sectionText: section.text || '',
      customFieldLabel: customField?.customField?.label || '',
      customFieldValue: customField?.text || '',
      customFields: customFieldContext
    }
  },

  buildVulnerabilityAiContext(vulnerability, detail, customField) {
    const customFieldContext = {}
    if (detail?.customFields && detail.customFields.length > 0) {
      detail.customFields.forEach((entry) => {
        if (entry?.customField?.label)
          customFieldContext[entry.customField.label] = entry.text
      })
    }

    return {
      title: detail?.title || '',
      vulnType: detail?.vulnType || '',
      category: vulnerability?.category || '',
      observation: detail?.observation || '',
      description: detail?.description || '',
      remediation: detail?.remediation || '',
      references: detail?.references || [],
      customFieldLabel: customField?.customField?.label || '',
      customFieldValue: customField?.text || '',
      customFields: customFieldContext
    }
  }
}
