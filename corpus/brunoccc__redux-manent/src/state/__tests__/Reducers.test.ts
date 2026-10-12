import { Action, Reducer } from "redux";
import {
  ReduxManentState,
  handleInternalActions,
  reduxManentState,
} from "../Reducers";
import { readyAction, startAction } from "..";
import { sanitizeConfig } from "../../config";
import { NullStorage } from "../../storage";
import * as LoaderModule from "../../storage/Loader";

jest.mock("../../storage/Loader");

describe("Reducers", () => {
  it("should create the initial state", () => {
    const state: ReduxManentState = reduxManentState(undefined, {} as Action);

    expect(state.loading).toBe(false);
    expect(state.ready).toBe(false);
    expect(state.version).toBe(undefined);
  });

  it("should handle START internal action", () => {
    const mockDispatch = jest.fn();
    const mockLoadState = jest.spyOn(LoaderModule, "loadState");
    const config = sanitizeConfig({
      reducer: {
        item1: {} as Reducer,
        item2: {} as Reducer,
      },
      storage: NullStorage,
    });

    const initialState = {};
    const state = handleInternalActions(
      mockDispatch,
      initialState,
      startAction(),
      config
    );

    expect(mockLoadState).toHaveBeenCalledTimes(1);
    expect(state.reduxManentState.loading).toBe(true);
    expect(state.reduxManentState.ready).toBe(false);
    expect(state.reduxManentState.version).toBe(undefined);
  });

  it("should handle READY internal action", () => {
    const mockDispatch = jest.fn();
    const config = sanitizeConfig({
      reducer: {
        item1: {} as Reducer,
        item2: {} as Reducer,
      },
      storage: NullStorage,
    });
    // Initial state is empty
    const initialState = {};
    // Loaded state is populated
    const item1 = {
      hello: "hello",
      test: "1",
    };
    const item2 = {
      world: "world",
      test: "2",
    };
    const loadedState = { item1, item2 };

    const state = handleInternalActions(
      mockDispatch,
      initialState,
      readyAction(loadedState, 42),
      config
    );

    expect(state.item1).toEqual(item1);
    expect(state.item2).toEqual(item2);
    expect(state.reduxManentState.loading).toBe(false);
    expect(state.reduxManentState.ready).toBe(true);
    expect(state.reduxManentState.version).toBe(42);
  });

  it("should ignore other actions", () => {
    const mockDispatch = jest.fn();
    const config = sanitizeConfig({
      reducer: {
        item1: {} as Reducer,
        item2: {} as Reducer,
      },
      storage: NullStorage,
    });
    // Initial state is populated
    const item1 = {
      hello: "hello",
      test: "1",
    };
    const item2 = {
      world: "world",
      test: "2",
    };
    const reduxManentState = {
      loading: false,
      ready: true,
      version: 42,
    };
    const initialState = { item1, item2, reduxManentState };

    const state = handleInternalActions(
      mockDispatch,
      initialState,
      { type: "TestAction" },
      config
    );

    expect(state.item1).toEqual(item1);
    expect(state.item2).toEqual(item2);
    expect(state.reduxManentState).toEqual(reduxManentState);
  });
});
