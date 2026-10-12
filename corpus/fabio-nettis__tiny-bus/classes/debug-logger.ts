import { c, type ConsoleColors } from "utils/console";

import type {
  DebugEventName,
  DebugEventKeyPrefix,
  DebugEventCallback,
  DebugLoggerInterface,
} from "types/debug-logger";

/**
 * A class for logging debug events. This class is used internally by TinyBus,
 * optionally a callback can be provided to log events to a custom logger.
 */
export default class DebugLogger implements DebugLoggerInterface {
  constructor(private readonly callback?: DebugEventCallback) {}

  // stores start times for each event
  private readonly time = new Map<string, Date>();

  // colors for each event type
  colors: Record<DebugEventKeyPrefix, ConsoleColors> = {
    error: "red",
    emit: "green",
    remove: "red",
    unique: "cyan",
    replay: "blue",
    persist: "gray",
    restore: "gray",
    subscribe: "yellow",
    removeAll: "red",
  };

  // sentences for each event type
  sentences: Record<DebugEventKeyPrefix, string> = {
    emit: "Emitting event",
    remove: "Removing event",
    replay: "Replaying event",
    restore: "Restoring event",
    persist: "Persisting event",
    error: "Error handler for event",
    subscribe: "Subscribing to event",
    unique: "Uniqueness check for event",
    removeAll: "Removing all subscribers for event",
  };

  getDuration(id: string): number {
    if (!this.time.has(id)) throw new Error(`No start time for ${id}`);
    const start = this.time.get(id);
    if (!start) throw new Error(`Invalid start time for ${id}`);
    const duration = new Date().getTime() - start.getTime();
    this.time.delete(id);
    return duration;
  }

  log(
    debugEventName: DebugEventName,
    keyPrefix: DebugEventKeyPrefix,
    debugEventId: string,
  ) {
    const key = `${keyPrefix}::${debugEventId}`;
    const isEventStart = debugEventName.startsWith("start", 0);
    if (isEventStart) {
      this.time.set(key, new Date());
      if (this.callback) return this.callback(debugEventName, debugEventId);
      this.out(debugEventName, keyPrefix, debugEventId);
    } else {
      const ms = this.getDuration(`${keyPrefix}::${debugEventId}`);
      if (this.callback) return this.callback(debugEventName, debugEventId, ms);
      this.out(debugEventName, keyPrefix, debugEventId, ms);
    }
  }

  out(
    debugEventName: DebugEventName,
    keyPrefix: DebugEventKeyPrefix,
    debugEventId: string,
    debugEventDurationMs?: number,
  ) {
    const color = this.colors[keyPrefix] ?? "gray";
    const isEventStart = debugEventName.startsWith("start", 0);
    const sentence = (this.sentences[keyPrefix] ?? "Unknown").toLowerCase();

    const label = c(
      `[${((str: string) => str.charAt(0).toUpperCase() + str.slice(1))(keyPrefix)}]`,
      color,
    );

    if (isEventStart) {
      console.log(`${label} Started ${sentence} ${debugEventId}`);
    } else {
      console.log(
        `${label} Ended ${sentence} ${debugEventId} (${debugEventDurationMs} ms)`,
      );
    }
  }
}
