import { describe, expect, it } from 'vitest'
import type { Store, UnknownAction } from 'redux'
import { legacy_createStore as createStore } from 'redux'

import {
  ActionCreators,
  ActionTypes,
  type HistoryAction,
  type HistoryState,
  type UndoableActionsConfig,
  undoableActions,
} from '../src'
import { HISTORY_KEY } from '../src/actions'

const counterReducer = (
  state = { name: 'Counter', count: 0 },
  action: UnknownAction,
): { name: string; count: number } => {
  switch (action.type) {
    case 'counter/increment':
      return {
        ...state,
        count: state.count + ((action.payload as number) || 1),
      }
    case 'counter/decrement':
      return {
        ...state,
        count: state.count - ((action.payload as number) || 1),
      }
    case 'counter/start':
      return { ...state, count: action.payload as number }
    case 'counter/changeName':
      return state.name === action.payload
        ? state
        : { ...state, name: action.payload as string }
    case 'counter/clone':
      return { ...state }
    default:
      return state
  }
}

function expectCount(
  store: Store<HistoryState<{ name: string; count: number }, UnknownAction>>,
  expectedCount: number,
) {
  expect(store.getState().present.count).toStrictEqual(expectedCount)
}

function expectHistoryActions(
  store: Store<HistoryState<{ name: string; count: number }, UnknownAction>>,
  expectedActions: HistoryAction<UnknownAction>[],
) {
  expect(store.getState()[HISTORY_KEY].actions).toStrictEqual(expectedActions)
}

describe.concurrent('undoableActions', () => {
  it.concurrent('should initialize with default state', () => {
    const store = createStore(undoableActions(counterReducer))
    expectCount(store, 0)
    expectHistoryActions(store, [])
    expect(store.getState().canUndo).toStrictEqual(false)
    expect(store.getState().canRedo).toStrictEqual(false)
  })

  it.concurrent('should not undo if action history is empty', () => {
    const store = createStore(undoableActions(counterReducer))
    store.dispatch(ActionCreators.undo())
    expectCount(store, 0)
    expectHistoryActions(store, [])
    expect(store.getState().canUndo).toStrictEqual(false)
    expect(store.getState().canRedo).toStrictEqual(false)
  })

  it.concurrent('should not redo if there are no future actions', () => {
    const store = createStore(undoableActions(counterReducer))
    store.dispatch(ActionCreators.redo())
    expectCount(store, 0)
    expect(store.getState().canUndo).toStrictEqual(false)
    expect(store.getState().canRedo).toStrictEqual(false)

    store.dispatch({ type: 'counter/increment' })
    expectCount(store, 1)
    expect(store.getState().canUndo).toStrictEqual(true)
    expect(store.getState().canRedo).toStrictEqual(false)
  })

  it.concurrent('should handle multiple undos and redos', () => {
    const store = createStore(undoableActions(counterReducer))
    store.dispatch({ type: 'counter/increment', payload: 1 })
    store.dispatch({ type: 'counter/increment', payload: 2 })
    store.dispatch({ type: 'counter/increment', payload: 3 })
    expectCount(store, 6)
    expect(store.getState().canUndo).toStrictEqual(true)
    expect(store.getState().canRedo).toStrictEqual(false)

    store.dispatch(ActionCreators.undo())
    expectCount(store, 3)
    expect(store.getState().canUndo).toStrictEqual(true)
    expect(store.getState().canRedo).toStrictEqual(true)

    store.dispatch(ActionCreators.undo())
    expectCount(store, 1)
    expect(store.getState().canUndo).toStrictEqual(true)
    expect(store.getState().canRedo).toStrictEqual(true)

    store.dispatch(ActionCreators.undo())
    expectCount(store, 0)
    expect(store.getState().canUndo).toStrictEqual(false)
    expect(store.getState().canRedo).toStrictEqual(true)

    // Further undo should not change state
    store.dispatch(ActionCreators.undo())
    expectCount(store, 0)
    expect(store.getState().canUndo).toStrictEqual(false)
    expect(store.getState().canRedo).toStrictEqual(true)

    // Redo all
    store.dispatch(ActionCreators.redo())
    expectCount(store, 1)
    expect(store.getState().canUndo).toStrictEqual(true)
    expect(store.getState().canRedo).toStrictEqual(true)

    store.dispatch(ActionCreators.redo())
    expectCount(store, 3)
    expect(store.getState().canUndo).toStrictEqual(true)
    expect(store.getState().canRedo).toStrictEqual(true)

    store.dispatch(ActionCreators.redo())
    expectCount(store, 6)
    expect(store.getState().canUndo).toStrictEqual(true)
    expect(store.getState().canRedo).toStrictEqual(false)

    // Further redo should not change state
    store.dispatch(ActionCreators.redo())
    expectCount(store, 6)
    expect(store.getState().canUndo).toStrictEqual(true)
    expect(store.getState().canRedo).toStrictEqual(false)
  })

  it.concurrent(
    'should apply actions with payloads and support undo/redo',
    () => {
      const store = createStore(undoableActions(counterReducer))
      store.dispatch({ type: 'counter/increment', payload: 2 })
      expectCount(store, 2)
      expect(store.getState().canUndo).toStrictEqual(true)
      expect(store.getState().canRedo).toStrictEqual(false)

      store.dispatch({ type: 'counter/increment', payload: 3 })
      expectCount(store, 5)
      expect(store.getState().canUndo).toStrictEqual(true)
      expect(store.getState().canRedo).toStrictEqual(false)

      store.dispatch(ActionCreators.undo())
      expectCount(store, 2)
      expect(store.getState().canUndo).toStrictEqual(true)
      expect(store.getState().canRedo).toStrictEqual(true)

      store.dispatch(ActionCreators.redo())
      expectCount(store, 5)
      expect(store.getState().canUndo).toStrictEqual(true)
      expect(store.getState().canRedo).toStrictEqual(false)
    },
  )

  it.concurrent('should store full actions including payload', () => {
    const store = createStore(undoableActions(counterReducer))
    const action = { type: 'counter/increment', payload: 10 }
    store.dispatch(action)
    expectHistoryActions(store, [{ action, undone: false }])
    expectCount(store, 10)
    expect(store.getState().canUndo).toStrictEqual(true)
    expect(store.getState().canRedo).toStrictEqual(false)
  })

  it.concurrent('should reset the state', () => {
    const store = createStore(undoableActions(counterReducer))
    store.dispatch({ type: 'counter/increment', payload: 10 })
    expectHistoryActions(store, [
      { action: { type: 'counter/increment', payload: 10 }, undone: false },
    ])
    expectCount(store, 10)

    store.dispatch(ActionCreators.reset())
    expectHistoryActions(store, [])
    expectCount(store, 0)
  })

  it.concurrent('should clear future on new action after undo', () => {
    const store = createStore(undoableActions(counterReducer))
    store.dispatch({ type: 'counter/increment' })
    store.dispatch({ type: 'counter/increment' })
    expectCount(store, 2)
    expect(store.getState().canUndo).toStrictEqual(true)
    expect(store.getState().canRedo).toStrictEqual(false)

    store.dispatch(ActionCreators.undo())
    expectCount(store, 1)
    expect(store.getState().canUndo).toStrictEqual(true)
    expect(store.getState().canRedo).toStrictEqual(true)

    store.dispatch({ type: 'counter/increment', payload: 5 })
    expectCount(store, 6)
    expect(store.getState().canUndo).toStrictEqual(true)
    expect(store.getState().canRedo).toStrictEqual(false)
  })
  it.concurrent('hydrates state with actions', () => {
    const store = createStore(undoableActions(counterReducer))

    const actions: HistoryAction<UnknownAction>[] = [
      { action: { type: 'counter/increment' }, undone: false },
      { action: { type: 'counter/increment' }, undone: false },
      { action: { type: 'counter/increment', payload: 10 }, undone: true },
    ]

    store.dispatch(ActionCreators.hydrate({ actions, tracking: true }))

    expectCount(store, 2)

    expect(store.getState()[HISTORY_KEY].tracking).toStrictEqual(true)
    expect(store.getState().canUndo).toStrictEqual(true)
    expect(store.getState().canRedo).toStrictEqual(true)

    store.dispatch(ActionCreators.redo())

    expectCount(store, 12)
    expect(store.getState().canUndo).toStrictEqual(true)
    expect(store.getState().canRedo).toStrictEqual(false)

    store.dispatch(ActionCreators.undo())

    expectCount(store, 2)
    expect(store.getState().canUndo).toStrictEqual(true)
    expect(store.getState().canRedo).toStrictEqual(true)

    store.dispatch(ActionCreators.undo())

    expectCount(store, 1)
    expect(store.getState().canUndo).toStrictEqual(true)
    expect(store.getState().canRedo).toStrictEqual(true)

    store.dispatch(ActionCreators.undo())

    expectCount(store, 0)
    expect(store.getState().canUndo).toStrictEqual(false)
    expect(store.getState().canRedo).toStrictEqual(true)
  })

  it.concurrent(
    'should not track actions that do not change the state of the reducer',
    () => {
      const store = createStore(undoableActions(counterReducer))

      store.dispatch({ type: 'counter/increment', payload: 1 })
      expectCount(store, 1)
      expectHistoryActions(store, [
        { action: { type: 'counter/increment', payload: 1 }, undone: false },
      ])

      // Dispatching an action that does not change the state
      store.dispatch({ type: 'unknown/action' })
      expectCount(store, 1)
      expectHistoryActions(store, [
        { action: { type: 'counter/increment', payload: 1 }, undone: false },
      ])

      // Dispatching another action that does not change the state
      expect(store.getState().present.name).toStrictEqual('Counter')
      store.dispatch({
        type: 'counter/changeName',
        payload: 'Counter',
      })
      expectHistoryActions(store, [
        { action: { type: 'counter/increment', payload: 1 }, undone: false },
      ])
    },
  )

  it.concurrent('tracks a new state reference with equal values', () => {
    const store = createStore(undoableActions(counterReducer))

    store.dispatch({ type: 'counter/clone' })

    expectHistoryActions(store, [
      { action: { type: 'counter/clone' }, undone: false },
    ])
  })
})

describe('immutable action history', () => {
  const amountReducer = (
    state = { total: 0 },
    action: UnknownAction,
  ): { total: number } => {
    if (action.type !== 'amount/add') {
      return state
    }
    const payload = action.payload as { amount: number }
    return { total: state.total + payload.amount }
  }

  it('copies and deeply freezes tracked actions', () => {
    const store = createStore(
      undoableActions(amountReducer, {
        trackedActions: ['amount/add'],
        undoableActions: ['amount/add'],
      }),
    )
    expect(Object.isFrozen(store.getState()[HISTORY_KEY].actions)).toBe(true)

    const action = {
      type: 'amount/add',
      payload: { amount: 2, labels: ['first'] },
    }
    store.dispatch(action)

    const actions = store.getState()[HISTORY_KEY].actions
    const captured = actions[0]
    const capturedPayload = captured.action.payload as {
      amount: number
      labels: string[]
    }

    expect(Object.isFrozen(actions)).toBe(true)
    expect(Object.isFrozen(captured)).toBe(true)
    expect(Object.isFrozen(captured.action)).toBe(true)
    expect(Object.isFrozen(capturedPayload)).toBe(true)
    expect(Object.isFrozen(capturedPayload.labels)).toBe(true)
    expect(captured.action).not.toBe(action)
    expect(capturedPayload).not.toBe(action.payload)
    expect(Object.isFrozen(action)).toBe(false)
    expect(Object.isFrozen(action.payload)).toBe(false)

    action.payload.amount = 50
    action.payload.labels.push('mutated later')

    expect(capturedPayload).toEqual({ amount: 2, labels: ['first'] })
    store.dispatch(ActionCreators.undo())
    store.dispatch(ActionCreators.redo())
    expect(store.getState().present.total).toBe(2)
    expect(Object.isFrozen(store.getState()[HISTORY_KEY].actions)).toBe(true)
    expect(Object.isFrozen(store.getState()[HISTORY_KEY].actions[0])).toBe(true)
  })

  it('copies and freezes hydrated history', () => {
    const store = createStore(
      undoableActions(amountReducer, {
        trackedActions: ['amount/add'],
        undoableActions: ['amount/add'],
      }),
    )
    const payload = {
      tracking: true,
      actions: [
        {
          action: { type: 'amount/add', payload: { amount: 3 } },
          undone: true,
        },
      ],
    }

    store.dispatch(ActionCreators.hydrate(payload))
    const captured = store.getState()[HISTORY_KEY].actions[0]
    const capturedPayload = captured.action.payload as { amount: number }

    expect(store.getState().present.total).toBe(0)
    expect(captured).not.toBe(payload.actions[0])
    expect(captured.action).not.toBe(payload.actions[0].action)
    expect(Object.isFrozen(store.getState()[HISTORY_KEY].actions)).toBe(true)
    expect(Object.isFrozen(capturedPayload)).toBe(true)

    payload.actions[0].action.payload.amount = 100
    store.dispatch(ActionCreators.redo())
    expect(store.getState().present.total).toBe(3)
  })

  it('normalizes and owns history supplied as preloaded Redux state', () => {
    const preloadedAction = {
      type: 'amount/add',
      payload: { amount: 4 },
    }
    const preloadedActions = Object.freeze([
      { action: preloadedAction, undone: false },
    ])
    const preloadedState: HistoryState<{ total: number }, UnknownAction> = {
      present: { total: 4 },
      canUndo: true,
      canRedo: false,
      [HISTORY_KEY]: {
        tracking: true,
        actions: preloadedActions,
        snapshot: { total: 0 },
      },
    }

    const store = createStore(
      undoableActions(amountReducer, {
        trackedActions: ['amount/add'],
        undoableActions: ['amount/add'],
      }),
      preloadedState,
    )

    const capturedActions = store.getState()[HISTORY_KEY].actions
    const capturedPayload = capturedActions[0].action.payload as {
      amount: number
    }
    expect(capturedActions).not.toBe(preloadedState[HISTORY_KEY].actions)
    expect(capturedActions[0].action).not.toBe(preloadedAction)
    expect(Object.isFrozen(capturedActions)).toBe(true)
    expect(Object.isFrozen(capturedActions[0])).toBe(true)
    expect(Object.isFrozen(capturedActions[0].action)).toBe(true)
    expect(Object.isFrozen(capturedPayload)).toBe(true)

    preloadedAction.payload.amount = 100
    store.dispatch(ActionCreators.undo())
    expect(store.getState().present.total).toBe(0)
    store.dispatch(ActionCreators.redo())
    expect(store.getState().present.total).toBe(4)
  })

  it('preserves sparse arrays and their own data properties', () => {
    const metadataKey = Symbol('metadata')
    type EnrichedArray = unknown[] & {
      label: { value: string }
      [metadataKey]: { value: string }
    }
    const shapeReducer = (state = 'initial', action: UnknownAction): string => {
      if (action.type !== 'shape/read') {
        return state
      }
      const payload = action.payload as EnrichedArray
      return [
        0 in payload,
        payload.length,
        payload.label.value,
        payload[metadataKey].value,
      ].join(':')
    }
    const payload = new Array(2) as EnrichedArray
    payload[1] = { value: 'second' }
    Object.defineProperty(payload, 'label', {
      configurable: true,
      enumerable: false,
      value: { value: 'label' },
      writable: true,
    })
    payload[metadataKey] = { value: 'symbol' }
    const store = createStore(
      undoableActions(shapeReducer, {
        trackedActions: ['shape/read'],
        undoableActions: ['shape/read'],
      }),
    )

    store.dispatch({ type: 'shape/read', payload })

    const capturedPayload = store.getState()[HISTORY_KEY].actions[0].action
      .payload as EnrichedArray
    expect(0 in capturedPayload).toBe(false)
    expect(1 in capturedPayload).toBe(true)
    expect(capturedPayload).toHaveLength(2)
    expect(
      Object.getOwnPropertyDescriptor(capturedPayload, 'label'),
    ).toMatchObject({ enumerable: false, writable: false })
    expect(capturedPayload.label).toEqual({ value: 'label' })
    expect(capturedPayload[metadataKey]).toEqual({ value: 'symbol' })
    expect(Object.isFrozen(capturedPayload.label)).toBe(true)
    expect(Object.isFrozen(capturedPayload[metadataKey])).toBe(true)

    payload[0] = 'added later'
    payload.label.value = 'changed'
    payload[metadataKey].value = 'changed'
    store.dispatch(ActionCreators.undo())
    store.dispatch(ActionCreators.redo())
    expect(store.getState().present).toBe('false:2:label:symbol')
  })

  it('preserves cycles and shared references in non-persisted history', () => {
    const shared = { value: 'shared' }
    const payload: {
      amount: number
      left: { value: string }
      right: { value: string }
      self?: unknown
    } = { amount: 1, left: shared, right: shared }
    payload.self = payload
    const store = createStore(
      undoableActions(amountReducer, { trackedActions: ['amount/add'] }),
    )

    store.dispatch({ type: 'amount/add', payload })

    const capturedPayload = store.getState()[HISTORY_KEY].actions[0].action
      .payload as typeof payload
    expect(capturedPayload).not.toBe(payload)
    expect(capturedPayload.self).toBe(capturedPayload)
    expect(capturedPayload.left).toBe(capturedPayload.right)
    expect(capturedPayload.left).not.toBe(shared)
    expect(Object.isFrozen(capturedPayload)).toBe(true)
    expect(Object.isFrozen(capturedPayload.left)).toBe(true)
  })

  it('rejects non-plain action history values with their path', () => {
    const reducer = undoableActions(amountReducer, {
      trackedActions: ['amount/add'],
    })
    const store = createStore(reducer)

    expect(() =>
      store.dispatch({
        type: 'amount/add',
        payload: { amount: 1, createdAt: new Date() },
      }),
    ).toThrow('Cannot store non-plain value at action.payload.createdAt')
  })

  it('allows opting out for non-plain action payload compatibility', () => {
    const reducer = undoableActions(amountReducer, {
      immutableHistory: false,
      trackedActions: ['amount/add'],
    })
    const store = createStore(reducer)
    const action = {
      type: 'amount/add',
      payload: { amount: 1, createdAt: new Date() },
    }

    store.dispatch(action)

    const actions = store.getState()[HISTORY_KEY].actions
    expect(actions[0].action).toBe(action)
    expect(Object.isFrozen(actions)).toBe(false)
    expect(Object.isFrozen(actions[0])).toBe(false)
  })

  it('retains every action in a long history', () => {
    const store = createStore(
      undoableActions(amountReducer, {
        trackedActions: ['amount/add'],
        undoableActions: ['amount/add'],
      }),
    )

    for (let index = 1; index <= 1_000; index += 1) {
      store.dispatch({ type: 'amount/add', payload: { amount: index } })
    }

    const actions = store.getState()[HISTORY_KEY].actions
    expect(actions).toHaveLength(1_000)
    expect(actions[0].action.payload).toEqual({ amount: 1 })
    expect(actions.at(-1)?.action.payload).toEqual({ amount: 1_000 })
    expect(actions.every((action) => Object.isFrozen(action))).toBe(true)
    expect(Object.isFrozen(actions)).toBe(true)
  })

  it('keeps immutableHistory optional in the full public config type', () => {
    const config: UndoableActionsConfig = {
      trackedActions: ['amount/add'],
      undoableActions: ['amount/add'],
      internalActions: {
        undo: 'history/undo',
        redo: 'history/redo',
        reset: 'history/reset',
        hydrate: 'history/hydrate',
        tracking: 'history/tracking',
      },
    }
    const store = createStore(undoableActions(amountReducer, config))

    store.dispatch({ type: 'amount/add', payload: { amount: 1 } })

    expect(Object.isFrozen(store.getState()[HISTORY_KEY].actions)).toBe(true)
  })

  it('uses the immutable default when the optional setting is undefined', () => {
    const store = createStore(
      undoableActions(amountReducer, {
        immutableHistory: undefined,
        trackedActions: ['amount/add'],
      }),
    )

    store.dispatch({ type: 'amount/add', payload: { amount: 1 } })

    expect(Object.isFrozen(store.getState()[HISTORY_KEY].actions)).toBe(true)
  })
})

describe.concurrent('undoableActions with custom config', () => {
  it.concurrent('should only track actions when the state changes', () => {
    const store = createStore(
      undoableActions(counterReducer, {
        undoableActions: ['counter/increment', 'counter/decrement'],
        trackAfterAction: 'counter/start',
        internalActions: {
          undo: 'counter/undo',
          redo: 'counter/redo',
        },
      }),
    )

    expectCount(store, 0)
    expectHistoryActions(store, [])
    expect(store.getState().canUndo).toStrictEqual(false)
    expect(store.getState().canRedo).toStrictEqual(false)

    store.dispatch({ type: 'counter/increment', payload: 5 })
    expectCount(store, 5)
    expectHistoryActions(store, [])
    expect(store.getState()[HISTORY_KEY].tracking).toStrictEqual(false)
    expect(store.getState().canUndo).toStrictEqual(false)
    expect(store.getState().canRedo).toStrictEqual(false)

    store.dispatch({ type: 'counter/start', payload: 10 })
    expectCount(store, 10)
    expectHistoryActions(store, [])
    expect(store.getState()[HISTORY_KEY].tracking).toStrictEqual(true)
    expect(store.getState().canUndo).toStrictEqual(false)
    expect(store.getState().canRedo).toStrictEqual(false)

    store.dispatch({ type: 'counter/increment', payload: 5 })
    expectCount(store, 15)
    expectHistoryActions(store, [
      { action: { type: 'counter/increment', payload: 5 }, undone: false },
    ])
    expect(store.getState().canUndo).toStrictEqual(true)
    expect(store.getState().canRedo).toStrictEqual(false)

    store.dispatch({ type: 'counter/changeName', payload: 'New Counter Name' })

    store.dispatch({ type: 'counter/undo' })
    expectCount(store, 10)
    expect(store.getState().present.name).toStrictEqual('New Counter Name')
    expect(store.getState().canUndo).toStrictEqual(false)
    expect(store.getState().canRedo).toStrictEqual(true)

    store.dispatch({ type: 'counter/undo' })
    expectCount(store, 10)
    expect(store.getState().present.name).toStrictEqual('New Counter Name')
    expect(store.getState().canUndo).toStrictEqual(false)
    expect(store.getState().canRedo).toStrictEqual(true)

    store.dispatch({ type: 'counter/redo' })
    expectCount(store, 15)
    expect(store.getState().present.name).toStrictEqual('New Counter Name')
    expect(store.getState().canUndo).toStrictEqual(true)
    expect(store.getState().canRedo).toStrictEqual(false)
  })

  it.concurrent('should only track tracked-actions when config is set', () => {
    const store = createStore(
      undoableActions(counterReducer, {
        trackedActions: [
          'counter/increment',
          'counter/decrement',
          'counter/changeName',
        ],
        undoableActions: ['counter/increment', 'counter/decrement'],
        trackAfterAction: 'counter/start',
      }),
    )

    store.dispatch({ type: 'counter/increment', payload: 5 })
    expectCount(store, 5)
    expectHistoryActions(store, [])
    expect(store.getState()[HISTORY_KEY].tracking).toStrictEqual(false)
    expect(store.getState().canUndo).toStrictEqual(false)
    expect(store.getState().canRedo).toStrictEqual(false)

    store.dispatch({ type: 'counter/start', payload: 10 })
    expectCount(store, 10)
    expectHistoryActions(store, [])
    expect(store.getState()[HISTORY_KEY].tracking).toStrictEqual(true)
    expect(store.getState().canUndo).toStrictEqual(false)
    expect(store.getState().canRedo).toStrictEqual(false)

    store.dispatch({ type: 'counter/increment', payload: 5 })
    expectCount(store, 15)
    expectHistoryActions(store, [
      { action: { type: 'counter/increment', payload: 5 }, undone: false },
    ])
    expect(store.getState().canUndo).toStrictEqual(true)
    expect(store.getState().canRedo).toStrictEqual(false)

    store.dispatch({ type: 'counter/changeName', payload: 'New Counter Name' })
    expect(store.getState().present.name).toStrictEqual('New Counter Name')
    expectHistoryActions(store, [
      { action: { type: 'counter/increment', payload: 5 }, undone: false },
      {
        action: { type: 'counter/changeName', payload: 'New Counter Name' },
        undone: false,
      },
    ])

    store.dispatch({ type: ActionTypes.Undo })
    expectCount(store, 10)
    expect(store.getState().present.name).toStrictEqual('New Counter Name')
    expect(store.getState().canUndo).toStrictEqual(false)
    expect(store.getState().canRedo).toStrictEqual(true)
  })

  it.concurrent('should lose state changes if an action is not tracked', () => {
    const store = createStore(
      undoableActions(counterReducer, {
        trackedActions: ['counter/increment', 'counter/decrement'],
        undoableActions: ['counter/increment', 'counter/decrement'],
        trackAfterAction: 'counter/start',
      }),
    )

    store.dispatch({ type: 'counter/increment', payload: 5 })
    expectCount(store, 5)
    expectHistoryActions(store, [])
    expect(store.getState()[HISTORY_KEY].tracking).toStrictEqual(false)
    expect(store.getState().canUndo).toStrictEqual(false)
    expect(store.getState().canRedo).toStrictEqual(false)

    store.dispatch({ type: 'counter/start', payload: 10 })
    expectCount(store, 10)
    expectHistoryActions(store, [])
    expect(store.getState()[HISTORY_KEY].tracking).toStrictEqual(true)
    expect(store.getState().canUndo).toStrictEqual(false)
    expect(store.getState().canRedo).toStrictEqual(false)

    store.dispatch({ type: 'counter/increment', payload: 5 })
    expectCount(store, 15)
    expectHistoryActions(store, [
      { action: { type: 'counter/increment', payload: 5 }, undone: false },
    ])
    expect(store.getState().canUndo).toStrictEqual(true)
    expect(store.getState().canRedo).toStrictEqual(false)

    store.dispatch({ type: 'counter/changeName', payload: 'New Counter Name' })
    expect(store.getState().present.name).toStrictEqual('New Counter Name')
    expectHistoryActions(store, [
      { action: { type: 'counter/increment', payload: 5 }, undone: false },
    ])

    store.dispatch({ type: ActionTypes.Undo })
    expectCount(store, 10)
    // Since counter/changeName is not tracked, the change of 'New Counter Name' is ignored/lost
    expect(store.getState().present.name).toStrictEqual('Counter')
    expect(store.getState().canUndo).toStrictEqual(false)
    expect(store.getState().canRedo).toStrictEqual(true)
  })

  it.concurrent('should not clear future if an action is not undoable', () => {
    const store = createStore(
      undoableActions(counterReducer, {
        trackedActions: ['counter/increment', 'counter/changeName'],
        undoableActions: ['counter/increment'],
      }),
    )

    store.dispatch({ type: 'counter/increment' })
    store.dispatch({ type: 'counter/increment', payload: 2 })
    expectCount(store, 3)
    expectHistoryActions(store, [
      { action: { type: 'counter/increment' }, undone: false },
      { action: { type: 'counter/increment', payload: 2 }, undone: false },
    ])

    store.dispatch(ActionCreators.undo())
    expectCount(store, 1)
    expect(store.getState().canUndo).toStrictEqual(true)
    expect(store.getState().canRedo).toStrictEqual(true)
    expectHistoryActions(store, [
      { action: { type: 'counter/increment' }, undone: false },
      { action: { type: 'counter/increment', payload: 2 }, undone: true },
    ])

    store.dispatch({ type: 'counter/changeName', payload: 'The new name' })
    expect(store.getState().present.name).toStrictEqual('The new name')
    expectHistoryActions(store, [
      { action: { type: 'counter/increment' }, undone: false },
      { action: { type: 'counter/increment', payload: 2 }, undone: true },
      {
        action: { type: 'counter/changeName', payload: 'The new name' },
        undone: false,
      },
    ])
    expect(store.getState().canUndo).toStrictEqual(true)
    expect(store.getState().canRedo).toStrictEqual(true)
  })
})
