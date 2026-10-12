import type { Reducer, UnknownAction } from 'redux'
import type {
  ExportedHistory,
  History,
  HistoryAction,
  HistoryState,
  ResolvedUndoableActionsConfig,
} from './types'
import { canRedo, canUndo, isActionTracked, isActionUndoable } from './utils'
import { HISTORY_KEY } from './actions'
import {
  captureHistoryAction,
  captureHistoryActions,
  freezeHistoryActions,
  isCapturedHistoryActions,
  setHistoryActionUndone,
} from './immutable'

export default function createReducer<State, Action extends UnknownAction>(
  reducer: Reducer<State, Action>,
  config: ResolvedUndoableActionsConfig,
): Reducer<HistoryState<State, Action>, Action> {
  const initialState = getInitialState(reducer, config)

  return function (
    state: HistoryState<State, Action> | undefined,
    action: Action,
  ) {
    if (!state) {
      return initialState
    }

    const normalizedState = normalizeHistoryState(state, config)

    switch (action.type) {
      case config.internalActions.undo:
        return undo(reducer, config, normalizedState)
      case config.internalActions.redo:
        return redo(reducer, config, normalizedState)
      case config.internalActions.reset:
        return reset(config, normalizedState, initialState)
      case config.internalActions.hydrate:
        return hydrate(reducer, config, normalizedState, action, initialState)
      case config.internalActions.tracking:
        return setTracking(normalizedState, action)
      case config.trackAfterAction:
        return trackAfter(
          reducer,
          config,
          normalizedState,
          action,
          initialState,
        )
      default:
        return handleAction(reducer, config, normalizedState, action)
    }
  }
}

function normalizeHistoryState<State, Action extends UnknownAction>(
  state: HistoryState<State, Action>,
  config: ResolvedUndoableActionsConfig,
): HistoryState<State, Action> {
  const history = state[HISTORY_KEY]
  if (!config.immutableHistory || isCapturedHistoryActions(history.actions)) {
    return state
  }

  return {
    ...state,
    [HISTORY_KEY]: {
      ...history,
      actions: captureHistoryActions(history.actions, true),
    },
  }
}

function getInitialState<State, Action extends UnknownAction>(
  reducer: Reducer<State, Action>,
  config: ResolvedUndoableActionsConfig,
): HistoryState<State, Action> {
  const initialPresent = reducer(undefined, {} as Action)

  return {
    present: initialPresent,
    [HISTORY_KEY]: {
      tracking: config.trackAfterAction === undefined,
      actions: freezeHistoryActions([], config.immutableHistory),
      snapshot: initialPresent,
    },
    canUndo: false,
    canRedo: false,
  }
}

function undo<State, Action extends UnknownAction>(
  reducer: Reducer<State, Action>,
  config: ResolvedUndoableActionsConfig,
  state: HistoryState<State, Action>,
): HistoryState<State, Action> {
  const history = state[HISTORY_KEY]
  const { actions } = history

  if (!canUndo(config, actions)) {
    return state
  }

  const lastUndoableIndex = actions.findLastIndex(
    (a) => !a.undone && isActionUndoable(config, a.action),
  )

  const newActions = freezeHistoryActions(
    actions.toSpliced(
      lastUndoableIndex,
      1,
      setHistoryActionUndone(
        actions[lastUndoableIndex],
        true,
        config.immutableHistory,
      ),
    ),
    config.immutableHistory,
  )

  const present = replay(reducer, newActions, history.snapshot)

  return {
    [HISTORY_KEY]: {
      ...history,
      actions: newActions,
    },
    present,
    canUndo: canUndo(config, newActions),
    canRedo: canRedo(config, newActions),
  }
}

function redo<State, Action extends UnknownAction>(
  reducer: Reducer<State, Action>,
  config: ResolvedUndoableActionsConfig,
  state: HistoryState<State, Action>,
): HistoryState<State, Action> {
  const { present } = state
  const history = state[HISTORY_KEY]
  const { actions } = history

  if (!canRedo(config, actions)) {
    return state
  }

  const firstUndoableIndex = actions.findIndex(
    (a) => a.undone && isActionUndoable(config, a.action),
  )

  const newActions = freezeHistoryActions(
    actions.toSpliced(
      firstUndoableIndex,
      1,
      setHistoryActionUndone(
        actions[firstUndoableIndex],
        false,
        config.immutableHistory,
      ),
    ),
    config.immutableHistory,
  )

  let newPresent: State

  if (firstUndoableIndex === actions.length - 1) {
    newPresent = reducer(present, newActions[firstUndoableIndex].action)
  } else {
    newPresent = replay(reducer, newActions, history.snapshot)
  }

  return {
    [HISTORY_KEY]: { ...history, actions: newActions },
    present: newPresent,
    canUndo: canUndo(config, newActions),
    canRedo: canRedo(config, newActions),
  }
}

function reset<State, Action extends UnknownAction>(
  config: ResolvedUndoableActionsConfig,
  state: HistoryState<State, Action>,
  initialState: HistoryState<State, Action>,
): HistoryState<State, Action> {
  if (config.trackAfterAction === undefined) {
    return initialState
  }

  return {
    ...initialState,
    [HISTORY_KEY]: {
      ...initialState[HISTORY_KEY],
      tracking: state[HISTORY_KEY].tracking,
      snapshot: state[HISTORY_KEY].snapshot,
    },
    present: state[HISTORY_KEY].snapshot,
  }
}

function trackAfter<State, Action extends UnknownAction>(
  reducer: Reducer<State, Action>,
  config: ResolvedUndoableActionsConfig,
  state: HistoryState<State, Action>,
  action: Action,
  initialState: HistoryState<State, Action>,
): HistoryState<State, Action> {
  const newState = handleAction(reducer, config, state, action)

  return {
    ...initialState,
    [HISTORY_KEY]: {
      ...initialState[HISTORY_KEY],
      tracking: true,
      snapshot: newState.present,
    },
    present: newState.present,
  }
}

function handleAction<State, Action extends UnknownAction>(
  reducer: Reducer<State, Action>,
  config: ResolvedUndoableActionsConfig,
  state: HistoryState<State, Action>,
  action: Action,
): HistoryState<State, Action> {
  const { present } = state
  const history = state[HISTORY_KEY]
  const { actions, tracking } = history

  const newPresent = reducer(present, action)

  if (
    !tracking ||
    !isActionTracked(config, action) ||
    Object.is(newPresent, present)
  ) {
    return {
      ...state,
      present: newPresent,
    }
  }

  const retainedActions = isActionUndoable(config, action)
    ? actions.filter((historyAction) => !historyAction.undone)
    : actions
  const newActions = freezeHistoryActions(
    [
      ...retainedActions,
      captureHistoryAction(action, false, config.immutableHistory),
    ],
    config.immutableHistory,
  )

  return {
    [HISTORY_KEY]: {
      ...history,
      actions: newActions,
    },
    present: newPresent,
    canUndo: canUndo(config, newActions),
    canRedo: canRedo(config, newActions),
  }
}

function hydrate<State, Action extends UnknownAction>(
  reducer: Reducer<State, Action>,
  config: ResolvedUndoableActionsConfig,
  state: HistoryState<State, Action>,
  action: Action,
  initialState: HistoryState<State, Action>,
): HistoryState<State, Action> {
  const { payload } = action
  const { actions = [], tracking = true } = payload as ExportedHistory<
    State,
    Action
  >
  const capturedActions = captureHistoryActions(
    actions,
    config.immutableHistory,
  )

  const newPresent = replay(reducer, capturedActions, state.present)

  return {
    ...initialState,
    [HISTORY_KEY]: {
      ...initialState[HISTORY_KEY],
      tracking,
      actions: capturedActions,
      snapshot: state.present,
    },
    present: newPresent,
    canUndo: canUndo(config, capturedActions),
    canRedo: canRedo(config, capturedActions),
  }
}

function setTracking<State, Action extends UnknownAction>(
  state: HistoryState<State, Action>,
  action: Action,
): HistoryState<State, Action> {
  const { payload } = action
  const tracking = payload as History<State, Action>['tracking']

  return {
    ...state,
    [HISTORY_KEY]: {
      ...state[HISTORY_KEY],
      tracking,
    },
  }
}

function replay<State, Action extends UnknownAction>(
  reducer: Reducer<State, Action>,
  newActions: readonly HistoryAction<Action>[],
  initialState: State,
): State {
  return newActions
    .filter((a) => !a.undone)
    .reduce((accState, a) => reducer(accState, a.action), initialState)
}
