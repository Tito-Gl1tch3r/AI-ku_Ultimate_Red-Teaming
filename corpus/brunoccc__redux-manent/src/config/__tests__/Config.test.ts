import { Reducer } from "redux";
import { sanitizeConfig, ReduxManentConfig, Config } from "..";
import { NullStorage, DefaultSerializer, Serializer } from "../../storage";

describe("Config", () => {
  it("should use default values if no config is provided", () => {
    const reducer = { item1: {} as Reducer };
    const storage = NullStorage;
    const config: ReduxManentConfig = { reducer, storage };
    const sanitizedConfig: Config = sanitizeConfig(config);

    expect(sanitizedConfig.reducer).toBe(reducer);
    expect(sanitizedConfig.storage).toBe(storage);
    expect(sanitizedConfig.coolDownTime).toBe(100);
    expect(sanitizedConfig.serializer).toBe(DefaultSerializer);
    expect(sanitizedConfig.version).toBe(0);
    expect(sanitizedConfig.verbose).toBe(false);
    expect(sanitizedConfig.whitelist).toEqual([]);
    expect(sanitizedConfig.blacklist).toEqual([]);
  });

  it("should override default values with provided config", () => {
    const customSerializer: Serializer = {
      serialize: function (o: object): string {
        return "hello";
      },
      deserialize: function (s: string): object {
        return {};
      },
    };
    const customMigrateState = async (state: any) => state;
    const reducer = { item1: {} as Reducer };
    const storage = NullStorage;
    const config: ReduxManentConfig = {
      reducer,
      storage,
      coolDownTime: 200,
      serializer: customSerializer,
      version: 1,
      migrateState: customMigrateState,
      verbose: true,
      whitelist: ["item1"],
      blacklist: ["item2"],
    };
    const sanitizedConfig: Config = sanitizeConfig(config);

    expect(sanitizedConfig.reducer).toBe(reducer);
    expect(sanitizedConfig.storage).toBe(storage);
    expect(sanitizedConfig.coolDownTime).toBe(200);
    expect(sanitizedConfig.serializer).toBe(customSerializer);
    expect(sanitizedConfig.version).toBe(1);
    expect(sanitizedConfig.migrateState).toBe(customMigrateState);
    expect(sanitizedConfig.verbose).toBe(true);
    expect(sanitizedConfig.whitelist).toEqual(["item1"]);
    expect(sanitizedConfig.blacklist).toEqual(["item2"]);
  });

  it("should retain default values for undefined properties in provided config", () => {
    const reducer = { item1: {} as Reducer };
    const storage = NullStorage;
    const config: ReduxManentConfig = {
      reducer,
      storage,
      coolDownTime: undefined,
      serializer: undefined,
      version: undefined,
      migrateState: undefined,
      verbose: undefined,
      whitelist: undefined,
      blacklist: undefined,
    };
    const sanitizedConfig: Config = sanitizeConfig(config);

    expect(sanitizedConfig.reducer).toBe(reducer);
    expect(sanitizedConfig.storage).toBe(storage);
    expect(sanitizedConfig.coolDownTime).toBe(100);
    expect(sanitizedConfig.serializer).toBe(DefaultSerializer);
    expect(sanitizedConfig.version).toBe(0);
    expect(sanitizedConfig.verbose).toBe(false);
    expect(sanitizedConfig.whitelist).toEqual([]);
    expect(sanitizedConfig.blacklist).toEqual([]);
  });

  it("should merge provided config with default values", () => {
    const reducer = { item1: {} as Reducer };
    const storage = NullStorage;
    const config: ReduxManentConfig = {
      reducer,
      storage,
      whitelist: ["item1"],
      blacklist: ["item2"],
    };
    const sanitizedConfig: Config = sanitizeConfig(config);

    expect(sanitizedConfig.reducer).toBe(reducer);
    expect(sanitizedConfig.storage).toBe(storage);
    expect(sanitizedConfig.coolDownTime).toBe(100);
    expect(sanitizedConfig.serializer).toBe(DefaultSerializer);
    expect(sanitizedConfig.version).toBe(0);
    expect(sanitizedConfig.verbose).toBe(false);
    expect(sanitizedConfig.whitelist).toEqual(["item1"]);
    expect(sanitizedConfig.blacklist).toEqual(["item2"]);
  });
});
