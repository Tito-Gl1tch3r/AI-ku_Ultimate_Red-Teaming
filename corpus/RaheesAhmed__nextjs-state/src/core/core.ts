import { createContext, useContext, useCallback, useRef, useEffect, useState } from 'react';
import type {
  StateConfig,
  Action,
  Selector,
  StateOptions,
  INextStateError,
  EqualityFn,
  DeepPartial,
  DeepReadonly,
  StateSnapshot,
} from '../types/types';
import { createPerformanceMonitor, createDebugLogger, deepMerge, ListenerSet } from '../utils';
import { DevTools } from '../dev-tools';

export class NextStateError extends Error implements INextStateError {
  code: string;
  details?: Record<string, unknown>;

  constructor(error: INextStateError) {
    super(error.message);
    this.name = 'NextStateError';
    this.code = error.code;
    this.details = error.details;
  }
}

/*#__PURE__*/
export function createNextState<T extends object>(config: StateConfig<T>) {
  // Initialize utilities
  const performance = createPerformanceMonitor();
  const debugLogger = createDebugLogger(!!config.options?.devTools);
  const devTools = config.options?.devTools ? new DevTools(config.initialState) : null;

  // State container with type safety
  let state: DeepReadonly<T> = config.initialState as DeepReadonly<T>;
  const listeners = new ListenerSet<DeepReadonly<T>>(!!config.options?.devTools);
  const serverCache = new Map<string, unknown>();

  // Batch update handling
  let batchUpdateScheduled = false;
  const pendingUpdates: DeepPartial<T>[] = [];

  // Type-safe context
  const StateContext = createContext<{
    getState: () => DeepReadonly<T>;
    setState: (update: DeepPartial<T>) => void;
    subscribe: (listener: (state: DeepReadonly<T>) => void) => () => void;
    devTools: DevTools<T> | null;
  } | null>(null);

  // Enhanced storage handling with type safety
  const storage = {
    save: async (data: T) => {
      if (config.options?.storage && typeof window !== 'undefined') {
        const { key, serialize = JSON.stringify } = config.options.storage;
        const startTime = performance.now();

        try {
          localStorage.setItem(
            key as string,
            serialize({
              version: config.options.storage.version,
              data,
            })
          );
          debugLogger.log('State saved to storage', {
            key,
            version: config.options.storage.version,
          });
        } catch (error) {
          debugLogger.error('storage save', error);
          throw new NextStateError({
            code: 'STORAGE_ERROR',
            message: 'Failed to save state to storage',
            details: { error },
          });
        } finally {
          performance.track('update', performance.now() - startTime);
        }
      }
    },
    load: () => {
      if (config.options?.storage && typeof window !== 'undefined') {
        const { key, deserialize = JSON.parse, migrations } = config.options.storage;

        const startTime = performance.now();
        try {
          const saved = localStorage.getItem(key as string);
          if (saved) {
            const { version, data } = deserialize(saved);
            if (version === config.options.storage.version) {
              debugLogger.log('State loaded from storage', { key, version });
              return data as T;
            } else if (migrations?.[version]) {
              const migratedData = migrations[version](data);
              debugLogger.log('State migrated', {
                fromVersion: version,
                toVersion: config.options.storage.version,
              });
              return migratedData;
            }
          }
        } catch (error) {
          debugLogger.error('storage load', error);
          throw new NextStateError({
            code: 'STORAGE_ERROR',
            message: 'Failed to load state from storage',
            details: { error },
          });
        } finally {
          performance.track('update', performance.now() - startTime);
        }
      }
      return null;
    },
  };

  // Batched state updates with DevTools integration
  const setState = (update: DeepPartial<T>, actionType?: string) => {
    pendingUpdates.push(update);
    debugLogger.log('Update queued', { pendingUpdates: pendingUpdates.length });

    if (!batchUpdateScheduled) {
      batchUpdateScheduled = true;
      const startTime = performance.now();

      Promise.resolve().then(() => {
        try {
          const nextState = pendingUpdates.reduce(
            (acc, update) => deepMerge(acc, update as T),
            state as T
          );

          state = nextState as DeepReadonly<T>;

          // Log action in DevTools
          if (devTools && actionType) {
            devTools.logAction({
              type: actionType,
              payload: update,
              duration: performance.now() - startTime,
            });
          }

          // Create state snapshot
          if (devTools) {
            devTools.createSnapshot(state as T);
          }

          listeners.notify(state, performance);
          debugLogger.log('Batch update applied', {
            updateCount: pendingUpdates.length,
            duration: performance.now() - startTime,
          });

          if (config.options?.storage) {
            storage.save(state as T).catch((error) => {
              debugLogger.error('storage save after update', error);
            });
          }
        } catch (error) {
          debugLogger.error('state update', error);
          throw new NextStateError({
            code: 'UPDATE_ERROR',
            message: 'Failed to apply state update',
            details: { error, pendingUpdates },
          });
        } finally {
          batchUpdateScheduled = false;
          pendingUpdates.length = 0;
          performance.track('update', performance.now() - startTime);
        }
      });
    }
  };

  // Enhanced selector hook with memoization
  function useSelector<R>(selector: Selector<T, R>, equalityFn: EqualityFn<R> = Object.is): R {
    const stableSelector = useCallback(selector, []); // Memoize selector
    const [value, setValue] = useState(() => stableSelector(state as T));
    const prevValue = useRef(value);
    const prevSelector = useRef(stableSelector);

    useEffect(() => {
      if (prevSelector.current !== stableSelector) {
        const newValue = stableSelector(state as T);
        if (!equalityFn(prevValue.current, newValue)) {
          prevValue.current = newValue;
          setValue(newValue);
        }
        prevSelector.current = stableSelector;
        debugLogger.log('Selector updated', { hasNewValue: prevValue.current !== newValue });
      }
    }, [stableSelector, equalityFn]);

    useEffect(() => {
      const listener = (nextState: DeepReadonly<T>) => {
        const nextValue = stableSelector(nextState as T);
        if (!equalityFn(prevValue.current, nextValue)) {
          prevValue.current = nextValue;
          setValue(nextValue);
          debugLogger.log('Selector value updated', {
            hasNewValue: true,
            selectorId: stableSelector.name || 'anonymous',
          });
        }
      };

      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    }, [stableSelector, equalityFn]);

    return value;
  }

  // Action creator with DevTools integration
  function createAction<P>(type: string, handler: (payload: P) => DeepPartial<T>) {
    return (payload: P) => {
      const update = handler(payload);
      setState(update, type);
      return update;
    };
  }

  return {
    StateContext,
    useSelector,
    getState: () => state,
    setState,
    createAction,
    devTools,
    getMetrics: () => performance.getMetrics(),
  };
}

// Export the create function as default and named
export default createNextState;
export { createNextState as create };
