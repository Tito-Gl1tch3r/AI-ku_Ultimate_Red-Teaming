import type { UnknownAction } from 'redux'
import type { ExportedHistory } from './types'

/**
 * The key used to identify the internal actions state.
 */
export const HISTORY_KEY = '@@redux-undo-actions'

/**
 * Action type constants for undo, redo, reset, and tracking actions.
 */
export const ActionTypes = {
  Undo: `${HISTORY_KEY}/undo`,
  Redo: `${HISTORY_KEY}/redo`,
  Reset: `${HISTORY_KEY}/reset`,
  Hydrate: `${HISTORY_KEY}/hydrate`,
  Tracking: `${HISTORY_KEY}/tracking`,
}

/**
 * Action creator utilities for undo, redo, reset, and tracking actions.
 * These utilities only work if the internal actions are not overridden in the configuration.
 */
export const ActionCreators = {
  /**
   * Creates an undo action.
   * @returns An action to trigger undo.
   */
  undo: (): UnknownAction => ({ type: ActionTypes.Undo }),
  /**
   * Creates a redo action.
   * @returns An action to trigger redo.
   */
  redo: (): UnknownAction => ({ type: ActionTypes.Redo }),
  /**
   * Creates a reset action.
   * @returns An action to reset history.
   */
  reset: (): UnknownAction => ({ type: ActionTypes.Reset }),
  /**
   * Creates an action to hydrate the history.
   * @param payload
   */
  hydrate: <State, Action extends UnknownAction>(
    payload: ExportedHistory<State, Action>,
  ): UnknownAction => ({ type: ActionTypes.Hydrate, payload }),
  /**
   * Creates an action to enable or disable the tracking of actions in history.
   *
   * @param payload - If true, enables tracking; if false, disables tracking.
   * @returns An action to update the tracking state in the undo/redo history.
   */
  tracking: (payload: boolean): UnknownAction => ({
    type: ActionTypes.Tracking,
    payload,
  }),
}
