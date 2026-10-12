import { Reducer } from "redux";
import { Config, KeyValueStore, sanitizeConfig } from "../../config";
import { readyAction } from "../../state";
import { NullStorage } from "../Storage";
import { migrateState } from "../Migration";
import * as SaverModule from "../../storage/Saver";

jest.mock("../../storage/Saver");

describe("Migrate", () => {
  it("should properly migrate the loaded version", async () => {
    const mockLoadedState = {
      item1: { value: 1 },
      item2: { value: 2 },
    };
    const mockMigratedState = {
      item_a: { text: "Hello" },
      item_b: { text: "World" },
    };
    const mockMigrate = jest.fn().mockReturnValue(mockMigratedState);
    const mockSaveState = jest.spyOn(SaverModule, "saveState").mockReset();
    const config: Config = sanitizeConfig({
      reducer: {
        item1: {} as Reducer,
        item2: {} as Reducer,
        item3: {} as Reducer,
      },
      storage: NullStorage,
      migrateState: mockMigrate,
      version: 43,
    });
    const mockDispatch = jest.fn();

    await migrateState(mockDispatch, config, mockLoadedState, 42);

    // Should have migrated the state...
    expect(mockMigrate).toHaveBeenCalledWith(mockLoadedState, 42, 43);
    // ...saved it...
    expect(mockSaveState).toHaveBeenCalledWith(
      mockLoadedState,
      mockMigratedState,
      config,
      true
    );
    // ...and moved on
    expect(mockDispatch).toHaveBeenCalledWith(
      readyAction(mockMigratedState, 43)
    );
  });

  it("should allow mutability during state migration", async () => {
    const mockLoadedState = {
      item1: { value: 1 },
      item2: { value: 2 },
      item3: { value: 3 },
    };
    const mutatingMigrate = async (
      state: KeyValueStore
    ): Promise<KeyValueStore> => {
      // Mutates the received state by adding a new property
      state.item1.text = "Ciao";
      delete state.item3;
      return state;
    };
    const mockSaveState = jest.spyOn(SaverModule, "saveState").mockReset();
    const config: Config = sanitizeConfig({
      reducer: {
        item1: {} as Reducer,
        item2: {} as Reducer,
        item3: {} as Reducer,
      },
      storage: NullStorage,
      migrateState: mutatingMigrate,
      version: 43,
    });
    const mockDispatch = jest.fn();

    await migrateState(mockDispatch, config, mockLoadedState, 42);

    console.log(JSON.stringify(mockSaveState.mock.calls[0][1]));

    expect(mockSaveState.mock.calls[0][0]).toBe(mockLoadedState);
    // Item1 should have been updated
    expect(mockSaveState.mock.calls[0][1]["item1"]).toEqual({
      value: 1,
      text: "Ciao",
    });
    // Item2 should be unchanged
    expect(mockSaveState.mock.calls[0][1]["item2"]).toBe(mockLoadedState.item2);
    // Item3 should be no longer there
    expect(mockSaveState.mock.calls[0][1]["item3"]).toBeUndefined();
  });
});
