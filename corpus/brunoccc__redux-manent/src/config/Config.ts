import { Reducer } from "redux";
import { DefaultSerializer, Serializer, Storage } from "../storage";
import { KeyValueStore } from "./Constants";
import { Filter, buildFilter } from "./Filters";
import { Log } from "../utils";

export type ReduxManentConfig = {
  reducer: { [id: string]: Reducer };
  storage: Storage;
  coolDownTime?: number;
  serializer?: Serializer;
  version?: number;
  migrateState?: (
    state: KeyValueStore,
    from: number | undefined,
    to: number
  ) => Promise<KeyValueStore>;
  verbose?: boolean;
  whitelist?: string[];
  blacklist?: string[];
};

type ReduxManentContext = {
  _filter: Filter;
};

export type Config = Required<ReduxManentConfig> & ReduxManentContext;

export const sanitizeConfig = (config: ReduxManentConfig): Config => {
  const defaultConfig: Config = {
    reducer: config.reducer,
    storage: config.storage,
    coolDownTime: config.coolDownTime ?? 100,
    serializer: config.serializer ?? DefaultSerializer,
    version: config.version ?? 0,
    migrateState:
      config.migrateState ?? (async (state: KeyValueStore) => state),
    verbose: config.verbose ?? false,
    whitelist: config.whitelist ?? [],
    blacklist: config.blacklist ?? [],
    _filter: buildFilter(config.reducer, config.whitelist, config.blacklist),
  };

  Log.setVerbose?.(defaultConfig.verbose);

  return defaultConfig;
};
