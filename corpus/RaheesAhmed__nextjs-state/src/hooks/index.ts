import { type NextState } from '../types/types';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

export interface UseNextStateOptions {
  sync?: boolean;
  suspense?: boolean;
  errorBoundary?: boolean;
}

// Core hooks
export function useNextState<T, S>(
  state: NextState<T>,
  selector: (state: T) => S,
  options: UseNextStateOptions = {}
): S {
  const [value, setValue] = useState(() => selector(state.getState()));

  useEffect(() => {
    return state.subscribe((newState) => {
      setValue(selector(newState));
    });
  }, [state, selector]);

  return value;
}

// Action hooks
export function useNextAction<T, A extends any[]>(
  state: NextState<T>,
  action: (...args: A) => (state: T) => Partial<T>
) {
  return useCallback(
    (...args: A) => {
      state.setState(action(...args));
    },
    [state, action]
  );
}

// Selector hooks
export function useNextSelector<T, S>(state: NextState<T>, selector: (state: T) => S) {
  return useMemo(() => selector(state.getState()), [state, selector, state.getState()]);
}

// Async hooks
export function useNextAsync<T, S>(
  state: NextState<T>,
  asyncSelector: (state: T) => Promise<S>,
  options: UseNextStateOptions = {}
) {
  const [value, setValue] = useState<S | undefined>(undefined);
  const [error, setError] = useState<Error | undefined>(undefined);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    const fetchData = async () => {
      try {
        setLoading(true);
        const result = await asyncSelector(state.getState());
        if (mounted) {
          setValue(result);
          setError(undefined);
        }
      } catch (err) {
        if (mounted) {
          setError(err as Error);
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    fetchData();

    return () => {
      mounted = false;
    };
  }, [state, asyncSelector]);

  return { value, error, loading };
}

// Export all hooks
export { useNextState as useState };
export { useNextAction as useAction };
export { useNextSelector as useSelector };
export { useNextAsync as useAsync };

// Export hook utilities
export { createStateHook } from './create-hook';
export { withNextState } from './with-next-state';
export { NextStateProvider } from './provider';
