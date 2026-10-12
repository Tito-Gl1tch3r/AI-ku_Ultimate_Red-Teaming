import { Extension } from '@tiptap/core'
import { Plugin, PluginKey } from '@tiptap/pm/state'
import { Decoration, DecorationSet } from 'prosemirror-view'

export const aiAnchorKey = new PluginKey('aiAnchor')

export const getAiAnchorState = (state) => aiAnchorKey.getState(state) || null

export default Extension.create({
    name: 'aiAnchor',

    addCommands() {
        return {
            setAiAnchor: ({ from, to }) => ({ tr, dispatch }) => {
                if (dispatch)
                    dispatch(tr.setMeta(aiAnchorKey, { type: 'set', from, to }))
                return true
            },

            clearAiAnchor: () => ({ tr, dispatch }) => {
                if (dispatch)
                    dispatch(tr.setMeta(aiAnchorKey, { type: 'clear' }))
                return true
            },

            invalidateAiAnchor: () => ({ tr, dispatch }) => {
                if (dispatch)
                    dispatch(tr.setMeta(aiAnchorKey, { type: 'invalidate' }))
                return true
            }
        }
    },

    addProseMirrorPlugins() {
        return [
            new Plugin({
                key: aiAnchorKey,

                state: {
                    init: () => null,

                    apply: (tr, value) => {
                        const meta = tr.getMeta(aiAnchorKey)

                        if (meta?.type === 'set')
                            return { from: meta.from, to: meta.to, status: 'active' }

                        if (meta?.type === 'clear')
                            return null

                        // Positions are meaningless once the document is about to be
                        // wholesale replaced (e.g. modelValue set externally, or the
                        // owning editor is being destroyed) - keep the status so the
                        // UI can disable Apply, without pretending to track a range.
                        if (meta?.type === 'invalidate')
                            return { from: 0, to: 0, status: 'invalid' }

                        if (!value || value.status === 'invalid' || !tr.docChanged)
                            return value

                        const from = tr.mapping.map(value.from, 1)
                        const to = tr.mapping.map(value.to, -1)
                        const collapsed = to <= from
                        const nextFrom = collapsed ? Math.min(from, to) : from
                        const nextTo = collapsed ? nextFrom : to
                        const status = collapsed ? 'collapsed' : 'active'

                        if (nextFrom === value.from && nextTo === value.to && status === value.status)
                            return value

                        return { from: nextFrom, to: nextTo, status }
                    }
                },

                props: {
                    // Cached alongside the plugin state's reference equality (the
                    // reducer above returns the same object when nothing changed),
                    // so an unrelated transaction doesn't rebuild the decoration set.
                    decorations(state) {
                        const value = aiAnchorKey.getState(state)
                        if (!value || value.status !== 'active')
                            return DecorationSet.empty

                        if (this.lastValue === value)
                            return this.lastSet

                        this.lastValue = value
                        this.lastSet = DecorationSet.create(state.doc, [
                            Decoration.inline(value.from, value.to, { class: 'ai-anchor-highlight' })
                        ])
                        return this.lastSet
                    }
                }
            })
        ]
    }
})
