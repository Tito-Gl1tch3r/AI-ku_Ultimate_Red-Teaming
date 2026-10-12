import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { createNextState } from '../src';
import { useSelector } from '../src/hooks';

interface CounterState {
  count: number;
  lastUpdated: string;
}

describe('Counter State', () => {
  it('should initialize with default state', () => {
    const { useNextState } = createNextState<CounterState>({
      initialState: {
        count: 0,
        lastUpdated: new Date().toISOString(),
      },
    });

    const { result } = renderHook(() => useNextState());
    expect(result.current.state.count).toBe(0);
  });

  it('should update count when setState is called', () => {
    const { useNextState } = createNextState<CounterState>({
      initialState: {
        count: 0,
        lastUpdated: new Date().toISOString(),
      },
    });

    const { result } = renderHook(() => useNextState());

    act(() => {
      result.current.setState({
        count: 1,
        lastUpdated: new Date().toISOString(),
      });
    });

    expect(result.current.state.count).toBe(1);
  });

  it('should select specific state using selector', () => {
    const { useNextState } = createNextState<CounterState>({
      initialState: {
        count: 0,
        lastUpdated: new Date().toISOString(),
      },
    });

    const { result } = renderHook(() => {
      const state = useNextState();
      return useSelector(state, (state) => ({ count: state.count }));
    });

    expect(result.current).toEqual({ count: 0 });
  });
});
