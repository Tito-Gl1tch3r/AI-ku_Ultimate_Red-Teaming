import { Dispatch, Reducer, combineReducers } from "redux";
import { ReduxManentConfig, sanitizeConfig } from "./config";
import { Log } from "./utils";
import {
  ReduxManentState,
  handleInternalActions,
  reduxManentState,
  startAction,
} from "./state";
import { saveState } from "./storage";

let dispatch: Dispatch;

export const persistReducer = (userConfig: ReduxManentConfig): Reducer => {
  const config = sanitizeConfig(userConfig);

  // Inject internal state and default
  const combinedReducers = combineReducers({
    ...config.reducer,
    reduxManentState,
  });

  return (state, action) => {
    // Intercept internal actions
    state = handleInternalActions(dispatch, state, action, config);
    // Process normal actions and save when changes are detected
    const before = state;
    const after = combinedReducers(state, action);
    if ((after.reduxManentState as ReduxManentState).ready) {
      saveState(before, after, config);
    }
    return after;
  };
};

export const wakeUp = (_dispatch: Dispatch) => {
  Log.d?.("WakeUp");
  dispatch = _dispatch;
  dispatch(startAction());
};
