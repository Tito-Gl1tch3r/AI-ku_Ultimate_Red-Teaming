import { Reducer } from "redux";
import { sanitizeConfig, Config } from "..";
import { NullStorage } from "../../storage";

describe("Filters", () => {
  it("by default should allow everything except the internal state", () => {
    const config: Config = sanitizeConfig({
      reducer: {
        item1: {} as Reducer,
        item2: {} as Reducer,
        item3: {} as Reducer,
        reduxManentState: {} as Reducer,
      },
      storage: NullStorage,
    });

    expect(config._filter.isAllowed("item1")).toBe(true);
    expect(config._filter.isAllowed("item2")).toBe(true);
    expect(config._filter.isAllowed("item3")).toBe(true);
    expect(config._filter.isAllowed("reduxManentState")).toBe(false);
  });

  it("should deny everything not included in the whitelist", () => {
    const config: Config = sanitizeConfig({
      reducer: {
        item1: {} as Reducer,
        item2: {} as Reducer,
        item3: {} as Reducer,
      },
      storage: NullStorage,
      whitelist: ["item1"],
    });

    expect(config._filter.isAllowed("item1")).toBe(true);
    expect(config._filter.isAllowed("item2")).toBe(false);
    expect(config._filter.isAllowed("item3")).toBe(false);
  });

  it("should deny everything included in the blacklist", () => {
    const config: Config = sanitizeConfig({
      reducer: {
        item1: {} as Reducer,
        item2: {} as Reducer,
        item3: {} as Reducer,
      },
      storage: NullStorage,
      blacklist: ["item2"],
    });

    expect(config._filter.isAllowed("item1")).toBe(true);
    expect(config._filter.isAllowed("item2")).toBe(false);
    expect(config._filter.isAllowed("item3")).toBe(true);
  });
});
