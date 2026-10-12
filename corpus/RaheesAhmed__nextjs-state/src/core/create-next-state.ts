/** @jsxImportSource react */
import React, {
  createContext,
  useContext,
  useCallback,
  useState,
  useEffect,
  useMemo,
  type ReactNode,
  type ComponentType,
  type FC,
} from 'react';
import type { StateConfig, Storage, Middleware } from '../types/types';
import { NextStateError } from '../error-boundary';
import { createStorage } from '../storage/storage';

export function createNextState<T extends object>(config: StateConfig<T>) {
  type SetStateFunction = (update: Partial<T> | ((prev: T) => Partial<T>)) => void;

  const StateContext = createContext<{
    state: T;
    setState: SetStateFunction;
    setStateAsync: (
      update: Promise<Partial<T>> | ((prev: T) => Promise<Partial<T>>)
    ) => Promise<void>;
  } | null>(null);

  const storage = createStorage();

  const NextStateProvider: FC<{
    children: ReactNode;
    initialData?: Partial<T>;
    middleware?: Middleware<T>[];
  }> = ({ children, initialData, middleware = [] }) => {
    const [state, setStateInternal] = useState<T>(() => ({
      ...config.initialState,
      ...initialData,
    }));

    // Load persisted state
    useEffect(() => {
      const loadState = async () => {
        const savedState = await storage.getItem('state');
        if (savedState) {
          setStateInternal((prev) => ({ ...prev, ...JSON.parse(savedState) }));
        }
      };
      loadState();
    }, []);

    // State update with middleware and persistence
    const setState = useCallback(
      (update: Partial<T> | ((prev: T) => Partial<T>)) => {
        setStateInternal((prev) => {
          const nextUpdate = typeof update === 'function' ? update(prev) : update;
          const next = { ...prev, ...nextUpdate };

          // Execute middleware
          middleware.forEach((mw) => {
            try {
              const result = mw(prev, nextUpdate);
              if (result instanceof Promise) {
                result.catch(console.error);
              }
            } catch (error) {
              console.error('Middleware error:', error);
            }
          });

          // Persist state
          storage.setItem('state', JSON.stringify(next)).catch(console.error);

          return next;
        });
      },
      [middleware]
    );

    // Async state updates
    const setStateAsync = useCallback(
      async (update: Promise<Partial<T>> | ((prev: T) => Promise<Partial<T>>)) => {
        const resolvedUpdate = typeof update === 'function' ? await update(state) : await update;
        setState(resolvedUpdate);
      },
      [state, setState]
    );

    const value = useMemo(
      () => ({
        state,
        setState,
        setStateAsync,
      }),
      [state, setState, setStateAsync]
    );

    return React.createElement(StateContext.Provider, { value }, children);
  };

  function withNextStateProvider<P extends object>(Component: ComponentType<P>) {
    const WrappedComponent = (props: P) => {
      return React.createElement(NextStateProvider, null, React.createElement(Component, props));
    };
    WrappedComponent.displayName = `withNextState(${Component.displayName || Component.name || 'Component'})`;
    return WrappedComponent;
  }

  function useNextState<S>(selector: (state: T) => S): {
    state: S;
    setState: SetStateFunction;
  } {
    const context = useContext(StateContext);
    if (!context) {
      throw new NextStateError('useNextState must be used within NextStateProvider');
    }
    const selectedState = selector(context.state);
    return {
      state: selectedState,
      setState: context.setState,
    };
  }

  return {
    Provider: NextStateProvider,
    useNextState,
    withNextStateProvider,
  };
}
