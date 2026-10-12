import { Reducer } from "redux";
import {
  KeyValueStore,
  STORAGE_VERSION_KEY,
  sanitizeConfig,
} from "../../config";

const ITEM1 = { value: 1 };
const ITEM1_NEW = { value: 11 };
const ITEM2 = { value: 2 };
const ITEM2_NEW = { value: 22 };
const ITEM3 = { value: "Hello" };
const ITEM3_NEW = { value: "Ciao" };

const STATE_T0: KeyValueStore = {
  item1: ITEM1,
  item2: ITEM2,
  item3: ITEM3,
};
const STATE_T1: KeyValueStore = {
  item1: ITEM1,
  item2: ITEM2_NEW,
  item3: ITEM3_NEW,
};
const STATE_T2: KeyValueStore = {
  item1: ITEM1_NEW,
  item2: ITEM2,
  item3: ITEM3_NEW,
};

describe("Saver", () => {
  beforeEach(() => {
    jest.resetModules(); // Clear module cache to reset the module state
  });

  it("should detect and save the differences", async () => {
    const { saveState } = require("../Saver");
    const mockStorage = {
      getItem: jest.fn(),
      setItem: jest.fn(),
      removeItem: jest.fn(),
    };
    const config = sanitizeConfig({
      reducer: {
        item1: {} as Reducer,
        item2: {} as Reducer,
        item3: {} as Reducer,
      },
      storage: mockStorage,
      version: 42,
      coolDownTime: 0,
    });

    saveState(STATE_T0, STATE_T1, config, false);

    expect(mockStorage.setItem.mock.calls[0]).toEqual([
      "item2",
      JSON.stringify(ITEM2_NEW),
    ]);
    expect(mockStorage.setItem.mock.calls[1]).toEqual([
      "item3",
      JSON.stringify(ITEM3_NEW),
    ]);
    expect(mockStorage.setItem.mock.calls[2]).toBeUndefined();
  });

  it("should only save whitelisted", async () => {
    const { saveState } = require("../Saver");
    const mockStorage = {
      getItem: jest.fn(),
      setItem: jest.fn(),
      removeItem: jest.fn(),
    };
    const config = sanitizeConfig({
      reducer: {
        item1: {} as Reducer,
        item2: {} as Reducer,
        item3: {} as Reducer,
      },
      storage: mockStorage,
      version: 42,
      coolDownTime: 0,
      whitelist: ["item3"],
    });

    saveState(STATE_T0, STATE_T1, config, false);

    expect(mockStorage.setItem.mock.calls[0]).toEqual([
      "item3",
      JSON.stringify(ITEM3_NEW),
    ]);
    expect(mockStorage.setItem.mock.calls[1]).toBeUndefined();
  });

  it("should not save blacklisted", async () => {
    const { saveState } = require("../Saver");
    const mockStorage = {
      getItem: jest.fn(),
      setItem: jest.fn(),
      removeItem: jest.fn(),
    };
    const config = sanitizeConfig({
      reducer: {
        item1: {} as Reducer,
        item2: {} as Reducer,
        item3: {} as Reducer,
      },
      storage: mockStorage,
      version: 42,
      coolDownTime: 0,
      blacklist: ["item3"],
    });

    saveState(STATE_T0, STATE_T1, config, false);

    expect(mockStorage.setItem.mock.calls[0]).toEqual([
      "item2",
      JSON.stringify(ITEM2_NEW),
    ]);
    expect(mockStorage.setItem.mock.calls[1]).toBeUndefined();
  });

  it("should save the version when requested", async () => {
    const { saveState } = require("../Saver");
    const mockStorage = {
      getItem: jest.fn(),
      setItem: jest.fn(),
      removeItem: jest.fn(),
    };
    const config = sanitizeConfig({
      reducer: {
        item1: {} as Reducer,
        item2: {} as Reducer,
        item3: {} as Reducer,
      },
      storage: mockStorage,
      version: 42,
      coolDownTime: 0,
    });

    saveState(STATE_T0, STATE_T1, config, true);

    // First persist the version
    expect(mockStorage.setItem.mock.calls[0]).toEqual([
      STORAGE_VERSION_KEY,
      JSON.stringify({ value: 42 }),
    ]);
    // Then the data
    expect(mockStorage.setItem.mock.calls[1]).toEqual([
      "item2",
      JSON.stringify(ITEM2_NEW),
    ]);
    expect(mockStorage.setItem.mock.calls[2]).toEqual([
      "item3",
      JSON.stringify(ITEM3_NEW),
    ]);
    expect(mockStorage.setItem.mock.calls[3]).toBeUndefined();
  });

  it("should do nothing when the state is unchanged", () => {
    const { saveState } = require("../Saver");
    const mockStorage = {
      getItem: jest.fn(),
      setItem: jest.fn(),
      removeItem: jest.fn(),
    };
    const config = sanitizeConfig({
      reducer: {
        item1: {} as Reducer,
        item2: {} as Reducer,
        item3: {} as Reducer,
      },
      storage: mockStorage,
      version: 42,
      coolDownTime: 0,
    });

    saveState(STATE_T0, STATE_T0, config);
    saveState(STATE_T1, STATE_T1, config);

    expect(mockStorage.setItem.mock.calls[0]).toBeUndefined();
  });

  it("should handle the rate limit", async () => {
    const { saveState } = require("../Saver");
    jest.useFakeTimers();

    const mockStorage = {
      getItem: jest.fn(),
      setItem: jest.fn(),
      removeItem: jest.fn(),
    };
    const config = sanitizeConfig({
      reducer: {
        item1: {} as Reducer,
        item2: {} as Reducer,
        item3: {} as Reducer,
      },
      storage: mockStorage,
      version: 42,
      coolDownTime: 1000,
    });

    // First set of changes are written immediately
    saveState(STATE_T0, STATE_T1, config, false);
    expect(mockStorage.setItem.mock.calls[0]).toEqual([
      "item2",
      JSON.stringify(ITEM2_NEW),
    ]);
    expect(mockStorage.setItem.mock.calls[1]).toEqual([
      "item3",
      JSON.stringify(ITEM3_NEW),
    ]);
    expect(mockStorage.setItem.mock.calls[2]).toBeUndefined();

    // Next changes must be cached and wait for the cooldown timer
    saveState(STATE_T1, STATE_T2, config, false);
    expect(mockStorage.setItem.mock.calls[2]).toBeUndefined();

    // Still nothing
    jest.advanceTimersByTime(990);
    expect(mockStorage.setItem.mock.calls[2]).toBeUndefined();

    // Now flush should take place and should contain the final state recorded so far
    jest.advanceTimersByTime(10);
    expect(mockStorage.setItem.mock.calls[2]).toEqual([
      "item1",
      JSON.stringify(ITEM1_NEW),
    ]);
    expect(mockStorage.setItem.mock.calls[3]).toEqual([
      "item2",
      JSON.stringify(ITEM2),
    ]);
  });

  it("should coalesce writing operations", async () => {
    const { saveState } = require("../Saver");
    jest.useFakeTimers();

    const mockStorage = {
      getItem: jest.fn(),
      setItem: jest.fn(),
      removeItem: jest.fn(),
    };
    const config = sanitizeConfig({
      reducer: {
        item1: {} as Reducer,
        item2: {} as Reducer,
        item3: {} as Reducer,
      },
      storage: mockStorage,
      version: 42,
      coolDownTime: 1000,
    });

    // First set of changes are written immediately
    saveState(STATE_T0, STATE_T1, config, false);
    expect(mockStorage.setItem.mock.calls[0]).toEqual([
      "item2",
      JSON.stringify(ITEM2_NEW),
    ]);
    expect(mockStorage.setItem.mock.calls[1]).toEqual([
      "item3",
      JSON.stringify(ITEM3_NEW),
    ]);
    expect(mockStorage.setItem.mock.calls[2]).toBeUndefined();

    // Fires a rapid sequence of changes
    saveState(STATE_T1, STATE_T2, config, false);
    jest.advanceTimersByTime(10);
    saveState(STATE_T2, STATE_T0, config, false);
    jest.advanceTimersByTime(10);
    saveState(STATE_T0, STATE_T1, config, false);
    jest.advanceTimersByTime(10);
    saveState(STATE_T1, STATE_T2, config, false);
    jest.advanceTimersByTime(10);

    // Nothing should have been written yet
    expect(mockStorage.setItem.mock.calls[2]).toBeUndefined();

    // Still nothing
    jest.advanceTimersByTime(940);
    expect(mockStorage.setItem.mock.calls[2]).toBeUndefined();

    // A new change should not flush the cache and not retrigger the timers
    saveState(STATE_T2, STATE_T0, config, false);
    jest.advanceTimersByTime(10);
    expect(mockStorage.setItem.mock.calls[2]).toBeUndefined();

    // Now flush should take place and should contain the final state recorded so far
    jest.advanceTimersByTime(10);
    expect(mockStorage.setItem.mock.calls[2]).toEqual([
      "item1",
      JSON.stringify(ITEM1),
    ]);
    expect(mockStorage.setItem.mock.calls[3]).toEqual([
      "item2",
      JSON.stringify(ITEM2),
    ]);
    expect(mockStorage.setItem.mock.calls[4]).toEqual([
      "item3",
      JSON.stringify(ITEM3),
    ]);
  });
});
