import type {
  PartialUndoableActionsConfig,
  Persistence,
  ResolvedPersistedUndoableActionsConfig,
  ResolvedUndoableActionsConfig,
} from './types'
import { ActionTypes } from './actions'

const initialUndoableActionsConfig: ResolvedUndoableActionsConfig = {
  immutableHistory: true,
  trackedActions: [],
  undoableActions: [],
  trackAfterAction: undefined,
  internalActions: {
    undo: ActionTypes.Undo,
    redo: ActionTypes.Redo,
    reset: ActionTypes.Reset,
    hydrate: ActionTypes.Hydrate,
    tracking: ActionTypes.Tracking,
  },
}

export function getConfig(
  customConfig?: PartialUndoableActionsConfig,
): ResolvedUndoableActionsConfig {
  return {
    ...initialUndoableActionsConfig,
    ...customConfig,
    immutableHistory:
      customConfig?.immutableHistory ??
      initialUndoableActionsConfig.immutableHistory,
    internalActions: {
      ...initialUndoableActionsConfig.internalActions,
      ...customConfig?.internalActions,
    },
  }
}

export function getConfigWithPersistence(
  customConfig: PartialUndoableActionsConfig & { persistence: Persistence },
): ResolvedPersistedUndoableActionsConfig {
  return {
    ...initialUndoableActionsConfig,
    ...customConfig,
    immutableHistory:
      customConfig.immutableHistory ??
      initialUndoableActionsConfig.immutableHistory,
    internalActions: {
      ...initialUndoableActionsConfig.internalActions,
      ...customConfig.internalActions,
    },
  }
}
