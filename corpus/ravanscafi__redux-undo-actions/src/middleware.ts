import { isAction, type Middleware, type UnknownAction } from 'redux'
import type { History, ResolvedPersistedUndoableActionsConfig } from './types'
import { isActionTracked } from './utils'
import { loadHistory, removeHistory, saveHistory } from './storage'
import { HISTORY_KEY } from './actions'

export default function createPersistenceMiddleware(
  config: ResolvedPersistedUndoableActionsConfig,
): Middleware {
  const { reducerKey, getStorageKey, storage, dispatchAfterMaybeLoading } =
    config.persistence
  const isTracked = (action: UnknownAction) => isActionTracked(config, action)
  let storageQueue: Promise<void> | undefined

  const schedule = (operation: () => Promise<void>) => {
    const result = storageQueue
      ? storageQueue.then(operation, operation)
      : operation()
    const settledResult = result.then(
      () => undefined,
      () => undefined,
    )
    storageQueue = settledResult
    void settledResult.then(() => {
      if (storageQueue === settledResult) {
        storageQueue = undefined
      }
    })
    return result
  }

  return (storeAPI) => (next) => async (action) => {
    if (!isAction(action)) {
      throw new Error(
        'Invalid action provided! Use custom middleware for async actions.',
      )
    }

    const previousState: unknown = storeAPI.getState()
    // after grabbing the previous state, we can call next
    const returnValue = next(action)

    if (action.type === config.internalActions.reset) {
      const storageKey = getStorageKey(() => previousState)
      await schedule(() => removeHistory(storage, storageKey))

      // no need to continue
      return returnValue
    }

    if (action.type === config.trackAfterAction) {
      const storageKey = getStorageKey(() => storeAPI.getState())
      await schedule(async () => {
        const history = await loadHistory(storage, storageKey)
        const isCurrent =
          getStorageKey(() => storeAPI.getState()) === storageKey
        if (!isCurrent) {
          return
        }

        if (history !== undefined) {
          storeAPI.dispatch({
            type: config.internalActions.hydrate,
            payload: history,
          })
        }

        if (dispatchAfterMaybeLoading) {
          // experimental timeout to allow visual changes to be applied after hydration
          setTimeout(() => {
            if (getStorageKey(() => storeAPI.getState()) === storageKey) {
              storeAPI.dispatch({ type: dispatchAfterMaybeLoading })
            }
          }, 100)
        }
      })

      // halt from saving for no reason
      return returnValue
    }

    if (!isTracked(action)) {
      return returnValue
    }

    const currentState: unknown = storeAPI.getState()

    const previousHistory = getHistoryState(previousState, reducerKey)
    const currentHistory = getHistoryState(currentState, reducerKey)

    if (
      currentHistory.tracking !== previousHistory.tracking ||
      (currentHistory.actions.length > 0 &&
        currentHistory.actions !== previousHistory.actions)
    ) {
      const storageKey = getStorageKey(() => currentState)
      const history = {
        actions: currentHistory.actions,
        tracking: currentHistory.tracking,
      }
      await schedule(() => saveHistory(storage, storageKey, history))
    }

    return returnValue
  }
}

function getHistoryState(
  obj: unknown,
  reducerKey: string | false,
): History<unknown, UnknownAction> {
  const error = new Error(
    'Unexpected state structure, make sure you provided the correct reducerKey: ' +
      (reducerKey || 'false'),
  )

  if (typeof obj !== 'object' || obj === null) {
    throw error
  }

  if (reducerKey === false && HISTORY_KEY in obj) {
    return obj[HISTORY_KEY] as History<unknown, UnknownAction>
  }

  if (reducerKey === false || !(reducerKey in obj)) {
    throw error
  }

  const reducerValue = (obj as Record<string, unknown>)[reducerKey]

  if (
    typeof reducerValue === 'object' &&
    reducerValue !== null &&
    HISTORY_KEY in reducerValue
  ) {
    return reducerValue[HISTORY_KEY] as History<unknown, UnknownAction>
  }

  throw error
}
