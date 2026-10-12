import { it, expect, spyOn } from "bun:test";

import DebugLogger from "classes/debug-logger";
import type { DebugEventName } from "types/debug-logger";

const debugEventNames: DebugEventName[] = [
  "startReplay",
  "endReplay",
  "startEmit",
  "endEmit",
  "startSubscribe",
  "endSubscribe",
  "startRemove",
  "endRemove",
  "startRemoveAll",
  "endRemoveAll",
  "startPersist",
  "endPersist",
  "startRestore",
  "endRestore",
  "startErrorHandler",
  "endErrorHandler",
  "startIsUnique",
  "endIsUnique",
];

it("Callback is called with correct arguments", () => {
  const debugLogger = new DebugLogger((debugName, debugId, duration) => {
    expect(debugEventNames).toContain(debugName);
    expect(debugId).toBe("test");
    if (debugName.startsWith("start")) expect(duration).toBeUndefined();
    else expect(duration).toBeTypeOf("string");
  });

  // suppress console output
  const outSpy = spyOn(console, "log").mockImplementation(() => {});

  debugLogger.log("startEmit", "emit", "test");
  debugLogger.out("endEmit", "emit", "test");
  expect(outSpy).toHaveBeenCalled();
  debugLogger.log("startEmit", "emit", "test");
  expect(debugLogger.getDuration("emit::test")).toBeTypeOf("number");
});
