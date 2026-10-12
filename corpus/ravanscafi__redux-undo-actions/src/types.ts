import type { UnknownAction } from 'redux'
import { HISTORY_KEY } from './actions'

/**
 * Represents an action in the history stack.
 * @template Action - The Redux action.
 */
export interface HistoryAction<Action extends UnknownAction> {
  /**
   * The Redux action that was dispatched.
   */
  readonly action: Action
  /**
   * Indicates whether this action was undone during history tracking.
   */
  readonly undone: boolean
}

/**
 * Internal structure for the history tracking.
 * @template State - The shape of the provided reducer.
 * @template Action - The Redux action.
 */
export interface History<State, Action extends UnknownAction> {
  /**
   * Whether history tracking is enabled.
   */
  tracking: boolean
  /**
   * List of actions in the history stack.
   */
  actions: readonly HistoryAction<Action>[]
  /**
   * The initial state snapshot from when tracking started.
   */
  snapshot: State
}

/**
 * The wrapped state shape.
 * @template State - The shape of the provided reducer.
 * @template Action - The Redux action.
 */
export interface HistoryState<State, Action extends UnknownAction> {
  /**
   * The current state of the application.
   * This is the state as provided by the reducer, not the history snapshot.
   * It represents the latest state after all actions have been applied.
   */
  present: State
  /**
   * Indicates whether undo is possible.
   * This is automatically updated by the library based on the history stack.
   */
  canUndo: boolean
  /**
   * Indicates whether redo is possible.
   * This is automatically updated by the library based on the history stack.
   */
  canRedo: boolean
  /**
   * Internal history tracking data.
   * This should not be modified directly, otherwise it can lead to inconsistent states.
   * The key is intentionally not exposed and might change in the future.
   */
  [HISTORY_KEY]: History<State, Action>
}

/**
 * Exported history data for serialization or inspection.
 * @template State - The shape of the provided reducer.
 * @template Action - The Redux action.
 * @property actions - List of actions in the history stack.
 * @property tracking - Whether history tracking is enabled.
 */
export type ExportedHistory<State, Action extends UnknownAction> = Pick<
  History<State, Action>,
  'actions' | 'tracking'
>

/**
 * Persistence configuration for storing history state.
 */
export interface Persistence {
  /**
   * The key under which the history reducer is stored in the Redux state tree.
   * This should match the key used when creating the reducer.
   * If using it directly in the root reducer, the reducer key should be false.
   */
  reducerKey: string | false
  /**
   * Function to generate a unique storage key for persisting history state.
   *
   * Receives the current Redux state and returns either:
   * - a `string` key to use for storage, or
   * - `false` to disable persistence for this state.
   *
   * This enables conditional persistence, such as saving history only for specific entities.
   *
   * @param getState - A function that returns the current Redux state.
   * @returns A unique string key for storage, or `false` to skip persistence.
   *
   * @example
   * // Persist history only for entities with an ID
   * getStorageKey: (getState) => {
   *   const state = getState() as { entityId?: string }
   *   return state.entityId ? `history_${state.entityId}` : false
   * }
   */
  getStorageKey: (getState: () => unknown) => string | false
  /**
   * Custom storage implementation for persisting history state.
   */
  storage: StoragePersistor
  /**
   * Optional Redux action type to dispatch after the stored history finishes loading.
   * This can be used to trigger state changes (e.g. `loadingStatus = 'done'` or other side effects once the history
   * is ready.
   * If not provided, no action will be dispatched after loading.
   *
   * To prevent UI issues, it's dispatched after `100ms` to ensure the state is fully loaded.
   */
  dispatchAfterMaybeLoading?: UnknownAction['type']
}

/**
 * Interface for custom storage implementations used for persisting history state.
 * Implement this to provide async storage (e.g., localStorage, AsyncStorage, IndexedDB, custom backend).
 *
 * All methods must be Promise-based and handle string values.
 * It is highly recommended to compress/decompress the data before storing it, especially for larger states.
 * This can be done using libraries like `lz-string` and the methods compressToUTF16/decompressFromUTF16.
 *
 * @example
 * const myPersistor: StoragePersistor = {
 *   async getItem(key) { return decompressFromUTF16(localStorage.getItem(key)) },
 *   async setItem(key, value) { localStorage.setItem(key, compressToUTF16(value)) },
 *   async removeItem(key) { localStorage.removeItem(key) }
 * }
 */
export interface StoragePersistor {
  /**
   * Retrieves a string value for the given key from storage.
   * Returns null if the key does not exist.
   */
  getItem(key: string): Promise<string | null>
  /**
   * Stores a string value under the given key in storage.
   */
  setItem(key: string, value: string): Promise<void>
  /**
   * Removes the value for the given key from storage.
   */
  removeItem(key: string): Promise<void>
}

/**
 * Configuration for customizing which actions are tracked and undoable.
 *
 * @example
 * const config: UndoableActionsConfig = {
 *   trackedActions: ['canvas/draw', 'canvas/zoomIn', 'canvas/zoomOut'],
 *   undoableActions: ['canvas/draw'],
 *   trackAfterAction: 'canvas/start',
 *   internalActions: {
 *     undo: 'canvas/undo',
 *     redo: 'canvas/redo',
 *     reset: 'canvas/reset',
 *     tracking: 'canvas/tracking',
 *   }
 * }
 */
export interface UndoableActionsConfig {
  /**
   * Copy and freeze tracked actions before storing them.
   * Set this to false if an action contains non-plain values.
   * @default true
   */
  immutableHistory?: boolean
  /**
   * Specifies which Redux action types should be tracked in the history.
   * If omitted, all actions will be tracked, which may include actions from other reducers.
   * For best results, provide only the relevant action types.
   *
   * @example ['canvas/draw', 'canvas/zoomIn', 'canvas/zoomOut']
   * @default []
   */
  trackedActions: UnknownAction['type'][]
  /**
   * Defines which tracked actions can be undone or redone.
   * If omitted, all tracked actions are considered undoable.
   *
   * @example ['canvas/draw']
   * @default []
   */
  undoableActions: UnknownAction['type'][]
  /**
   * Action type that triggers the start of history tracking.
   * Useful if your actual initial state loads asynchronously.
   * If omitted, tracking begins when the store is created.
   *
   * @example 'canvas/start'
   * @default undefined
   */
  trackAfterAction?: UnknownAction['type']
  /**
   * Customizable internal action types for undo, redo, reset, and tracking operations.
   * Useful if you use the reducer multiple times in your store and need to differentiate actions.
   * These actions are handled internally and are not dispatched to the store.
   */
  internalActions: {
    /**
     * Action type for the undo operation.
     * Dispatching this action undoes the most recent undoable action, if available.
     * @default {@link ActionTypes.Undo}
     */
    undo: UnknownAction['type']
    /**
     * Action type for the redo operation.
     * Dispatching this action redoes the most recently undone action, if available.
     * @default {@link ActionTypes.Redo}
     */
    redo: UnknownAction['type']
    /**
     * Action type for the reset operation.
     * Dispatching this action resets the history to its initial state,
     * cleaning the tracked actions.
     * If `trackAfterAction` is set and the specified action has occurred,
     * the reset will restore the state to immediately after that action.
     * @default {@link ActionTypes.Reset}
     */
    reset: UnknownAction['type']
    /**
     * Action type for the hydrate operation.
     * Dispatching this action will apply the actions on the state.
     * @default {@link ActionTypes.Hydrate}
     */
    hydrate: UnknownAction['type']
    /**
     * Action type for the tracking operation.
     * Dispatching this action toggles the tracking state.
     * @default {@link ActionTypes.Tracking}
     */
    tracking: UnknownAction['type']
  }
}

/**
 * Configuration for undoable actions with persistence.
 * This extends the basic `UndoableActionsConfig` with persistence settings.
 */
export type PersistedUndoableActionsConfig = UndoableActionsConfig & {
  persistence: Persistence
}

export type ResolvedUndoableActionsConfig = Omit<
  UndoableActionsConfig,
  'immutableHistory'
> & {
  immutableHistory: boolean
}

export type ResolvedPersistedUndoableActionsConfig =
  ResolvedUndoableActionsConfig & {
    persistence: Persistence
  }

/**
 * Partial configuration for undoable actions.
 * The provided properties will override the defaults.
 */
export type PartialUndoableActionsConfig = DeepPartial<UndoableActionsConfig>

type DeepPartial<T> = T extends object
  ? T extends unknown[]
    ? T
    : { [K in keyof T]?: DeepPartial<T[K]> }
  : T
