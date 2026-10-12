import { persistReducer, wakeUp } from "..";
import { NullStorage } from "../storage";
import * as Reducers from "../state/Reducers";
import * as Saver from "../storage/Saver";
import { sanitizeConfig } from "../config";

const DEFAULT_MANENT_STATE = {
  test: true,
  value: 42,
};

jest.mock("../state/Reducers");
jest.mock("../storage/Saver");

describe("ReduxManent tests", () => {
  beforeEach(() => {
    const mockManentStateReducer = jest.spyOn(Reducers, "reduxManentState");
    mockManentStateReducer.mockReturnValue(DEFAULT_MANENT_STATE);
  });

  it("Should combine reducers", () => {
    // Creates fake reducers that save the actions payload into a "value" field
    const reducer = persistReducer({
      reducer: {
        item1: (state, action) => {
          return { ...state, value: action.payload };
        },
        item2: (state, action) => {
          return { ...state, value: action.payload };
        },
      },
      storage: NullStorage,
    });

    // Invoke the reducer with an action and an empty state
    const initialState = {};
    const action = { type: "test", payload: 12 };
    const state = reducer(initialState, action);

    // Assert that the state contains the reducers slices and the redux-manent slice
    expect(state.item1).toEqual({ value: 12 });
    expect(state.item2).toEqual({ value: 12 });
    expect(state.reduxManentState).toEqual(DEFAULT_MANENT_STATE);
  });

  it("Should handle internal actions", () => {
    const mockHandleInternalActions = jest
      .spyOn(Reducers, "handleInternalActions")
      .mockReset();

    // Creates fake reducers that save the actions payload into a "value" field
    const config = sanitizeConfig({
      reducer: {
        item1: (state, action) => {
          return { ...state, value: action.payload };
        },
        item2: (state, action) => {
          return { ...state, value: action.payload };
        },
      },
      storage: NullStorage,
    });
    const reducer = persistReducer(config);

    const mockDispatch = jest.fn();
    wakeUp(mockDispatch);

    // Invoke the reducer with an action and an empty state
    const initialState = {};
    const action = { type: "test", payload: 13 };
    reducer(initialState, action);

    // Assert that the right information are passed to handleInternalActions
    expect(mockHandleInternalActions.mock.calls[0][0]).toBe(mockDispatch);
    expect(mockHandleInternalActions.mock.calls[0][1]).toEqual(initialState);
    expect(mockHandleInternalActions.mock.calls[0][2]).toEqual(action);
    expect(JSON.stringify(mockHandleInternalActions.mock.calls[0][3])).toEqual(
      JSON.stringify(config)
    );
  });

  it("Should pass the state to the saving engine", () => {
    jest
      .spyOn(Reducers, "handleInternalActions")
      .mockImplementation((_dispatch, state) => state);
    jest.spyOn(Reducers, "reduxManentState").mockReturnValue({
      ready: true,
    });
    const mockSaveState = jest.spyOn(Saver, "saveState").mockReset();

    // Creates fake reducers that save the actions payload into a "value" field
    const config = sanitizeConfig({
      reducer: {
        item1: (state, action) => {
          return { ...state, value: action.payload };
        },
        item2: (state, action) => {
          return { ...state, value: action.payload };
        },
      },
      storage: NullStorage,
    });
    const reducer = persistReducer(config);

    const mockDispatch = jest.fn();
    wakeUp(mockDispatch);

    // Invoke the reducer with an action
    const initialState = {
      item1: { value: 10 },
      item2: { value: 11 },
    };
    const action = { type: "test", payload: 13 };
    reducer(initialState, action);

    // Assert that the right information are passed to saveState
    expect(mockSaveState.mock.calls[0][0]).toBe(initialState);
    expect(mockSaveState.mock.calls[0][1]).toEqual({
      item1: { value: 13 },
      item2: { value: 13 },
      reduxManentState: { ready: true },
    });
    expect(JSON.stringify(mockSaveState.mock.calls[0][2])).toEqual(
      JSON.stringify(config)
    );
  });

  it("Should not call the saving engine if not ready", () => {
    jest
      .spyOn(Reducers, "handleInternalActions")
      .mockImplementation((_dispatch, state) => state);
    jest.spyOn(Reducers, "reduxManentState").mockReturnValue({
      ready: false,
    });
    const mockSaveState = jest.spyOn(Saver, "saveState").mockReset();

    // Creates fake reducers that save the actions payload into a "value" field
    const config = sanitizeConfig({
      reducer: {
        item1: (state, action) => {
          return { ...state, value: action.payload };
        },
        item2: (state, action) => {
          return { ...state, value: action.payload };
        },
      },
      storage: NullStorage,
    });
    const reducer = persistReducer(config);

    const mockDispatch = jest.fn();
    wakeUp(mockDispatch);

    // Invoke the reducer with an action
    const initialState = {
      item1: { value: 10 },
      item2: { value: 11 },
    };
    const action = { type: "test", payload: 13 };
    reducer(initialState, action);

    // Assert that saveState wasn't called at all
    expect(mockSaveState).not.toHaveBeenCalled();
  });
});
