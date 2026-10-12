import type { Middleware, Reducer, UnknownAction } from 'redux'
import type {
  HistoryState,
  PartialUndoableActionsConfig,
  Persistence,
} from './types'
import createReducer from './reducer'
import createPersistenceMiddleware from './middleware'
import { getConfig, getConfigWithPersistence } from './config'

/**
 * Enhances a reducer to support undo/redo actions.
 *
 * @template State - The shape of the reducer state.
 * @template Action - The Redux action.
 *
 * @param reducer - The base reducer to wrap with undo/redo functionality.
 * @param customConfig - Optional configuration.
 * @returns A reducer managing history state for undo/redo.
 */
export function undoableActions<State, Action extends UnknownAction>(
  reducer: Reducer<State, Action>,
  customConfig?: PartialUndoableActionsConfig,
): Reducer<HistoryState<State, Action>, Action> {
  const config = getConfig(customConfig)
  return createReducer(reducer, config)
}

/**
 * Enhances a reducer with undo/redo actions and a persistence middleware.
 *
 * @template State - The shape of the reducer state.
 * @template Action - The Redux action.
 *
 * @param reducer - The base reducer to wrap with undo/redo functionality.
 * @param customConfig - Configuration for undoable actions and persistence.
 * @returns An object containing the reducer and a persistence middleware that should be added to the store.
 */
export function persistedUndoableActions<State, Action extends UnknownAction>(
  reducer: Reducer<State, Action>,
  customConfig: PartialUndoableActionsConfig & { persistence: Persistence },
): {
  reducer: Reducer<HistoryState<State, Action>, Action>
  middleware: Middleware
} {
  const config = getConfigWithPersistence(customConfig)
  const wrappedReducer = createReducer(reducer, config)
  const middleware = createPersistenceMiddleware(config)

  return { reducer: wrappedReducer, middleware }
}
