import { describe, expect, it } from 'vitest'
import {
  canRedo,
  canUndo,
  isActionTracked,
  isActionUndoable,
} from '../src/utils'

describe.concurrent('canUndo', () => {
  const config = {
    undoableActions: ['file/add', 'file/remove'],
  }
  const actions = [
    { action: { type: 'file/add' }, undone: false },
    { action: { type: 'file/remove' }, undone: false },
    { action: { type: 'file/update' }, undone: false },
  ]

  it.concurrent('returns true if there are undoable actions', () => {
    expect(canUndo(config, actions)).toBe(true)
  })

  it.concurrent('returns false if no actions', () => {
    expect(canUndo(config, [])).toBe(false)
  })

  it.concurrent('returns false if all actions are undone', () => {
    const undoneActions = actions.map((a) => ({ ...a, undone: true }))
    expect(canUndo(config, undoneActions)).toBe(false)
  })
})

describe.concurrent('canRedo', () => {
  const config = { undoableActions: ['file/add', 'file/remove'] }
  const actions = [
    { action: { type: 'file/add' }, undone: false },
    { action: { type: 'file/remove' }, undone: true },
  ]

  it.concurrent('returns true if any action is undone', () => {
    expect(canRedo(config, actions)).toBe(true)
  })

  it.concurrent('returns false if no actions are undone', () => {
    const noUndone = actions.map((a) => ({ ...a, undone: false }))
    expect(canRedo(config, noUndone)).toBe(false)
  })
})

describe.concurrent('isActionUndoable', () => {
  const config = { undoableActions: ['file/add', 'file/remove'] }

  it.concurrent('returns true for undoable action', () => {
    expect(isActionUndoable(config, { type: 'file/add' })).toBe(true)
  })

  it.concurrent('returns false for non-undoable action', () => {
    expect(isActionUndoable(config, { type: 'file/update' })).toBe(false)
  })

  it.concurrent('returns true if undoableActions is empty', () => {
    expect(
      isActionUndoable({ undoableActions: [] }, { type: 'file/open' }),
    ).toBe(true)
  })
})

describe.concurrent('isActionTracked', () => {
  const config = { trackedActions: ['file/add', 'file/remove'] }

  it.concurrent('returns true for tracked action', () => {
    expect(isActionTracked(config, { type: 'file/add' })).toBe(true)
  })

  it.concurrent('returns false for non-tracked action', () => {
    expect(isActionTracked(config, { type: 'file/update' })).toBe(false)
  })

  it.concurrent('returns true if trackedActions is empty', () => {
    expect(isActionTracked({ trackedActions: [] }, { type: 'file/open' })).toBe(
      true,
    )
  })
})
