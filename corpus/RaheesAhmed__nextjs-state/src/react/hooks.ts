import {
  useEffect,
  useCallback,
  useRef,
  useState,
  useMemo,
  useContext,
  useTransition,
  useSyncExternalStore,
} from 'react';
import type { DeepPartial, Selector, EqualityFn } from '../types/types';
import { StateContext } from './context';

/**
 * Hook to access state with automatic subscription
 */
export function useNextState<T extends object, R = T>(
  selector?: Selector<T, R>,
  equalityFn: EqualityFn<R> = Object.is
): R {
  const store = useContext(StateContext);
  if (!store) {
    throw new Error('useNextState must be used within NextStateProvider');
  }

  // Use sync external store for better concurrent mode support
  return useSyncExternalStore(
    store.subscribe,
    // Memoize selector
    useMemo(
      () => (selector ? () => selector(store.getState()) : store.getState),
      [selector, store]
    ),
    // Server-side state
    useMemo(
      () => (selector ? () => selector(store.getInitialState()) : store.getInitialState),
      [selector, store]
    )
  );
}

/**
 * Hook for optimistic updates with automatic rollback
 */
export function useOptimisticUpdate<T extends object>() {
  const store = useContext(StateContext);
  const [isPending, startTransition] = useTransition();
  const pendingUpdates = useRef<Array<{ update: DeepPartial<T>; timestamp: number }>>([]);

  if (!store) {
    throw new Error('useOptimisticUpdate must be used within NextStateProvider');
  }

  const update = useCallback(
    (update: DeepPartial<T>) => {
      const timestamp = Date.now();
      
      // Apply optimistic update
      store.setState(update);
      pendingUpdates.current.push({ update, timestamp });

      // Schedule server update
      startTransition(() => {
        store.syncWithServer(update).catch(() => {
          // Rollback on error
          const failedUpdate = pendingUpdates.current.find(u => u.timestamp === timestamp);
          if (failedUpdate) {
            // Remove failed update
            pendingUpdates.current = pendingUpdates.current.filter(u => u !== failedUpdate);
            // Reapply remaining updates
            store.setState(store.getInitialState());
            pendingUpdates.current.forEach(({ update }) => store.setState(update));
          }
        });
      });
    },
    [store]
  );

  return [update, isPending] as const;
}

/**
 * Hook for async actions with loading states
 */
export function useNextAction<T extends object, P = void>(
  action: (payload: P) => Promise<DeepPartial<T>>
) {
  const store = useContext(StateContext);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  if (!store) {
    throw new Error('useNextAction must be used within NextStateProvider');
  }

  const execute = useCallback(
    async (payload: P) => {
      try {
        setIsLoading(true);
        setError(null);
        const update = await action(payload);
        store.setState(update);
      } catch (err) {
        setError(err as Error);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [action, store]
  );

  return { execute, isLoading, error };
}

/**
 * Hook for computed values with dependency tracking
 */
export function useComputed<T extends object, R>(
  compute: (state: T) => R,
  deps: any[] = []
): R {
  const state = useNextState<T>();
  return useMemo(() => compute(state), [state, ...deps]);
}

/**
 * Hook for batched updates
 */
export function useBatchedUpdates<T extends object>() {
  const store = useContext(StateContext);
  const batchedUpdates = useRef<DeepPartial<T>[]>([]);
  const batchTimeout = useRef<NodeJS.Timeout>();

  if (!store) {
    throw new Error('useBatchedUpdates must be used within NextStateProvider');
  }

  const scheduleUpdate = useCallback(() => {
    if (batchTimeout.current) {
      clearTimeout(batchTimeout.current);
    }

    batchTimeout.current = setTimeout(() => {
      if (batchedUpdates.current.length) {
        // Merge all updates
        const mergedUpdate = batchedUpdates.current.reduce(
          (acc, update) => ({ ...acc, ...update }),
          {} as DeepPartial<T>
        );
        store.setState(mergedUpdate);
        batchedUpdates.current = [];
      }
    }, 0);
  }, [store]);

  const queueUpdate = useCallback(
    (update: DeepPartial<T>) => {
      batchedUpdates.current.push(update);
      scheduleUpdate();
    },
    [scheduleUpdate]
  );

  // Cleanup
  useEffect(() => {
    return () => {
      if (batchTimeout.current) {
        clearTimeout(batchTimeout.current);
      }
    };
  }, []);

  return queueUpdate;
}

/**
 * Hook for state persistence
 */
export function usePersist<T extends object>(key: string) {
  const store = useContext(StateContext);
  const [isLoading, setIsLoading] = useState(true);

  if (!store) {
    throw new Error('usePersist must be used within NextStateProvider');
  }

  useEffect(() => {
    // Load persisted state
    store.loadPersistedState(key).finally(() => {
      setIsLoading(false);
    });

    // Subscribe to changes
    return store.subscribeWithKey(key, (state) => {
      store.persistState(key, state);
    });
  }, [store, key]);

  return isLoading;
}

/**
 * Hook for state history
 */
export function useStateHistory<T extends object>(maxHistory = 10) {
  const store = useContext(StateContext);
  const [history, setHistory] = useState<T[]>([]);
  const [currentIndex, setCurrentIndex] = useState(-1);

  if (!store) {
    throw new Error('useStateHistory must be used within NextStateProvider');
  }

  useEffect(() => {
    return store.subscribe((state) => {
      setHistory(prev => {
        const newHistory = [...prev.slice(0, currentIndex + 1), state];
        if (newHistory.length > maxHistory) {
          newHistory.shift();
        }
        setCurrentIndex(newHistory.length - 1);
        return newHistory;
      });
    });
  }, [store, maxHistory, currentIndex]);

  const undo = useCallback(() => {
    if (currentIndex > 0) {
      const previousState = history[currentIndex - 1];
      store.setState(previousState as DeepPartial<T>);
      setCurrentIndex(currentIndex - 1);
    }
  }, [store, history, currentIndex]);

  const redo = useCallback(() => {
    if (currentIndex < history.length - 1) {
      const nextState = history[currentIndex + 1];
      store.setState(nextState as DeepPartial<T>);
      setCurrentIndex(currentIndex + 1);
    }
  }, [store, history, currentIndex]);

  return {
    undo,
    redo,
    canUndo: currentIndex > 0,
    canRedo: currentIndex < history.length - 1,
    history,
    currentIndex,
  };
} 