import { describe, expect, it, vi } from 'vitest'
import {
  applyMiddleware,
  combineReducers,
  legacy_createStore as createStore,
  type UnknownAction,
} from 'redux'
import {
  ActionCreators,
  type HistoryState,
  type PartialUndoableActionsConfig,
  persistedUndoableActions,
  type Persistence,
} from '../src'
import { HISTORY_KEY } from '../src/actions'

interface CounterState {
  id: string
  count: number
}
const initialState: CounterState = { id: 'counter-id', count: 0 }

describe.concurrent('persistedUndoableActions', () => {
  it.concurrent('should ignore untracked actions', async () => {
    const { store, mockStorage } = getStore()
    store.dispatch({ type: 'untracked' })
    expect(store.getState().counter.present).toEqual(initialState)
    expect(store.getState().counter[HISTORY_KEY]).toEqual({
      tracking: false,
      actions: [],
      snapshot: initialState,
    })

    // wait for "possible" save
    await sleep(50)

    expect(mockStorage.getItem).not.toHaveBeenCalled()
    expect(mockStorage.setItem).not.toHaveBeenCalled()
  })

  it.concurrent(
    'should ignore persistence if no storage key is returned',
    async () => {
      const { store, mockStorage } = getStore({
        persistence: { getStorageKey: () => false },
      })

      store.dispatch({ type: 'counter/start' })
      await sleep(50)
      store.dispatch({ type: 'counter/increment' })
      await sleep(50)
      store.dispatch({ type: 'counter/increment' })
      await sleep(50)

      expect(store.getState().counter[HISTORY_KEY]).toEqual({
        tracking: true,
        actions: [
          { action: { type: 'counter/increment' }, undone: false },
          { action: { type: 'counter/increment' }, undone: false },
        ],
        snapshot: { id: 'counter-id', count: 0 },
      })

      store.dispatch({ type: 'counter/reset' })
      await sleep(50)

      expect(store.getState().counter[HISTORY_KEY]).toEqual({
        tracking: true,
        actions: [],
        snapshot: { id: 'counter-id', count: 0 },
      })

      expect(mockStorage.getItem).not.toHaveBeenCalled()
      expect(mockStorage.setItem).not.toHaveBeenCalled()
      expect(mockStorage.removeItem).not.toHaveBeenCalled()
    },
  )

  it.concurrent('should load state when tracking starts', async () => {
    const { store, mockStorage } = getStore()
    mockStorage.getItem = vi.fn().mockResolvedValue(
      JSON.stringify({
        tracking: true,
        actions: [{ action: { type: 'counter/increment' }, undone: false }],
      }),
    )

    store.dispatch({ type: 'counter/start' })

    await vi.waitFor(() => {
      expect(store.getState().counter.present).toEqual({
        id: 'counter-id',
        count: 1,
      })
      expect(store.getState().counter[HISTORY_KEY]).toEqual({
        tracking: true,
        actions: [{ action: { type: 'counter/increment' }, undone: false }],
        snapshot: { id: 'counter-id', count: 0 },
      })
    })
  })

  it.concurrent('should save history when actions happen', async () => {
    const { store, mockStorage } = getStore()
    expect(store.getState().counter.present).toEqual({
      id: 'counter-id',
      count: 0,
    })

    // start tracking
    store.dispatch({ type: 'counter/start' })

    // wait for load
    await sleep(50) // not sure why vi.wait doesn't work for the last expectation unless we sleep here
    expect(mockStorage.getItem).toHaveBeenCalledExactlyOnceWith(
      'key-counter-id',
    )

    // start actions
    store.dispatch({ type: 'counter/increment' })
    expect(store.getState().counter.present).toEqual({
      id: 'counter-id',
      count: 1,
    })
    expect(store.getState().counter[HISTORY_KEY]).toEqual({
      tracking: true,
      actions: [{ action: { type: 'counter/increment' }, undone: false }],
      snapshot: { id: 'counter-id', count: 0 },
    })
    // wait for save
    expect(mockStorage.setItem).toHaveBeenCalledExactlyOnceWith(
      'key-counter-id',
      expect.any(String),
    )
  })

  it.concurrent('should reset state when reset action happens', async () => {
    const { store, mockStorage } = getStore({
      internalActions: {
        reset: 'counter/reset',
      },
    })

    // reset state before trackAfterAction happens
    store.dispatch({ type: 'counter/reset' })
    expect(store.getState().counter.present).toEqual({
      ...initialState,
    })
    expect(store.getState().counter[HISTORY_KEY]).toEqual({
      actions: [],
      tracking: false,
      snapshot: { ...initialState },
    })

    // prepare some state
    store.dispatch({ type: 'counter/start', payload: 100 }) //  should be the initial state
    await vi.waitFor(() => {
      expect(store.getState().counter[HISTORY_KEY]).toEqual({
        tracking: true,
        actions: [],
        snapshot: { ...initialState, count: 100 },
      })
    })
    store.dispatch({ type: 'counter/increment' })
    store.dispatch({ type: 'counter/increment' })
    expect(store.getState().counter.present.count).toEqual(102)
    await sleep(50)

    // reset state
    store.dispatch({ type: 'counter/reset' })
    await sleep(50)

    await vi.waitFor(() => {
      expect(mockStorage.removeItem).toHaveBeenNthCalledWith(
        2,
        'key-counter-id',
      )
      expect(store.getState().counter.present).toEqual({
        ...initialState,
        count: 100,
      })
      expect(store.getState().counter[HISTORY_KEY]).toEqual({
        actions: [],
        tracking: true,
        snapshot: { ...initialState, count: 100 },
      })
    })
  })

  it.concurrent('should handle saving storage errors gracefully', async () => {
    const { store, mockStorage } = getStore()
    const error = new Error('failed!')
    mockStorage.setItem = vi.fn().mockRejectedValue(error)

    // start tracking
    store.dispatch({ type: 'counter/start' })

    // wait for load
    await sleep(50)
    expect(mockStorage.getItem).toHaveBeenCalledExactlyOnceWith(
      'key-counter-id',
    )
    // start actions
    const spy = vi.spyOn(console, 'warn').mockImplementation(() => void 0)

    store.dispatch({ type: 'counter/increment' })
    expect(store.getState().counter.present).toEqual({
      id: 'counter-id',
      count: 1,
    })
    expect(store.getState().counter[HISTORY_KEY]).toEqual({
      tracking: true,
      actions: [{ action: { type: 'counter/increment' }, undone: false }],
      snapshot: initialState,
    })

    await vi.waitFor(() => {
      expect(mockStorage.setItem).toHaveBeenCalledExactlyOnceWith(
        'key-counter-id',
        expect.any(String),
      )
      expect(spy).toHaveBeenCalledExactlyOnceWith(
        'failed to save history to storage',
        error,
      )
    })
    spy.mockRestore()
  })

  it.concurrent('should handle loading storage errors gracefully', async () => {
    const { store, mockStorage } = getStore()
    const error = new Error('failed!')
    mockStorage.getItem = vi.fn().mockRejectedValue(error)

    const spy = vi.spyOn(console, 'warn').mockImplementation(() => void 0)
    // start tracking and trigger loading
    store.dispatch({ type: 'counter/start' })

    await vi.waitFor(() => {
      expect(mockStorage.getItem).toHaveBeenCalledExactlyOnceWith(
        'key-counter-id',
      )
      expect(spy).toHaveBeenCalledExactlyOnceWith(
        'failed to load history from storage',
        error,
      )
    })
    spy.mockRestore()
  })

  it.concurrent(
    'should handle errors when removing from the storage gracefully',
    async () => {
      const { store, mockStorage } = getStore()
      const error = new Error('failed!')
      mockStorage.removeItem = vi.fn().mockRejectedValue(error)

      const spy = vi.spyOn(console, 'warn').mockImplementation(() => void 0)

      // trigger removing
      store.dispatch({ type: 'counter/reset' })

      await vi.waitFor(() => {
        expect(mockStorage.removeItem).toHaveBeenCalledExactlyOnceWith(
          'key-counter-id',
        )
        expect(spy).toHaveBeenCalledExactlyOnceWith(
          'failed to remove history from storage',
          error,
        )
      })
      spy.mockRestore()
    },
  )

  it.concurrent('should reject dispatched non-actions', async () => {
    const { store } = getStore()
    // @ts-expect-error purposely invalid
    await expect(() => store.dispatch(() => undefined)).rejects.toThrow(
      'Invalid action provided! Use custom middleware for async actions.',
    )
  })

  it.concurrent('should ignore untracked actions', () => {
    const { store } = getStore({
      trackAfterAction: undefined,
      trackedActions: ['counter/increment'],
    })

    store.dispatch({ type: 'counter/decrement' })
    expect(store.getState().counter.present).toEqual({
      id: 'counter-id',
      count: -1,
    })
    expect(store.getState().counter[HISTORY_KEY]).toEqual({
      tracking: true,
      actions: [],
      snapshot: initialState,
    })

    store.dispatch({ type: 'counter/increment' })

    expect(store.getState().counter.present).toEqual(initialState)
    expect(store.getState().counter[HISTORY_KEY]).toEqual({
      tracking: true,
      actions: [{ action: { type: 'counter/increment' }, undone: false }],
      snapshot: initialState,
    })
  })

  it.concurrent(
    'should dispatch custom dispatchAfterMaybeLoading after hydration',
    async () => {
      const { store, mockStorage } = getStore({
        persistence: {
          dispatchAfterMaybeLoading: 'counter/loaded',
        },
      })
      const spy = vi.fn()
      store.subscribe(() => {
        if (store.getState().counter.present.count === 0) {
          spy()
        }
      })
      mockStorage.getItem = vi.fn().mockResolvedValue(
        JSON.stringify({
          tracking: true,
          actions: [],
          snapshot: initialState,
        }),
      )
      store.dispatch({ type: 'counter/start' })
      await sleep(50)
      expect(spy).toHaveBeenCalled()
    },
  )

  it.concurrent('hydrates state with actions', async () => {
    const { store, mockStorage } = getStore()
    const exportedHistory = {
      tracking: false,
      actions: [
        { action: { type: 'counter/increment' }, undone: false },
        { action: { type: 'counter/increment' }, undone: false },
        { action: { type: 'counter/increment', payload: 10 }, undone: true },
      ],
    }
    mockStorage.getItem = vi
      .fn()
      .mockResolvedValue(JSON.stringify(exportedHistory))

    store.dispatch({ type: 'counter/start', payload: 0 })

    await vi.waitFor(() => {
      expect(store.getState().counter.present.count).toStrictEqual(2)
      expect(store.getState().counter[HISTORY_KEY].tracking).toStrictEqual(
        false,
      )
      expect(store.getState().counter[HISTORY_KEY].actions).toStrictEqual(
        exportedHistory.actions,
      )
      const actions = store.getState().counter[HISTORY_KEY].actions
      expect(Object.isFrozen(actions)).toBe(true)
      expect(actions.every((entry) => Object.isFrozen(entry))).toBe(true)
      expect(actions.every((entry) => Object.isFrozen(entry.action))).toBe(true)
      expect(store.getState().counter.canUndo).toStrictEqual(true)
      expect(store.getState().counter.canRedo).toStrictEqual(true)
    })

    // start tracking again
    store.dispatch(ActionCreators.tracking(true))

    store.dispatch(ActionCreators.redo())
    expect(store.getState().counter.present.count).toStrictEqual(12)
    expect(store.getState().counter.canUndo).toStrictEqual(true)
    expect(store.getState().counter.canRedo).toStrictEqual(false)

    store.dispatch(ActionCreators.undo())
    expect(store.getState().counter.present.count).toStrictEqual(2)
    expect(store.getState().counter.canUndo).toStrictEqual(true)
    expect(store.getState().counter.canRedo).toStrictEqual(true)

    store.dispatch(ActionCreators.undo())
    expect(store.getState().counter.present.count).toStrictEqual(1)
    expect(store.getState().counter.canUndo).toStrictEqual(true)
    expect(store.getState().counter.canRedo).toStrictEqual(true)
    store.dispatch(ActionCreators.undo())

    expect(store.getState().counter.present.count).toStrictEqual(0)
    expect(store.getState().counter.canUndo).toStrictEqual(false)
    expect(store.getState().counter.canRedo).toStrictEqual(true)
  })
})

describe('persistence serialization', () => {
  it('persists undo dispatched while a preceding write is pending', async () => {
    const { store, mockStorage } = getStore({
      trackedActions: [
        'counter/increment',
        'counter/decrement',
        'counter/undo',
      ],
      internalActions: { undo: 'counter/undo' },
    })
    await Promise.resolve(store.dispatch({ type: 'counter/start' }))

    let releaseWrite!: () => void
    const writeBlocked = new Promise<void>((resolve) => {
      releaseWrite = resolve
    })
    let markWriteStarted!: () => void
    const writeStarted = new Promise<void>((resolve) => {
      markWriteStarted = resolve
    })
    const values: string[] = []
    let writeCount = 0
    mockStorage.setItem.mockImplementation(
      async (_key: string, value: string) => {
        writeCount += 1
        if (writeCount === 1) {
          markWriteStarted()
          await writeBlocked
        }
        values.push(value)
      },
    )

    const increment = store.dispatch({ type: 'counter/increment' })
    await writeStarted
    const undo = store.dispatch({ type: 'counter/undo' })
    releaseWrite()
    await Promise.all([Promise.resolve(increment), Promise.resolve(undo)])

    const lastPersistedValue = values.at(-1)
    expect(lastPersistedValue).toBeDefined()
    if (lastPersistedValue === undefined) {
      throw new Error('Expected history to be persisted')
    }
    const persisted = JSON.parse(lastPersistedValue) as { actions: unknown[] }
    expect(persisted.actions).toEqual([
      { action: { type: 'counter/increment' }, undone: true },
    ])
  })

  it('loads a new storage key while a preceding write is pending', async () => {
    const { store, mockStorage } = getStore()
    await Promise.resolve(
      store.dispatch({
        type: 'counter/start',
        payload: { id: 'first', count: 0 },
      }),
    )

    let releaseWrite!: () => void
    const writeBlocked = new Promise<void>((resolve) => {
      releaseWrite = resolve
    })
    let markWriteStarted!: () => void
    const writeStarted = new Promise<void>((resolve) => {
      markWriteStarted = resolve
    })
    mockStorage.setItem.mockImplementation(async () => {
      markWriteStarted()
      await writeBlocked
    })
    mockStorage.getItem.mockImplementation((key: string) => {
      if (key !== 'key-second') {
        return Promise.resolve(null)
      }
      return Promise.resolve(
        JSON.stringify({
          tracking: true,
          actions: [{ action: { type: 'counter/decrement' }, undone: false }],
        }),
      )
    })

    const increment = store.dispatch({ type: 'counter/increment' })
    await writeStarted
    const nextSession = store.dispatch({
      type: 'counter/start',
      payload: { id: 'second', count: 0 },
    })
    releaseWrite()
    await Promise.all([
      Promise.resolve(increment),
      Promise.resolve(nextSession),
    ])

    expect(mockStorage.getItem).toHaveBeenCalledWith('key-second')
    expect(store.getState().counter.present).toEqual({
      id: 'second',
      count: -1,
    })
  })

  it('removes history when reset follows a pending write', async () => {
    const { store, mockStorage } = getStore({
      internalActions: { reset: 'counter/reset' },
    })
    await Promise.resolve(store.dispatch({ type: 'counter/start' }))

    let releaseWrite!: () => void
    const writeBlocked = new Promise<void>((resolve) => {
      releaseWrite = resolve
    })
    let markWriteStarted!: () => void
    const writeStarted = new Promise<void>((resolve) => {
      markWriteStarted = resolve
    })
    mockStorage.setItem.mockImplementation(async () => {
      markWriteStarted()
      await writeBlocked
    })

    const increment = store.dispatch({ type: 'counter/increment' })
    await writeStarted
    const reset = store.dispatch({ type: 'counter/reset' })
    releaseWrite()
    await Promise.all([Promise.resolve(increment), Promise.resolve(reset)])

    expect(mockStorage.removeItem).toHaveBeenCalledExactlyOnceWith(
      'key-counter-id',
    )
  })

  it('does not hydrate history after its storage key becomes stale', async () => {
    const { store, mockStorage } = getStore()
    let releaseFirstLoad!: () => void
    const firstLoadBlocked = new Promise<void>((resolve) => {
      releaseFirstLoad = resolve
    })
    let markFirstLoadStarted!: () => void
    const firstLoadStarted = new Promise<void>((resolve) => {
      markFirstLoadStarted = resolve
    })
    mockStorage.getItem.mockImplementation(async (key: string) => {
      if (key === 'key-first') {
        markFirstLoadStarted()
        await firstLoadBlocked
        return JSON.stringify({
          tracking: true,
          actions: [
            {
              action: { type: 'counter/increment', payload: 10 },
              undone: false,
            },
          ],
        })
      }
      if (key === 'key-second') {
        return JSON.stringify({
          tracking: true,
          actions: [{ action: { type: 'counter/decrement' }, undone: false }],
        })
      }
      return null
    })

    const firstSession = store.dispatch({
      type: 'counter/start',
      payload: { id: 'first', count: 0 },
    })
    await firstLoadStarted
    const secondSession = store.dispatch({
      type: 'counter/start',
      payload: { id: 'second', count: 0 },
    })
    releaseFirstLoad()
    await Promise.all([
      Promise.resolve(firstSession),
      Promise.resolve(secondSession),
    ])

    expect(store.getState().counter.present).toEqual({
      id: 'second',
      count: -1,
    })
  })
})

describe.concurrent('configuration validation', () => {
  it.concurrent('should identify a non-existing reducer key', async () => {
    const { store } = getStore({
      trackAfterAction: undefined,
      persistence: { reducerKey: 'wrongKey' },
    })
    await expect(() =>
      store.dispatch({ type: 'counter/decrement' }),
    ).rejects.toThrow(
      'Unexpected state structure, make sure you provided the correct reducerKey: wrongKey',
    )
  })

  it.concurrent(
    'should identify a reducer key that is not the correct reducer',
    async () => {
      const { persistedReducer } = getReducer({
        persistence: {
          reducerKey: 'another',
          getStorageKey: (getState: () => unknown) => {
            const state = getState() as HistoryState<
              CounterState,
              UnknownAction
            >

            return `key-${state.present.id}`
          },
        },
      })
      const store = createStore(
        combineReducers({
          counter: persistedReducer.reducer,
          another: () => ({ some: 'state' }),
        }),
        applyMiddleware(persistedReducer.middleware),
      )
      await expect(() =>
        store.dispatch({ type: 'counter/decrement' }),
      ).rejects.toThrow(
        'Unexpected state structure, make sure you provided the correct reducerKey: another',
      )
    },
  )

  it.concurrent('should handle null state', async () => {
    const { persistedReducer } = getReducer({
      persistence: {
        reducerKey: 'another',
        getStorageKey: (getState: () => unknown) => {
          const state = getState() as HistoryState<CounterState, UnknownAction>

          return `key-${state.present.id}`
        },
      },
    })
    const store = createStore(
      () => null,
      applyMiddleware(persistedReducer.middleware),
    )
    await expect(() =>
      store.dispatch({ type: 'counter/decrement' }),
    ).rejects.toThrow(
      'Unexpected state structure, make sure you provided the correct reducerKey: another',
    )
  })
})

describe.concurrent('persistedUndoableActions with root reducer', () => {
  it.concurrent('should work with the root reducer', async () => {
    const { mockStorage, persistedReducer } = getReducer({
      persistence: {
        reducerKey: false,
        getStorageKey: (getState: () => unknown) => {
          const state = getState() as HistoryState<CounterState, UnknownAction>

          return `key-${state.present.id}`
        },
      },
    })
    const store = createStore(
      persistedReducer.reducer,
      applyMiddleware(persistedReducer.middleware),
    )

    store.dispatch({ type: 'counter/start' })
    await vi.waitFor(() => {
      expect(mockStorage.getItem).toHaveBeenCalledExactlyOnceWith(
        'key-counter-id',
      )
    })

    await sleep(100)

    store.dispatch({ type: 'counter/increment' })
    await vi.waitFor(() => {
      expect(mockStorage.setItem).toHaveBeenCalledExactlyOnceWith(
        'key-counter-id',
        expect.any(String),
      )
    })

    store.dispatch({ type: 'counter/increment' })
    await vi.waitFor(() => {
      expect(mockStorage.setItem).toHaveBeenCalledExactlyOnceWith(
        'key-counter-id',
        expect.any(String),
      )
    })

    expect(store.getState().present.count).toEqual(2)
    expect(store.getState()[HISTORY_KEY]).toEqual({
      tracking: true,
      actions: [
        { action: { type: 'counter/increment' }, undone: false },
        { action: { type: 'counter/increment' }, undone: false },
      ],
      snapshot: { id: 'counter-id', count: 0 },
    })

    store.dispatch(ActionCreators.undo())

    expect(store.getState().present.count).toEqual(1)
    expect(store.getState()[HISTORY_KEY]).toEqual({
      tracking: true,
      actions: [
        { action: { type: 'counter/increment' }, undone: false },
        { action: { type: 'counter/increment' }, undone: true },
      ],
      snapshot: { id: 'counter-id', count: 0 },
    })
  })
})

function getReducer(
  config?: PartialUndoableActionsConfig & {
    persistence?: Partial<Persistence>
  },
) {
  const counterReducer = (
    state: CounterState = initialState,
    action: UnknownAction,
  ): CounterState => {
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
        if (typeof action.payload === 'object' && action.payload !== null) {
          const payload = action.payload as Partial<CounterState>
          return { ...state, ...payload }
        }
        return { ...state, count: (action.payload as number) || 0 }
      default:
        return state
    }
  }

  const mockStorage = {
    getItem: vi.fn().mockResolvedValue(null),
    setItem: vi.fn().mockResolvedValue(undefined),
    removeItem: vi.fn().mockResolvedValue(undefined),
  }

  const persistedReducer = persistedUndoableActions(counterReducer, {
    trackedActions: ['counter/increment', 'counter/decrement'],
    trackAfterAction: 'counter/start',
    ...config,
    internalActions: {
      ...config?.internalActions,
      reset: 'counter/reset',
    },
    persistence: {
      reducerKey: 'counter',
      getStorageKey: (getState: () => unknown) => {
        const { counter } = getState() as {
          counter: HistoryState<CounterState, UnknownAction>
        }

        return `key-${counter.present.id}`
      },
      storage: mockStorage,
      dispatchAfterMaybeLoading: 'counter/loaded',
      ...config?.persistence,
    },
  })
  return { mockStorage, persistedReducer }
}

function getStore(
  config?: PartialUndoableActionsConfig & {
    persistence?: Partial<Persistence>
  },
) {
  const { mockStorage, persistedReducer } = getReducer(config)

  const store = createStore(
    combineReducers({ counter: persistedReducer.reducer }),
    applyMiddleware(persistedReducer.middleware),
  )

  return { store, mockStorage }
}

function sleep(delay: number) {
  return new Promise((resolve) => {
    setTimeout(resolve, delay)
  })
}
