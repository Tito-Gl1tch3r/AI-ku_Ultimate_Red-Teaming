import { useState, useCallback, useMemo } from 'react';

export interface NextStateConfig<T> {
  initialState: T;
  middleware?: Array<(state: T, nextState: T) => T>;
}

export interface NextStateHook<T> {
  state: T;
  setState: (newState: T | ((prevState: T) => T)) => void;
}

export function createNextState<T>(config: NextStateConfig<T>) {
  const { initialState, middleware = [] } = config;

  function useNextState(): NextStateHook<T> {
    const [state, setInternalState] = useState<T>(initialState);

    const setState = useCallback((newState: T | ((prevState: T) => T)) => {
      setInternalState((prevState) => {
        const nextState =
          typeof newState === 'function' ? (newState as (prevState: T) => T)(prevState) : newState;

        return middleware.reduce((acc, fn) => fn(prevState, acc), nextState);
      });
    }, []);

    return useMemo(
      () => ({
        state,
        setState,
      }),
      [state, setState]
    );
  }

  return {
    useNextState,
  };
}
