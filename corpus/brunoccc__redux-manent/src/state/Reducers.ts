import { Action, Dispatch, Reducer } from "redux";
import {
  ACTION_MIGRATE,
  ACTION_READY,
  ACTION_START,
  ReduxManentAction,
} from "./Actions";
import { Config, KeyValueStore } from "../config";
import { loadState, migrateState } from "../storage";
import { Log } from "../utils";

export type ReduxManentState = {
  loading: boolean;
  migrating: boolean;
  ready: boolean;
  version?: number;
};

const DEFAULT_STATE: ReduxManentState = {
  loading: false,
  migrating: false,
  ready: false,
  version: undefined,
};

export const reduxManentState: Reducer = (
  state,
  _action: Action
): ReduxManentState => {
  if (state === undefined) {
    // Just return the default initial state. Actions are managed internally
    return DEFAULT_STATE;
  }
  return state;
};

export const handleInternalActions = (
  dispatch: Dispatch,
  state: KeyValueStore,
  action: Action,
  config: Config
) => {
  if (
    action.type === ACTION_START ||
    action.type === ACTION_MIGRATE ||
    action.type === ACTION_READY
  ) {
    const manentAction = action as ReduxManentAction;
    switch (manentAction.type) {
      case ACTION_START: {
        loadState(dispatch, config);
        const reduxManentState: ReduxManentState = {
          loading: true,
          migrating: false,
          ready: false,
          version: undefined,
        };
        return {
          ...state,
          reduxManentState,
        };
      }
      case ACTION_MIGRATE: {
        migrateState(
          dispatch,
          config,
          manentAction.payload.loadedState,
          manentAction.payload.loadedVersion
        );
        const reduxManentState: ReduxManentState = {
          loading: false,
          migrating: true,
          ready: false,
          version: undefined,
        };
        return {
          ...state,
          reduxManentState,
        };
      }
      case ACTION_READY: {
        const reduxManentState: ReduxManentState = {
          loading: false,
          migrating: false,
          ready: true,
          version: manentAction.payload.loadedVersion,
        };
        return {
          ...state,
          ...manentAction.payload.state,
          reduxManentState,
        };
      }
      default:
        // This switch case must be exaustive
        const wtf: never = manentAction;
        Log.e?.("Unknown internal action detected", wtf);
    }
  }
  return state;
};
