import { useEffect, useState, useCallback, useRef } from 'react';
import type { DeepPartial } from '../types/types';
import type { ServerState } from '../server';

/**
 * Hook for server state synchronization
 */
export function useServerState<T extends object>(
  serverState: ServerState<T>
): [T | null, (update: DeepPartial<T>) => Promise<void>] {
  const [state, setState] = useState<T | null>(null);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;

    // Initial state fetch
    serverState.get().then((initialState) => {
      if (mounted.current) {
        setState(initialState);
      }
    });

    // Subscribe to state changes
    const unsubscribe = serverState.subscribe(async () => {
      const updatedState = await serverState.get();
      if (mounted.current) {
        setState(updatedState);
      }
    });

    return () => {
      mounted.current = false;
      unsubscribe();
    };
  }, [serverState]);

  const updateState = useCallback(
    async (update: DeepPartial<T>) => {
      await serverState.set(update);
    },
    [serverState]
  );

  return [state, updateState];
}

/**
 * Hook for optimistic updates with server state
 */
export function useOptimisticServerState<T extends object>(
  serverState: ServerState<T>
): [T | null, (update: DeepPartial<T>) => void] {
  const [state, setState] = useState<T | null>(null);
  const pendingUpdates = useRef<DeepPartial<T>[]>([]);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;

    // Initial state fetch
    serverState.get().then((initialState) => {
      if (mounted.current) {
        setState(initialState);
      }
    });

    // Subscribe to state changes
    const unsubscribe = serverState.subscribe(async () => {
      const updatedState = await serverState.get();
      if (mounted.current) {
        setState(updatedState);
        // Clear pending updates as server state is now in sync
        pendingUpdates.current = [];
      }
    });

    return () => {
      mounted.current = false;
      unsubscribe();
    };
  }, [serverState]);

  const updateState = useCallback(
    (update: DeepPartial<T>) => {
      // Apply optimistic update locally
      setState((current) => {
        if (!current) return current;
        const optimisticState = { ...current, ...update };
        return optimisticState;
      });

      // Track pending update
      pendingUpdates.current.push(update);

      // Send update to server
      serverState.set(update).catch((error) => {
        console.error('Failed to update server state:', error);

        // Rollback optimistic update on error
        if (mounted.current) {
          setState((current) => {
            if (!current) return current;
            // Remove failed update from pending updates
            pendingUpdates.current = pendingUpdates.current.filter((u) => u !== update);
            // Reapply remaining pending updates
            return pendingUpdates.current.reduce(
              (state, update) => ({ ...state, ...update }),
              current
            );
          });
        }
      });
    },
    [serverState]
  );

  return [state, updateState];
}

/**
 * Hook for server state revalidation
 */
export function useServerStateRevalidation(serverState: ServerState<unknown>, tags?: string[]) {
  const revalidate = useCallback(
    async (specificTags?: string[]) => {
      await serverState.revalidate(specificTags ?? tags);
    },
    [serverState, tags]
  );

  return revalidate;
}

/**
 * Hook for automatic server state revalidation
 */
export function useAutoRevalidation(
  serverState: ServerState<unknown>,
  tags?: string[],
  interval?: number
) {
  useEffect(() => {
    if (!interval) return;

    const timer = setInterval(async () => {
      await serverState.revalidate(tags);
    }, interval);

    return () => clearInterval(timer);
  }, [serverState, tags, interval]);
}
