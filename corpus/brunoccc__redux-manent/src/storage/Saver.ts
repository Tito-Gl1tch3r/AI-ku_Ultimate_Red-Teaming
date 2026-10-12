import { Config, KeyValueStore, STORAGE_VERSION_KEY } from "../config";
import { Log } from "../utils";

let lastWritingTime = 0;
let coolDownCache: KeyValueStore = {};
let coolDownTimeout: NodeJS.Timeout | undefined = undefined;

export const saveState = (
  before: KeyValueStore,
  after: KeyValueStore,
  config: Config,
  saveVersion: boolean = false
) => {
  if (saveVersion) {
    writeKey(STORAGE_VERSION_KEY, { value: config.version }, config);
  }

  // Add to cache
  for (const [key, oldValue] of Object.entries(before || {})) {
    const newValue = after[key as keyof KeyValueStore];
    if (oldValue !== newValue) {
      coolDownCache[key] = newValue;
    }
  }

  if (coolDownTimeout !== undefined) {
    // Timer is already running, nothing else to do for now
    return;
  }

  // Check if we can write now or we need to set a new timer
  const timeLeft =
    config.coolDownTime === 0
      ? 0
      : lastWritingTime + config.coolDownTime - Date.now();

  if (timeLeft <= 0) {
    // Flush immediately
    flushCache(config);
    return;
  }
  // Set a delayed flush
  coolDownTimeout = setTimeout(() => {
    flushCache(config);
  }, timeLeft);
};

const flushCache = (config: Config) => {
  const now = Date.now();
  coolDownTimeout = undefined;
  lastWritingTime = now;
  for (const [key, value] of Object.entries(coolDownCache)) {
    if (config._filter.isAllowed(key)) {
      writeKey(key, value, config);
    } else {
      Log.v?.("Key skipped", { key, value });
    }
  }
  coolDownCache = {};
};

const writeKey = (
  key: string,
  newValue: object | undefined,
  config: Config
) => {
  if (newValue === undefined) {
    Log.v?.("Key removed", { key });
    config.storage.removeItem(key);
  } else {
    Log.v?.("Key saved", { key, newValue });
    config.storage.setItem(key, config.serializer.serialize(newValue));
  }
};
