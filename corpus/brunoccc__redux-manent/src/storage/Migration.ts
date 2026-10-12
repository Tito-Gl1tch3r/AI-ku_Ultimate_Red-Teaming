import { Config, KeyValueStore } from "../config";
import { Dispatch } from "redux";
import { Log } from "../utils";
import { readyAction } from "../state";
import { saveState } from "./Saver";

export const migrateState = async (
  dispatch: Dispatch,
  config: Config,
  loadedState: KeyValueStore,
  loadedVersion: number | undefined
) => {
  Log.d?.(`Migrating from version ${loadedVersion} to ${config.version} ...`);
  const tempState = await config.migrateState(
    clone(loadedState),
    loadedVersion,
    config.version
  );

  // Detect changes in the new state, so that the upgrade routine doesn't have
  // to worry about immutability
  const migratedState: KeyValueStore = {};
  for (const key in tempState) {
    if (!deepEqual(loadedState[key], tempState[key])) {
      // This slice has been changed: use the new one
      migratedState[key] = tempState[key];
    } else {
      // This slice has not been changed: reuse the one we loaded
      migratedState[key] = loadedState[key];
    }
  }

  // Save the newly updated state and its version
  Log.d?.("Saving migrated state...");
  saveState(loadedState, migratedState, config, true);

  Log.d?.("Migration complete.");
  dispatch(readyAction(migratedState, config.version));
};

const clone = (obj: any): any => {
  return JSON.parse(JSON.stringify(obj));
};

const isObject = (obj: any): boolean => {
  return obj !== null && typeof obj === "object";
};

const deepEqual = (obj1: any, obj2: any): boolean => {
  if (obj1 === obj2) {
    return true;
  }

  if (!isObject(obj1) || !isObject(obj2)) {
    return false;
  }

  const keys1 = Object.keys(obj1);
  const keys2 = Object.keys(obj2);

  if (keys1.length !== keys2.length) {
    return false;
  }

  for (const key of keys1) {
    if (!keys2.includes(key)) {
      return false;
    }
    if (!deepEqual(obj1[key], obj2[key])) {
      return false;
    }
  }

  return true;
};
